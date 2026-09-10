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

# ATAJO-P1: el artefacto vive dentro del repositorio, junto al codigo.
#           Alcanza para un modelo de pocos megabytes y hace que desplegar
#           sea copiar una carpeta.
#           Parte 2 -> model registry con versionado y rollback.
#
# La ruta se lee de una variable de entorno y no esta escrita a mano: asi,
# cuando el artefacto se mueva a S3 en la Parte 2, no hay que tocar esta
# logica de carga.


# ---------------------------------------------------------------------------
# ESTADO DE ARRANQUE DE LA SESION 2: hay cuatro TODO por llenar.
#
# Mientras este archivo no exponga un blueprint 'bp' con endpoints, app.py lo
# carga y no registra nada: el tablero de la sesion 1 sigue funcionando igual.
# ---------------------------------------------------------------------------


# TODO 1 sesion 2: cargar el artefacto y verificar que sea compatible
#
# Define MODEL_DIR leyendo la variable de entorno MODEL_PATH, escribe
# cargar_artefacto() y la funcion estado() que aporta a /api/health.
#
# La verificacion de version de scikit-learn no es opcional: joblib no es un
# formato estable y un mismatch puede devolver numeros distintos sin avisar.


# TODO 2 sesion 2: validar la entrada CONTRA EL CONTRATO
#
# Define la excepcion InputInvalido y la funcion validar(payload).
# Sin reglas escritas a mano: todo sale de contrato["features"].
#
# Feature faltante o categoria inexistente -> error.
# Numero fuera de rango -> se predice Y se avisa.


# TODO 3 sesion 2: GET /api/model
#
# Devuelve el contrato tal cual. El formulario de la sesion 3 lo va a usar
# para construirse solo.


# TODO 4 sesion 2: POST /api/predict
#
# Una casa entra, un precio sale.
# 400 si el cliente se equivoco, diciendo en que campo.
# 500 si fallamos nosotros, sin exponer el detalle al cliente.
