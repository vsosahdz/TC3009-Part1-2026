"""Arma data/datos.csv para la practica, a partir de OpenML.

Este script NO es parte de lo que el alumno construye: es como se preparo el
dataset de ejemplo. Lo dejamos a la vista porque preparar los datos es la
mitad del trabajo real, y porque tiene dos decisiones que conviene ver.

    ./.venv/bin/python template/notebooks/preparar-datos.py

El dataset es Wine Quality (UCI, via OpenML): 6,497 vinos con 11 medidas
fisicoquimicas y una calificacion de 3 a 9 dada por catadores.
"""

import pathlib

import pandas as pd
from sklearn.datasets import fetch_openml

COLUMNAS = [
    "acidez_fija", "acidez_volatil", "acido_citrico", "azucar_residual",
    "cloruros", "dioxido_azufre_libre", "dioxido_azufre_total",
    "densidad", "pH", "sulfatos", "alcohol",
]

AQUI = pathlib.Path(__file__).resolve().parent
DESTINO = AQUI.parent / "data" / "datos.csv"


def main():
    # OpenML tiene los dos vinos por separado, y ahi esta la primera trampa:
    # el blanco codifica la calidad de 1 a 7 donde el tinto la codifica de 3 a
    # 9. Concatenarlos sin mirar produce un dataset silenciosamente corrupto:
    # el 99.9% de los blancos pareceria malo. Se comprueba contra la
    # distribucion conocida antes de seguir.
    tinto = fetch_openml(data_id=40691, as_frame=True, parser="auto").frame
    blanco = fetch_openml(data_id=40498, as_frame=True, parser="auto").frame

    tinto.columns = COLUMNAS + ["calidad"]
    blanco.columns = COLUMNAS + ["calidad"]
    tinto["calidad"] = tinto["calidad"].astype(int)
    blanco["calidad"] = blanco["calidad"].astype(int) + 2  # el desplazamiento

    esperado = [20, 163, 1457, 2198, 880, 175, 5]
    real = list(blanco["calidad"].value_counts().sort_index().values)
    assert real == esperado, f"el desplazamiento del blanco cambio: {real}"

    tinto["color"] = "tinto"
    blanco["color"] = "blanco"
    df = pd.concat([tinto, blanco], ignore_index=True)

    # El target. Un vino "bueno" es 7 o mas: es una decision de producto, no un
    # hecho del dataset, y mueve por completo el balance de clases.
    df["bueno"] = (df["calidad"] >= 7).astype(int)

    # Un corte ordinal para la segunda grafica del tablero.
    df["nivel_alcohol"] = pd.cut(
        df["alcohol"], bins=[0, 10, 11.5, 100], labels=[1, 2, 3]
    ).astype(int)

    # 'calidad' SALE. El target se derivo de ella: dejarla entre las features
    # seria fuga, y el modelo acertaria el 100% sin haber aprendido nada.
    df = df.drop(columns=["calidad"])

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DESTINO, index=False)

    print(f"{DESTINO}: {len(df)} filas, {len(df.columns)} columnas")
    print(f"  tasa de 'bueno': {df.bueno.mean():.4f}")
    print(df.groupby("color").bueno.agg(["count", "mean"]).round(4).to_string())


if __name__ == "__main__":
    main()
