# Boilerplate de la práctica

Los archivos del producto que **sí** cambian al cambiar de problema, ya escritos de forma
genérica. La práctica completa está en [docs/practica.md](../docs/practica.md).

No es una copia del proyecto. Lo que no está aquí es porque no se toca.

```
backend/
  s1_tablero.py     COMPLETA 1  · el bloque de configuración, vacío
  s2_modelo.py                  · predict_proba y el umbral (se lee, no se toca)
  s4_producto.py                · la explicación (genérica)
frontend/src/
  main.jsx          COMPLETA 4  · el título
  api.js                      · un nombre de parámetro (neighborhood → grupo)
  vistas/                     · los cuatro, genéricos. NO se tocan
notebooks/
  preparar-datos.py           · cómo se armó el CSV de ejemplo
  entrenar.py       COMPLETA 2 y 3 · features, categóricas, umbral
data/datos.csv                · el ejemplo, 6,497 vinos
```

## Qué demuestra el ejemplo

El dataset de ejemplo es **Wine Quality** (UCI, vía OpenML): 6,497 vinos portugueses con once
medidas fisicoquímicas. El target es `bueno` = calidad ≥ 7, una clasificación binaria con 19.7%
de positivos.

Los bloques de configuración llegan **vacíos**, con marcadores `COMPLETA 1` a `COMPLETA 4`, y
nada arranca hasta llenarlos — el error dice cuál falta. Son unas 15 líneas en total.

Los cuatro archivos de `frontend/src/vistas/` no se tocan **nunca**: el formulario, la Model
Card, el historial y las gráficas se rearman solos leyendo el contrato.

## Cómo correrlo tal cual

Desde la raíz del repositorio, para ver el destino antes de cambiar nada:

```bash
cp -r template/backend/* backend/
cp -r template/frontend/src/* frontend/src/
cp template/notebooks/entrenar.py notebooks/
cp template/data/datos.csv data/
```

Y luego llena los cuatro `COMPLETA`. Los valores para el ejemplo de vinos están en
[docs/profesor/practica-ensayo.md](../docs/profesor/practica-ensayo.md), listos para pegar.

⚠ Hazlo en una rama (`git checkout -b practica`), no sobre tu trabajo de las sesiones.

## Cómo se preparó el CSV

```bash
./.venv/bin/python template/notebooks/preparar-datos.py
```

Ese script está a la vista porque tiene dos decisiones que conviene ver: un desplazamiento de
etiquetas entre los dos datasets de origen que corrompe el resultado si no lo detectas, y la
eliminación de la columna de la que se derivó el target — que es fuga de datos.
