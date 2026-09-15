"""Sesion 4: de un endpoint a un producto.

Aqui el servicio gana dos cosas que lo separan de un script que predice:

  · MEMORIA    cada prediccion queda registrada, y se puede consultar
  · PALABRAS   la prediccion se explica, no solo se entrega

Ninguna de las dos cambia el modelo. Las dos cambian el producto.
"""

import json
import os
import pathlib
import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

import s2_modelo

bp = Blueprint("s4_producto", __name__)

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# ATAJO-P1: el registro vive en un archivo SQLite junto al codigo.
#           Alcanza para una clase y no necesita servidor.
#           Parte 2 -> almacenamiento durable, fuera de la maquina, con
#           deteccion de drift sobre estos mismos datos.
DB_PATH = os.environ.get("DB_PATH", str(RAIZ / "predicciones.sqlite"))


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def crear_esquema():
    """Crea la tabla si no existe. Idempotente.

    Se guarda el input COMPLETO, no solo el resultado. Esa decision cuesta lo
    mismo hoy y es la que hace posible, en la Parte 2, comparar lo que el
    modelo esta viendo contra lo que vio al entrenar: eso es deteccion de
    drift, y sin los inputs no hay nada que comparar.

    Nota de producto: registrar entradas crudas tiene implicaciones de datos
    personales en un sistema real. Aqui son casas; en tu reto puede que no.
    """
    with conectar() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS predicciones (
                prediction_id TEXT PRIMARY KEY,
                creado_en     TEXT NOT NULL,
                model_version TEXT NOT NULL,
                prediccion    REAL NOT NULL,
                entrada       TEXT NOT NULL
            )
            """
        )


crear_esquema()


def registrar(prediction_id, model_version, prediccion, entrada):
    """Guarda una prediccion."""
    with conectar() as con:
        con.execute(
            "INSERT OR REPLACE INTO predicciones VALUES (?, ?, ?, ?, ?)",
            (
                prediction_id,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                model_version,
                float(prediccion),
                json.dumps(entrada, ensure_ascii=False),
            ),
        )


@bp.after_app_request
def registrar_si_fue_prediccion(respuesta):
    """Registra cada prediccion exitosa, SIN tocar el codigo de la sesion 2.

    Este es el detalle interesante del modulo. Necesitamos que cada llamada a
    /api/predict quede guardada, pero /api/predict lo escribiste tu en la
    sesion 2 y no queremos volver a abrir ese archivo: editarlo obligaria a
    fusionar cambios sobre codigo que ya es tuyo.

    La solucion es un gancho: Flask deja mirar --y reaccionar a-- cualquier
    respuesta de la aplicacion, venga del modulo que venga.

        agregar comportamiento sin modificar lo que ya funciona

    Es una idea que vas a reencontrar como middleware, interceptores o
    decoradores en casi cualquier framework.

    Un 400 no se registra: solo hay prediccion cuando hubo prediccion.
    """
    if request.path != "/api/predict" or respuesta.status_code != 200:
        return respuesta

    try:
        datos = respuesta.get_json()
        registrar(
            datos["prediction_id"],
            datos["model_version"],
            datos["prediction"],
            request.get_json(silent=True) or {},
        )
    except Exception:  # noqa: BLE001
        # Que falle el registro NO debe tumbar una prediccion que ya salio
        # bien. El usuario ya tiene su numero; el log es cosa nuestra.
        current_app.logger.exception("no se pudo registrar la prediccion")

    return respuesta


def estado():
    """Lo que este modulo aporta a /api/health."""
    with conectar() as con:
        n = con.execute("SELECT COUNT(*) AS n FROM predicciones").fetchone()["n"]
    return {"predicciones_registradas": int(n)}


@bp.get("/api/history")
def history():
    """Lo que el modelo ha estado prediciendo.

    Un tablero que solo muestra el dataset de entrenamiento envejece el primer
    dia. Este endpoint lo alimenta con el uso real del producto.
    """
    try:
        limite = int(request.args.get("limit", 50))
    except ValueError:
        limite = 50
    limite = max(1, min(limite, 500))

    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM predicciones ORDER BY creado_en DESC, rowid DESC LIMIT ?",
            (limite,),
        ).fetchall()

    return jsonify(
        {
            "count": len(filas),
            "rows": [
                {
                    "prediction_id": f["prediction_id"],
                    "created_at": f["creado_en"],
                    "model_version": f["model_version"],
                    "prediction": round(f["prediccion"], 2),
                    "input": json.loads(f["entrada"]),
                }
                for f in filas
            ],
        }
    )


def redactar(entrada, prediccion):
    """Convierte una prediccion en una frase que un humano entiende.

    Usa las importancias del contrato y compara la casa contra el promedio de
    su colonia. Es una PLANTILLA: no hay modelo de lenguaje aqui.

    La regla que importa, y que se conserva si un dia esto llama a un LLM:

        el modelo DECIDE el numero
        esta funcion lo TRADUCE
        nunca lo cambia
    """
    contrato = s2_modelo.contrato
    importancias = contrato.get("feature_importances", {})
    top = [f for f, _ in sorted(importancias.items(), key=lambda kv: -kv[1])[:3]]

    partes = []
    for nombre in top:
        valor = entrada.get(nombre)
        if valor is None:
            continue
        ficha = next((f for f in contrato["features"] if f["name"] == nombre), None)
        if ficha and ficha["type"] == "num" and "median" in ficha:
            mediana = ficha["median"]
            if valor > mediana * 1.15:
                partes.append(f"{nombre} por encima de lo habitual ({valor:g})")
            elif valor < mediana * 0.85:
                partes.append(f"{nombre} por debajo de lo habitual ({valor:g})")
            else:
                partes.append(f"{nombre} en el rango habitual ({valor:g})")
        else:
            partes.append(f"{nombre} = {valor}")

    detalle = "; ".join(partes) if partes else "los datos proporcionados"
    return (
        f"El modelo estima {prediccion:,.0f} para esta casa. "
        f"Lo que mas pesa en esa estimacion es {detalle}."
    )


@bp.post("/api/explain")
def explain():
    """Explica una prediccion, sin volver a decidirla.

    Fijate en que NO vuelve a predecir por su cuenta: recibe el numero que ya
    dio el modelo. Si esta funcion calculara su propio valor, la explicacion
    podria contradecir lo que el usuario esta viendo.
    """
    payload = request.get_json(silent=True) or {}
    entrada = payload.get("input")
    prediccion = payload.get("prediction")

    if not isinstance(entrada, dict) or prediccion is None:
        return jsonify({"error": "se esperaba {input: {...}, prediction: numero}"}), 400

    try:
        prediccion = float(prediccion)
    except (TypeError, ValueError):
        return jsonify({"error": "'prediction' debe ser un numero"}), 400

    return jsonify(
        {
            "explanation": redactar(entrada, prediccion),
            # ATAJO-P1: la explicacion la arma una plantilla determinista.
            #           docs/extras/gemini-explain.md documenta el cambio a un
            #           modelo de lenguaje real, que es reemplazar esta funcion.
            "source": "plantilla",
        }
    )
