"""Sesion 2: el modelo cruza la frontera.

Aqui vive TODO lo que el servicio necesita saber del modelo: cargar el
artefacto, verificar que sea compatible, validar la entrada contra el contrato,
y predecir.

Fijate en lo que este archivo NO hace: no imputa, no escala, no codifica, y no
invierte el logaritmo del target. Todo eso viaja dentro de pipeline.joblib. Si
este archivo tuviera que saber algo de eso, la exportacion estaria mal hecha.
"""

import json
import os
import pathlib
import uuid

import joblib
import pandas as pd
import sklearn
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("s2_modelo", __name__)

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def donde_generarlo():
    """De donde sale el artefacto, segun en que estes trabajando.

    En el curso lo produce el notebook en Colab; en la practica, un script que
    corre en la propia instancia. Decir siempre "corre el notebook" manda al
    sitio equivocado justo a quien ya iba perdido.

    No lo escribes tu: viene con el modulo.
    """
    if (RAIZ / "notebooks" / "entrenar.py").exists():
        return "    Generalo asi:  ./.venv/bin/python notebooks/entrenar.py"
    return (
        "    Corre el notebook notebooks/01-entrenar-y-exportar.ipynb en Colab,\n"
        "    descarga el zip y descomprimelo en artifacts/."
    )


# ATAJO-P1: el artefacto vive dentro del repositorio, junto al codigo.
#           Alcanza para un modelo de pocos megabytes y hace que desplegar
#           sea copiar una carpeta.
#           Parte 2 -> model registry con versionado y rollback.
#
# La ruta se lee de una variable de entorno y no esta escrita a mano: asi,
# cuando el artefacto se mueva a S3 en la Parte 2, no hay que tocar esta
# logica de carga.
MODEL_DIR = pathlib.Path(os.environ.get("MODEL_PATH", str(RAIZ / "artifacts")))


def cargar_artefacto():
    """Carga el pipeline y su contrato, y verifica que sean compatibles.

    La verificacion de version no es paranoia: joblib no es un formato estable.
    Un artefacto exportado con una version de scikit-learn y cargado con otra
    puede fallar al deserializar o --peor-- cargar y devolver numeros distintos
    sin avisar de nada.
    """
    ruta_contrato = MODEL_DIR / "metadata.json"
    ruta_pipeline = MODEL_DIR / "pipeline.joblib"

    if not ruta_contrato.exists() or not ruta_pipeline.exists():
        raise FileNotFoundError(
            f"no encuentro el artefacto en {MODEL_DIR}.\n" + donde_generarlo()
        )

    contrato = json.loads(ruta_contrato.read_text())
    pipeline = joblib.load(ruta_pipeline)

    entrenado_con = contrato["sklearn_version"]
    if entrenado_con != sklearn.__version__:
        print(
            "\n*** AVISO DE COMPATIBILIDAD ***\n"
            f"    El artefacto se entreno con scikit-learn {entrenado_con}\n"
            f"    y este servicio tiene instalada la {sklearn.__version__}.\n"
            "    Las predicciones pueden ser incorrectas sin dar ningun error.\n"
            "    Revisa backend/requirements.txt.\n",
            flush=True,
        )
    else:
        print(
            f"artefacto {contrato['model_version']} cargado "
            f"(scikit-learn {entrenado_con})",
            flush=True,
        )

    return pipeline, contrato


pipeline, contrato = cargar_artefacto()


def estado():
    """Lo que este modulo aporta a /api/health.

    Que el estado del servicio diga QUE modelo esta sirviendo no es un detalle:
    es lo que permite saber, mirando una URL, si un despliegue quedo con el
    artefacto que esperabas. En la Parte 2 es lo que hace posible un rollback.
    """
    return {
        "model_version": contrato["model_version"],
        "sklearn_version": sklearn.__version__,
        "artifact_hash": contrato["artifact_hash"],
    }


class InputInvalido(Exception):
    """El cliente mando algo que el contrato no acepta."""


def validar(payload):
    """Valida la entrada CONTRA EL CONTRATO, no contra reglas escritas a mano.

    Esto es lo que hace que el servicio siga siendo correcto cuando el modelo
    cambia: si el contrato gana una feature, la validacion la exige sola.

    Devuelve el DataFrame de una fila listo para el pipeline, y la lista de
    advertencias que no invalidan la peticion.
    """
    if not isinstance(payload, dict):
        raise InputInvalido("el cuerpo de la peticion debe ser un objeto JSON")

    fila = {}
    advertencias = []

    for f in contrato["features"]:
        nombre = f["name"]
        if nombre not in payload:
            raise InputInvalido(f"falta la feature '{nombre}'")
        valor = payload[nombre]

        if f["type"] == "num":
            try:
                valor = float(valor)
            except (TypeError, ValueError):
                raise InputInvalido(f"'{nombre}' debe ser un numero, llego {valor!r}")
            # Fuera de rango NO es un error: es una casa legitima que el modelo
            # no vio al entrenar. Rechazarla seria un mal producto; predecir sin
            # avisar seria deshonesto. Se predice Y se avisa.
            if valor < f["min"] or valor > f["max"]:
                advertencias.append(
                    f"'{nombre}' = {valor:g} esta fuera del rango visto al "
                    f"entrenar ({f['min']:g} a {f['max']:g}); la prediccion es "
                    "menos confiable"
                )
        else:
            if valor not in f["allowed"]:
                raise InputInvalido(
                    f"'{nombre}' no acepta el valor {valor!r}. "
                    f"Valores validos: {', '.join(map(str, f['allowed']))}"
                )

        fila[nombre] = valor

    return pd.DataFrame([fila]), advertencias


@bp.get("/api/model")
def model():
    """El contrato del modelo, tal cual. Alimenta el formulario y la Model Card.

    El frontend no tiene una lista de features escrita a mano: la pide aqui. Si
    el modelo cambia, el formulario cambia solo.
    """
    return jsonify(contrato)


@bp.post("/api/predict")
def predict():
    """Un caso entra, una clase sale --con su probabilidad."""
    try:
        entrada, advertencias = validar(request.get_json(silent=True))
    except InputInvalido as e:
        # 400: el cliente mando algo invalido, y se le dice QUE fue.
        return jsonify({"error": str(e)}), 400

    try:
        # AJUSTA 4 — de un numero a una clase.
        #
        # En regresion esto era una linea: pipeline.predict(entrada)[0].
        # En clasificacion hay que decidir, y decidir tiene dos partes:
        #
        #   1. el MODELO da probabilidades      -> predict_proba
        #   2. el PRODUCTO elige donde cortar   -> el umbral
        #
        # Fijate que el umbral sale del CONTRATO, no esta escrito aqui. Asi,
        # cambiarlo es reentrenar --o editar metadata.json-- y no tocar el
        # servicio. Es la misma regla de siempre: lo que depende del modelo
        # viaja con el modelo.
        probas = pipeline.predict_proba(entrada)[0]
        clases = [_json(c) for c in pipeline.classes_]
        positiva = contrato.get("clase_positiva", clases[-1])
        umbral = float(contrato.get("umbral", 0.5))

        p_positiva = float(probas[clases.index(positiva)])
        negativa = next(c for c in clases if c != positiva)
        clase = positiva if p_positiva >= umbral else negativa

        probabilidades = {
            str(c): round(float(p), 4) for c, p in zip(clases, probas)
        }
    except Exception:
        # 500: fallamos nosotros. El detalle va a los registros del servidor,
        # no a la respuesta.
        current_app.logger.exception("fallo la prediccion")
        return jsonify({"error": "no se pudo generar la prediccion"}), 500

    return jsonify(
        {
            "prediction_id": str(uuid.uuid4()),
            # La clase decidida. Es lo que el usuario ve en grande.
            "prediction": clase,
            # Y la probabilidad, que es lo que el modelo de verdad dijo.
            # Mostrar solo la clase esconde la diferencia entre 0.51 y 0.99.
            "probabilities": probabilidades,
            "confidence": round(p_positiva, 4),
            "threshold": umbral,
            "model_version": contrato["model_version"],
            "warnings": advertencias,
        }
    )


def _json(v):
    """numpy -> tipos de Python. classes_ viene como numpy y no es serializable."""
    try:
        return v.item()
    except AttributeError:
        return v
