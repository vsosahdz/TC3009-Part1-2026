"""El unico test que de verdad importa en este modulo.

Comprueba que el notebook y el servicio dicen LO MISMO para el mismo input.

    notebook                              servicio
    ────────────────────                  ─────────────────────────
    pipeline.predict(ejemplo)             POST /api/predict (example.json)
             │                                      │
             ▼                                      ▼
        141,334.96                            141,334.96
             └──────────── ¿iguales? ───────────────┘

Si no coinciden, la costura entre el modelo y el producto esta rota, y las
causas posibles son siempre las mismas:

  · el servicio transforma la entrada por su cuenta en lugar de dejar que lo
    haga el pipeline
  · se reemplazo pipeline.joblib sin regenerar example.json
  · la version de scikit-learn del servicio no es la del entrenamiento
  · la regla de decision quedo fuera del artefacto

QUE se compara depende del tipo de problema, y la diferencia importa:

    regresion      un numero, con tolerancia de centavos

    clasificacion  la clase, EXACTA, y ademas el vector de probabilidades
                   completo. Comparar solo la clase no sirve: 0.51 y 0.94
                   dan la misma clase y no son el mismo modelo. Un test que
                   solo mirara la etiqueta pasaria en verde con un modelo
                   completamente distinto debajo.

Se corre desde la raiz del proyecto:

    .venv/bin/python tests/test_paridad.py
"""

import importlib.util
import json
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TOLERANCIA = 0.01  # centavos: es el mismo modelo, no una aproximacion

fallos = 0


def ok(mensaje):
    print(f"  OK    {mensaje}")


def falla(mensaje):
    global fallos
    fallos += 1
    print(f"  FALLA {mensaje}")


def cargar_servicio():
    os.environ.setdefault("DATA_PATH", str(RAIZ / "data" / "train.csv"))
    os.environ.setdefault("MODEL_PATH", str(RAIZ / "artifacts"))
    sys.path.insert(0, str(RAIZ / "backend"))
    spec = importlib.util.spec_from_file_location("app", RAIZ / "backend" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# En clasificacion la tolerancia es mas estricta: no hay centavos que perdonar,
# es el mismo modelo dando el mismo vector o no lo es.
TOLERANCIA_PROBA = 1e-4


def comparar_clasificacion(ejemplo, cuerpo):
    """La clase EXACTA, y ademas todas las probabilidades.

    Comparar solo la clase es la trampa de este test. Un modelo que devuelve
    0.51 y otro que devuelve 0.94 dan la misma clase, y no son el mismo
    modelo: el primero esta dudando y el segundo no. Para quien decide --y
    para el umbral que eligieron-- esa diferencia es todo.
    """
    esperada = ejemplo["prediction"]
    obtenida = cuerpo["prediction"]

    p_esp = ejemplo.get("probabilities") or {}
    p_obt = cuerpo.get("probabilities") or {}

    print()
    print(f"  clase      notebook={esperada}   servicio={obtenida}")
    if p_esp:
        print()
        print(f"  {'clase':<12}{'notebook':>12}{'servicio':>12}{'dif':>12}")
        for clase in sorted(p_esp, key=str):
            a = float(p_esp[clase])
            b = float(p_obt.get(clase, float("nan")))
            print(f"  {clase:<12}{a:>12.6f}{b:>12.6f}{abs(a - b):>12.6f}")
    print()

    # La clase se compara como texto: puede ser 0, "0", True o "aprobado", y
    # lo que importa es que sean la misma etiqueta.
    if str(esperada) == str(obtenida):
        ok(f"la clase coincide ({obtenida})")
    else:
        falla(f"el notebook dice {esperada} y el servicio {obtenida}")

    if not p_esp:
        falla("example.json no trae 'probabilities': regeneralo con el entrenador")
        return
    if not p_obt:
        falla("/api/predict no devuelve 'probabilities': el producto esconde la duda")
        return

    if set(map(str, p_esp)) != set(map(str, p_obt)):
        falla(f"las clases no son las mismas: {sorted(p_esp)} vs {sorted(p_obt)}")
        return

    peor = max(abs(float(p_esp[c]) - float(p_obt[str(c)])) for c in p_esp)
    if peor <= TOLERANCIA_PROBA:
        ok(f"las {len(p_esp)} probabilidades coinciden (peor diferencia {peor:.2e})")
    else:
        falla(
            f"las probabilidades difieren hasta {peor:.6f}: la clase coincide "
            "por casualidad, el modelo no es el mismo"
        )

    suma = sum(float(v) for v in p_obt.values())
    if abs(suma - 1.0) <= 0.01:
        ok("las probabilidades suman 1")
    else:
        falla(f"las probabilidades suman {suma:.4f}: alguien las esta tocando")


def main():
    ruta_ejemplo = RAIZ / "artifacts" / "example.json"
    if not ruta_ejemplo.exists():
        print("\nNo existe artifacts/example.json.")
        print("Corre el notebook notebooks/01-entrenar-y-exportar.ipynb primero.\n")
        return 1

    ejemplo = json.loads(ruta_ejemplo.read_text())
    esperado = ejemplo["prediction"]

    contrato_json = json.loads((RAIZ / "artifacts" / "metadata.json").read_text())
    es_clasificacion = contrato_json.get("task") == "clasificacion"

    print()
    print("Paridad notebook <-> servicio")
    print("=" * 54)
    print(f"  problema: {contrato_json.get('task', 'regresion')}")

    modulo = cargar_servicio()
    cliente = modulo.app.test_client()

    respuesta = cliente.post("/api/predict", json=ejemplo["input"])
    if respuesta.status_code != 200:
        print(f"\n  El servicio respondio {respuesta.status_code}:")
        print(f"  {respuesta.get_json()}\n")
        return 1

    cuerpo = respuesta.get_json()
    obtenido = cuerpo["prediction"]

    if es_clasificacion:
        comparar_clasificacion(ejemplo, cuerpo)
    else:
        diferencia = abs(obtenido - esperado)
        print()
        print(f"  notebook   {esperado:>16,.2f}")
        print(f"  servicio   {obtenido:>16,.2f}")
        print(f"  diferencia {diferencia:>16,.2f}")
        print()
        if diferencia <= TOLERANCIA:
            ok("las predicciones coinciden")
        else:
            falla(f"difieren en mas de {TOLERANCIA}: la costura esta rota")

    # La version del modelo tiene que viajar con la prediccion.
    if cuerpo["model_version"] == ejemplo["model_version"]:
        ok(f"la version del modelo coincide ({cuerpo['model_version']})")
    else:
        falla(
            f"el servicio sirve {cuerpo['model_version']} y el ejemplo se genero "
            f"con {ejemplo['model_version']}: no es el mismo artefacto"
        )

    # La version de scikit-learn del contrato tiene que ser la instalada.
    import sklearn

    s2 = sys.modules.get("s2_modelo")
    entrenado_con = s2.contrato["sklearn_version"]
    if entrenado_con == sklearn.__version__:
        ok(f"scikit-learn coincide ({entrenado_con})")
    else:
        falla(
            f"entrenado con scikit-learn {entrenado_con}, "
            f"sirviendo con {sklearn.__version__}"
        )

    # La REGLA DE DECISION tiene que viajar con el modelo, no vivir en el
    # servicio. Cambia de forma segun el problema, pero es la misma idea:
    #
    #   regresion      la inversion del target va dentro del pipeline
    #   clasificacion  el umbral sale del contrato
    #
    # Si se escapa al servicio, cambiar el modelo exige recordar cambiar el
    # codigo, y nadie se acuerda.
    if es_clasificacion:
        umbral_contrato = float(contrato_json.get("umbral", 0.5))
        umbral_servido = cuerpo.get("threshold")
        if umbral_servido is None:
            falla("/api/predict no dice con que umbral decidio")
        elif abs(float(umbral_servido) - umbral_contrato) < 1e-9:
            ok(f"el umbral sale del contrato ({umbral_contrato})")
        else:
            falla(
                f"el servicio decidio con umbral {umbral_servido} y el contrato "
                f"dice {umbral_contrato}: la regla de decision esta escrita a mano"
            )
    else:
        fuente = (RAIZ / "backend" / "s2_modelo.py").read_text()
        if "expm1" in fuente:
            falla(
                "el servicio menciona expm1: la inversion del target deberia vivir "
                "dentro del pipeline, no aqui"
            )
        else:
            ok("el servicio no invierte el target por su cuenta")

    # El artefacto no debe arrastrar rutas absolutas del entorno de entrenamiento.
    crudo = (RAIZ / "artifacts" / "pipeline.joblib").read_bytes()
    for basura in (b"/Users/", b"/home/", b"C:\\\\"):
        if basura in crudo:
            falla(f"el artefacto contiene rutas absolutas ({basura.decode()})")
            break
    else:
        ok("el artefacto no contiene rutas absolutas")

    print()
    if fallos:
        print(f"{fallos} FALLAS: la costura esta rota.")
        return 1
    print("La costura esta sana.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
