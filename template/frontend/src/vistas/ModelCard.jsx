export const meta = { titulo: "Model Card", orden: 4 };

import { useEffect, useState } from "react";
import { getModel } from "../api.js";

export default function ModelCard() {
  const [c, setC] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getModel().then(setC).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="estado error">{error}</div>;
  if (!c) return <div className="estado">Cargando...</div>;

  // De mayor a menor: la pregunta es "que pesa mas", asi que el orden
  // alfabetico que trae el JSON no sirve.
  const importancias = Object.entries(c.feature_importances || {}).sort(
    (a, b) => b[1] - a[1],
  );
  const maxImp = Math.max(...importancias.map(([, v]) => v), 0.0001);

  // Los conjuntos se muestran en el orden en que se usan, no en el que vienen.
  const ORDEN = ["train", "validation", "test"];
  const porOrden = (a, b) => ORDEN.indexOf(a[0]) - ORDEN.indexOf(b[0]);
  const splits = Object.entries(c.splits).sort(porOrden);
  const metricas = Object.entries(c.metrics).sort(porOrden);
  const columnasMetrica = [...new Set(metricas.flatMap(([, m]) => Object.keys(m)))];

  return (
    <>
      <p className="subtitulo-vista">
        Todo lo que hay aquí se lee de <code>metadata.json</code>. Nada está
        escrito a mano: si cambias el modelo, esta página cambia sola.
      </p>

      <div className="panel">
        <h2>Qué modelo es</h2>
        <p className="subtitulo">Rúbrica: configura y entrena el modelo</p>
        <dl className="ficha ancha">
          <dt>algoritmo</dt><dd>{c.algorithm}</dd>
          <dt>versión</dt><dd>{c.model_version}</dd>
          <dt>entrenado</dt><dd>{c.trained_at}</dd>
          <dt>scikit-learn</dt><dd>{c.sklearn_version}</dd>
          <dt>target</dt><dd>{c.target} (transformado con {c.target_transform})</dd>
          {c.task && (<><dt>tipo</dt><dd>{c.task}</dd></>)}
          {c.classes && (
            <><dt>clases</dt><dd>{c.classes.join(" · ")}</dd></>
          )}
          {c.umbral !== undefined && (
            <>
              <dt>umbral</dt>
              <dd>
                {c.umbral} — decisión de producto, no del modelo
              </dd>
            </>
          )}
        </dl>
      </div>

      <div className="panel">
        <h2>Con cuántos datos</h2>
        <p className="subtitulo">Rúbrica: separa en entrenamiento, validación y prueba</p>
        <div className="tarjetas sin-margen">
          {splits.map(([k, v]) => (
            <div className="tarjeta" key={k}>
              <div className="etiqueta">{k}</div>
              <div className="valor">{v.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>Qué tan bien predice</h2>
        <p className="subtitulo">Rúbrica: selecciona medidas de desempeño adecuadas</p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th className="txt">conjunto</th>
                {/* Las columnas salen de las claves que trae el contrato.
                    Un regresor manda rmse/mae/r2; un clasificador manda
                    accuracy/precision/recall/f1/roc_auc. Esta tabla no
                    necesita saber cual de los dos es. */}
                {columnasMetrica.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metricas.map(([nombre, m]) => (
                <tr key={nombre}>
                  <td className="txt">{nombre}</td>
                  {columnasMetrica.map((c) => (
                    <td key={c}>
                      {typeof m[c] === "number" ? m[c].toLocaleString() : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h2>Qué pesa en la predicción</h2>
        <p className="subtitulo">Rúbrica: interpreta los resultados del modelo</p>
        <div className="barras">
          {importancias.map(([nombre, valor]) => (
            <div className="barra-fila" key={nombre}>
              <span className="barra-etiqueta">{nombre}</span>
              <span className="barra-pista">
                <span
                  className="barra-relleno"
                  style={{ width: `${(valor / maxImp) * 100}%` }}
                />
              </span>
              <span className="barra-valor">{(valor * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>Modelos comparados</h2>
        <p className="subtitulo">Rúbrica: selecciona el modelo adecuado al problema</p>
        {(c.model_comparison || []).length === 0 ? (
          <div className="vacio">
            Sin datos. En tu reto, llena <code>model_comparison</code> en{" "}
            <code>metadata.json</code> con los candidatos que probaste y esta
            tabla aparece sola.
          </div>
        ) : (
          <pre>{JSON.stringify(c.model_comparison, null, 2)}</pre>
        )}
      </div>

      <div className="panel">
        <h2>Experimentos de hiperparámetros</h2>
        <p className="subtitulo">Rúbrica: ajusta los hiperparámetros</p>
        {(c.hyperparameter_experiments || []).length === 0 ? (
          <div className="vacio">
            Sin datos. Llena <code>hyperparameter_experiments</code> en tu reto.
          </div>
        ) : (
          <pre>{JSON.stringify(c.hyperparameter_experiments, null, 2)}</pre>
        )}
      </div>
    </>
  );
}
