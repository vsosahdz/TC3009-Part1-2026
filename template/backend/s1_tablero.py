"""El tablero, desacoplado del dataset.

Es el mismo archivo de la sesion 1, con una diferencia: en el curso las
columnas estaban escritas a mano por todo el archivo. Aqui viven en UN bloque
de configuracion, y el resto del codigo no sabe como se llama nada.

    ┌─────────────────────────────────────────────────┐
    │  AJUSTA 1        <- lo unico que editas aqui    │
    ├─────────────────────────────────────────────────┤
    │  todo lo demas   <- no lo toques                │
    └─────────────────────────────────────────────────┘

Y hay una consecuencia que vale la practica entera: /api/stats ahora devuelve
un bloque 'meta' diciendo COMO se llaman sus propias columnas, asi que el
tablero del frontend tambien deja de saberlo. Es la misma idea del contrato
del modelo, aplicada a los datos.

Sirve para regresion (target numerico) y para clasificacion binaria (target
categorico). El contrato de la API no cambia entre los dos casos: cambia el
significado de 'metrica', y el propio 'meta' dice cual es.
"""

import os
import pathlib

import pandas as pd
from flask import Blueprint, jsonify, request

bp = Blueprint("s1_tablero", __name__)

RAIZ = pathlib.Path(__file__).resolve().parent.parent


# ===========================================================================
# AJUSTA 1 — tu dataset
# ===========================================================================
#
# Esto es todo lo que este archivo sabe de tu problema. Si lo llenas bien, el
# resto del archivo funciona sin que lo abras.

# El archivo, dentro de data/.
ARCHIVO = "datos.csv"

# La columna que el modelo va a predecir.
TARGET = "bueno"

# "numero"    -> regresion.     La metrica de cada grupo es el PROMEDIO del target.
# "categoria" -> clasificacion. La metrica es la PROPORCION de CLASE_POSITIVA.
TIPO_TARGET = "categoria"

# Solo para clasificacion: cual de las clases es la que te interesa medir.
# En regresion se ignora.
CLASE_POSITIVA = 1

# La columna categorica que organiza el tablero. Es el filtro y el eje de
# comparacion de la primera grafica. Elige una con pocas categorias (2 a 30) y
# que signifique algo para quien mira: un segmento, una region, un tipo.
GRUPO = "color"

# Una segunda columna para cortar los datos, idealmente ordinal (pocos valores
# con orden natural: un nivel, una clase, un rango de edad).
CORTE = "nivel_alcohol"

# Las columnas que el modelo va a usar. Las mismas que vas a exportar en el
# contrato: el tablero y el predictor hablan del mismo vocabulario.
FEATURES = [
    "acidez_volatil",
    "acido_citrico",
    "azucar_residual",
    "cloruros",
    "dioxido_azufre_total",
    "densidad",
    "pH",
    "sulfatos",
    "alcohol",
    "color",
]

# La columna que identifica cada fila. None si tu dataset no tiene una.
ID = None

# ===========================================================================
# De aqui para abajo no hay nada que ajustar.
# ===========================================================================

DEFAULT_LIMIT = 20
MAX_LIMIT = 200

DATA_PATH = os.environ.get("DATA_PATH", str(RAIZ / "data" / ARCHIVO))

# ATAJO-P1: el CSV se carga completo en memoria al arrancar y nunca se recarga.
#           Parte 2 -> base de datos, consultas, paginacion real.
df = pd.read_csv(DATA_PATH)

COLUMNAS_EXPUESTAS = ([ID] if ID else []) + FEATURES + [TARGET]

# Un fallo aqui es de configuracion, no de codigo, y conviene que lo diga al
# arrancar y no en la primera peticion.
faltantes = [c for c in COLUMNAS_EXPUESTAS + [GRUPO, CORTE] if c not in df.columns]
if faltantes:
    raise ValueError(
        f"AJUSTA 1: estas columnas no existen en {ARCHIVO}: {faltantes}.\n"
        f"    Las que si existen: {list(df.columns)}"
    )


def metrica(serie):
    """El numero que resume un grupo.

    Es el unico punto del archivo donde regresion y clasificacion difieren, y
    por eso esta aislado aqui en lugar de repartido por los endpoints.
    """
    if TIPO_TARGET == "categoria":
        return round(float((serie == CLASE_POSITIVA).mean()), 4)
    return round(float(serie.mean()), 2)


def resumen_target(serie):
    """Las cifras grandes del tablero."""
    if TIPO_TARGET == "categoria":
        conteos = serie.value_counts()
        return {
            "name": TARGET,
            "tipo": "categoria",
            "positiva": CLASE_POSITIVA,
            "tasa": metrica(serie),
            "clases": {str(k): int(v) for k, v in conteos.items()},
        }
    return {
        "name": TARGET,
        "tipo": "numero",
        "mean": round(float(serie.mean()), 2),
        "median": round(float(serie.median()), 2),
        "min": round(float(serie.min()), 2),
        "max": round(float(serie.max()), 2),
    }


def por_columna(datos, columna, ordenar_por_valor):
    """Agrega el target por una columna. Sirve igual para GRUPO y para CORTE."""
    g = datos.groupby(columna)[TARGET].agg(["count"])
    g["metrica"] = datos.groupby(columna)[TARGET].apply(metrica)
    g = g.reset_index()
    g = g.sort_values(columna) if ordenar_por_valor else g.sort_values(
        "metrica", ascending=False
    )
    return [
        {
            "valor": fila[columna] if isinstance(fila[columna], str) else _num(fila[columna]),
            "count": int(fila["count"]),
            "metrica": float(fila["metrica"]),
        }
        for _, fila in g.iterrows()
    ]


def _num(v):
    """int si es entero, float si no. Evita '3.0' en las etiquetas."""
    f = float(v)
    return int(f) if f.is_integer() else f


@bp.get("/api/stats")
def stats():
    """Agregados del dataset. Alimenta las graficas del tablero.

    Si llega ?grupo=, las cifras y el desglose por CORTE se calculan solo sobre
    ese grupo. El desglose por GRUPO se mantiene global a proposito: es el eje
    de comparacion, y filtrarlo a un solo valor lo dejaria sin sentido.
    """
    valor = request.args.get("grupo")
    alcance = df[df[GRUPO].astype(str) == valor] if valor else df

    return jsonify(
        {
            # Esto es lo que hace que el frontend no sepa de tu dataset.
            # Las etiquetas de las graficas salen de aqui, no del JSX.
            "meta": {
                "target": TARGET,
                "tipo_target": TIPO_TARGET,
                "clase_positiva": CLASE_POSITIVA if TIPO_TARGET == "categoria" else None,
                "grupo": GRUPO,
                "corte": CORTE,
                "id": ID,
                "features": FEATURES,
            },
            "count": int(len(alcance)),
            "scope": valor or "todos",
            "target": resumen_target(alcance[TARGET]),
            "by_grupo": por_columna(df, GRUPO, ordenar_por_valor=False),
            "by_corte": por_columna(alcance, CORTE, ordenar_por_valor=True),
        }
    )


@bp.get("/api/data")
def data():
    """Registros del dataset, para la tabla del tablero."""
    valor = request.args.get("grupo")
    try:
        limite = int(request.args.get("limit", DEFAULT_LIMIT))
    except ValueError:
        limite = DEFAULT_LIMIT
    limite = max(1, min(limite, MAX_LIMIT))

    filtrado = df[df[GRUPO].astype(str) == valor] if valor else df

    return jsonify(
        {
            "meta": {"columnas": COLUMNAS_EXPUESTAS, "target": TARGET, "grupo": GRUPO},
            "count": int(min(limite, len(filtrado))),
            "total_matching": int(len(filtrado)),
            "rows": filtrado[COLUMNAS_EXPUESTAS]
            .head(limite)
            .where(pd.notna(filtrado[COLUMNAS_EXPUESTAS].head(limite)), None)
            .to_dict(orient="records"),
        }
    )


def estado():
    """Lo que este modulo aporta a /api/health."""
    return {"filas_en_datos": int(len(df)), "target": TARGET}
