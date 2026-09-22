"""Sesion 4: de un endpoint a un producto.

Aqui el servicio gana dos cosas que lo separan de un script que predice:

  · MEMORIA    cada prediccion queda registrada, y se puede consultar
  · PALABRAS   la prediccion se explica, no solo se entrega

Ninguna de las dos cambia el modelo. Las dos cambian el producto.

Hay 4 TODO. La guia (docs/s4-guia.md) los lleva en orden.
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

    TODO 1 sesion 4: la tabla.

    Escribe el CREATE TABLE IF NOT EXISTS con estas columnas:

        prediction_id  TEXT PRIMARY KEY
        creado_en      TEXT NOT NULL
        model_version  TEXT NOT NULL
        prediccion     REAL NOT NULL
        entrada        TEXT NOT NULL

    Fijate en la ultima: se guarda el input COMPLETO, no solo el resultado.
    Esa decision cuesta lo mismo hoy y es la que hace posible, mas adelante,
    comparar lo que el modelo esta viendo contra lo que vio al entrenar. Sin
    los inputs no hay nada que comparar.

    Nota de producto: registrar entradas crudas tiene implicaciones de datos
    personales en un sistema real. Aqui son casas; en tu reto puede que no.
    """
    with conectar() as con:
        ...


crear_esquema()


def registrar(prediction_id, model_version, prediccion, entrada):
    """Guarda una prediccion.

    TODO 2 sesion 4: el INSERT.

    Cinco columnas, cinco valores, con ? por cada uno (nunca con formato de
    cadena: eso es inyeccion de SQL).

    Dos detalles:
      · la hora la pone el servidor, en UTC, no el cliente
      · 'entrada' es un diccionario y la columna es TEXT -> json.dumps
    """
    with conectar() as con:
        ...


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

    Este metodo ya esta escrito. Leelo: es lo que hay que entender de la
    sesion, y es lo que vas a querer copiar en tu reto.

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
    """Lo que este modulo aporta a /api/health.

    Devuelve {"predicciones_registradas": <cuantas hay>}. Es la forma mas
    rapida de saber, desde la terminal, si el registro esta funcionando.
    """
    with conectar() as con:
        n = con.execute("SELECT COUNT(*) AS n FROM predicciones").fetchone()["n"]
    return {"predicciones_registradas": int(n)}


@bp.get("/api/history")
def history():
    """Lo que el modelo ha estado prediciendo.

    TODO 3 sesion 4: el endpoint.

    Un tablero que solo muestra el dataset de entrenamiento envejece el primer
    dia. Este endpoint lo alimenta con el uso real del producto.

    Lee ?limit= (por defecto 50), acotalo entre 1 y 500 --nunca dejes que el
    cliente pida "todo"-- y devuelve:

        {"count": n, "rows": [{prediction_id, created_at, model_version,
                               prediction, input}, ...]}

    Mas reciente primero. 'entrada' vuelve de la base como texto: json.loads.
    """
    return jsonify({"count": 0, "rows": []})


def redactar(entrada, prediccion):
    """Convierte una prediccion en una frase que un humano entiende.

    TODO 4 sesion 4: la explicacion.

    Usa las importancias del contrato (s2_modelo.contrato) para quedarte con
    las 3 features que mas pesan, y compara el valor que mando el usuario
    contra la mediana de esa feature en el contrato:

        > mediana * 1.15   -> "por encima de lo habitual"
        < mediana * 0.85   -> "por debajo de lo habitual"
        si no              -> "en el rango habitual"

    Es una PLANTILLA: no hay modelo de lenguaje aqui.

    La regla que importa, y que se conserva si un dia esto llama a un LLM:

        el modelo DECIDE el numero
        esta funcion lo TRADUCE
        nunca lo cambia
    """
    return f"El modelo estima {prediccion:,.0f} para esta casa."


@bp.post("/api/explain")
def explain():
    """Explica una prediccion, sin volver a decidirla.

    Fijate en que NO vuelve a predecir por su cuenta: recibe el numero que ya
    dio el modelo. Si esta funcion calculara su propio valor, la explicacion
    podria contradecir lo que el usuario esta viendo.

    Ya esta escrito.
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
