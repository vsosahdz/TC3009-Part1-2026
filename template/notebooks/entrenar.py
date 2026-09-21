"""Entrena un clasificador y exporta el artefacto. Plantilla de la practica.

    ./.venv/bin/python template/notebooks/entrenar.py

Produce lo mismo que el notebook de la sesion 2, con la misma estructura:

    artifacts/
    ├── pipeline.joblib     el modelo, con su preproceso adentro
    ├── metadata.json       el CONTRATO
    └── example.json        una entrada y su respuesta, para el test de paridad

El contrato tiene la MISMA forma que el de regresion. Esa es la razon de que
el formulario y la Model Card funcionen sin tocarlos: no saben de que problema
se trata, solo leen el contrato.

Lo unico que cambia entre regresion y clasificacion:

    · el estimador                     RandomForestClassifier
    · 'task' en el contrato            "clasificacion"
    · las metricas                     accuracy/precision/recall/f1/roc_auc
    · 'classes' y 'umbral'             no existen en regresion
"""

import hashlib
import json
import pathlib
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEMILLA = 42


# ===========================================================================
# AJUSTA 2 — tu modelo
# ===========================================================================

ARCHIVO = "datos.csv"
TARGET = "bueno"

# La clase que te interesa detectar. Es la que manda en precision y recall.
CLASE_POSITIVA = 1

# Las features. Tienen que ser las MISMAS que pusiste en AJUSTA 1, o el
# tablero y el predictor hablarian de cosas distintas.
FEATURES = [
    "acidez_volatil", "acido_citrico", "azucar_residual", "cloruros",
    "dioxido_azufre_total", "densidad", "pH", "sulfatos", "alcohol", "color",
]

# Cuales son categoricas. El resto se tratan como numericas.
CATEGORICAS = ["color"]

# AJUSTA 3 — el umbral.
#
# Esta linea es una decision de PRODUCTO, no del modelo, y no tiene equivalente
# en regresion.
#
# El modelo devuelve una probabilidad. Convertirla en un si/no exige elegir
# donde cortar, y esa eleccion depende de que error duele mas:
#
#   umbral bajo   -> mas positivos detectados, mas falsas alarmas
#   umbral alto   -> menos falsas alarmas, se te escapan casos reales
#
# 0.5 no es "el valor por defecto correcto": es el que sale de no haber
# elegido. Con clases desbalanceadas --aqui 20% de positivos-- casi siempre
# esta mal. Justifica el tuyo en el reto.
UMBRAL = 0.5

MODEL_VERSION = "1.0.0"

# ===========================================================================
# De aqui para abajo, nada que ajustar.
# ===========================================================================

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
DATOS = RAIZ / "data" / ARCHIVO
ARTEFACTOS = RAIZ / "artifacts"

NUMERICAS = [f for f in FEATURES if f not in CATEGORICAS]


def construir():
    preproceso = ColumnTransformer(
        [
            ("num", Pipeline([
                ("imputar", SimpleImputer(strategy="median")),
                ("escalar", StandardScaler()),
            ]), NUMERICAS),
            ("cat", Pipeline([
                ("imputar", SimpleImputer(strategy="most_frequent")),
                ("codificar", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]), CATEGORICAS),
        ]
    )
    return Pipeline([
        ("preproceso", preproceso),
        # class_weight="balanced" porque las clases estan desbalanceadas.
        # Sin esto el modelo aprende que decir "no" siempre acierta el 80%.
        ("estimador", RandomForestClassifier(
            n_estimators=100, random_state=SEMILLA, n_jobs=-1,
            class_weight="balanced",
        )),
    ])


def metricas(modelo, X, y):
    """Las metricas de clasificacion.

    Accuracy sola miente con clases desbalanceadas: aqui un modelo que diga
    siempre "no bueno" saca 80% y no sirve para nada. Por eso van las cuatro.
    """
    proba = modelo.predict_proba(X)[:, list(modelo.classes_).index(CLASE_POSITIVA)]
    pred = np.where(proba >= UMBRAL, CLASE_POSITIVA, _clase_negativa(modelo))
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, pos_label=CLASE_POSITIVA, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, pos_label=CLASE_POSITIVA, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, pos_label=CLASE_POSITIVA, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, proba)), 4),
    }


def _clase_negativa(modelo):
    otras = [c for c in modelo.classes_ if c != CLASE_POSITIVA]
    return otras[0]


def contrato_de_features(df):
    """El dominio de cada feature. Identico al de regresion, y por eso el
    formulario del frontend funciona sin tocarlo."""
    fichas = []
    for f in FEATURES:
        if f in CATEGORICAS:
            fichas.append({
                "name": f, "type": "cat",
                "allowed": sorted(df[f].dropna().astype(str).unique().tolist()),
            })
        else:
            s = pd.to_numeric(df[f], errors="coerce").dropna()
            fichas.append({
                "name": f, "type": "num",
                "min": float(s.min()), "max": float(s.max()),
                "median": float(s.median()),
            })
    return fichas


def importancias(modelo):
    """Importancias por feature ORIGINAL, sumando las columnas del one-hot."""
    est = modelo.named_steps["estimador"]
    nombres = modelo.named_steps["preproceso"].get_feature_names_out()
    pesos = est.feature_importances_
    acc = {f: 0.0 for f in FEATURES}
    for nombre, peso in zip(nombres, pesos):
        limpio = nombre.split("__", 1)[-1]
        for f in FEATURES:
            if limpio == f or limpio.startswith(f + "_"):
                acc[f] += float(peso)
                break
    return {k: round(v, 4) for k, v in sorted(acc.items(), key=lambda kv: -kv[1])}


def main():
    df = pd.read_csv(DATOS)
    faltan = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if faltan:
        raise SystemExit(f"AJUSTA 2: no existen en {ARCHIVO}: {faltan}")

    X, y = df[FEATURES], df[TARGET]

    # stratify: con clases desbalanceadas, un split al azar puede dejar el
    # conjunto de prueba casi sin positivos y las metricas dejan de significar.
    X_ent, X_resto, y_ent, y_resto = train_test_split(
        X, y, test_size=0.3, random_state=SEMILLA, stratify=y)
    X_val, X_pru, y_val, y_pru = train_test_split(
        X_resto, y_resto, test_size=0.5, random_state=SEMILLA, stratify=y_resto)

    modelo = construir()
    modelo.fit(X_ent, y_ent)

    m_val, m_pru = metricas(modelo, X_val, y_val), metricas(modelo, X_pru, y_pru)

    ARTEFACTOS.mkdir(parents=True, exist_ok=True)
    ruta = ARTEFACTOS / "pipeline.joblib"
    joblib.dump(modelo, ruta, compress=3)
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()[:12]

    metadata = {
        "model_version": MODEL_VERSION,
        "task": "clasificacion",
        "algorithm": f"RandomForestClassifier(n_estimators={modelo.named_steps['estimador'].n_estimators})",
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sklearn_version": sklearn.__version__,
        "artifact_hash": huella,
        "target": TARGET,
        "target_transform": "ninguna",
        "classes": [_json(c) for c in modelo.classes_],
        "clase_positiva": _json(CLASE_POSITIVA),
        "umbral": UMBRAL,
        "features": contrato_de_features(df),
        "splits": {"train": len(X_ent), "validation": len(X_val), "test": len(X_pru)},
        "metrics": {"validation": m_val, "test": m_pru},
        "feature_importances": importancias(modelo),
        "model_comparison": [],
        "hyperparameter_experiments": [],
    }
    (ARTEFACTOS / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    # example.json: la referencia del test de paridad.
    fila = X_pru.iloc[[0]]
    proba = modelo.predict_proba(fila)[0]
    idx_pos = list(modelo.classes_).index(CLASE_POSITIVA)
    clase = CLASE_POSITIVA if proba[idx_pos] >= UMBRAL else _clase_negativa(modelo)
    (ARTEFACTOS / "example.json").write_text(json.dumps({
        "input": {k: _json(v) for k, v in fila.iloc[0].items()},
        "prediction": _json(clase),
        "probabilities": {str(_json(c)): round(float(p), 6)
                          for c, p in zip(modelo.classes_, proba)},
        "model_version": MODEL_VERSION,
    }, indent=2, ensure_ascii=False) + "\n")

    print(f"artefacto  : {ruta}  ({ruta.stat().st_size / 1e6:.1f} MB, {huella})")
    print(f"splits     : {metadata['splits']}")
    print(f"umbral     : {UMBRAL}")
    print(f"validation : {m_val}")
    print(f"test       : {m_pru}")
    print("importancias:")
    for k, v in list(metadata["feature_importances"].items())[:5]:
        print(f"    {k:24s} {v}")


def _json(v):
    """numpy -> tipos de Python, para que json.dumps no se queje."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


if __name__ == "__main__":
    main()
