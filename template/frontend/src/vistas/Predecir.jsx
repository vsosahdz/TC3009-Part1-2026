export const meta = { titulo: "Predecir", orden: 2 };

import { useEffect, useState } from "react";
import { explicar, getModel, getStats, predecir } from "../api.js";

// Como se presenta el resultado depende del tipo de problema, y de nada mas.
// El contrato dice cual es en 'task'.
const pct = (n) => `${(n * 100).toFixed(1)}%`;

export default function Predecir() {
  const [contrato, setContrato] = useState(null);
  const [valores, setValores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [explicacion, setExplicacion] = useState(null);
  const [referencia, setReferencia] = useState(null);
  const [grupoCol, setGrupoCol] = useState(null);
  const [error, setError] = useState(null);

  // El formulario NO tiene una lista de campos escrita a mano: se construye
  // con lo que dice el contrato del modelo. Si el modelo gana una feature,
  // aqui aparece un campo. Si cambia el rango, cambia la ayuda.
  useEffect(() => {
    getModel()
      .then((c) => {
        setContrato(c);
        const iniciales = {};
        for (const f of c.features) {
          iniciales[f.name] = f.type === "num" ? f.median : f.allowed[0];
        }
        setValores(iniciales);
      })
      .catch((e) => setError(`No se pudo leer el contrato del modelo: ${e.message}`));

    // Cual de las features organiza el tablero. Solo para la comparacion.
    getStats().then((s) => setGrupoCol(s.meta?.grupo ?? null)).catch(() => {});
  }, []);

  async function enviar(evento) {
    evento.preventDefault();
    if (enviando) return; // sin envios duplicados mientras hay uno en curso

    setEnviando(true);
    setError(null);
    setResultado(null);
    setExplicacion(null);
    setReferencia(null);

    try {
      const r = await predecir(valores);
      setResultado(r);

      // Las dos peticiones de contexto van DESPUES y por separado: si
      // cualquiera falla, el usuario se queda con su resultado igual.
      explicar(valores, r.prediction)
        .then((e) => setExplicacion(e.explanation))
        .catch(() => setExplicacion(null));

      // Una prediccion sola no dice nada. Al lado de la tasa base de su grupo
      // --el mismo /api/stats de la sesion 1-- ya es una decision.
      //
      // Cual es "su grupo" no esta escrito aqui: lo dice el backend en
      // meta.grupo, asi que cambiar de dataset no toca este archivo.
      if (grupoCol) {
        getStats(valores[grupoCol])
          .then((s) => setReferencia(s))
          .catch(() => setReferencia(null));
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  if (error && !contrato) {
    return <div className="estado error">{error}</div>;
  }
  if (!contrato) {
    return <div className="estado">Cargando el contrato del modelo...</div>;
  }

  return (
    <>
      <p className="subtitulo-vista">
        Modelo {contrato.model_version} &middot; entrenado el{" "}
        {contrato.trained_at.slice(0, 10)}
      </p>

      <div className="dos-columnas">
        <form className="panel" onSubmit={enviar}>
          <h2>Datos del caso</h2>
          <p className="subtitulo">
            {contrato.features.length} campos, los que declara el contrato.
          </p>

          <div className="campos">
            {contrato.features.map((f) => (
              <label key={f.name} className="campo">
                <span className="etiqueta-campo">{f.name}</span>

                {f.type === "cat" ? (
                  <select
                    value={valores[f.name] ?? ""}
                    onChange={(e) =>
                      setValores({ ...valores, [f.name]: e.target.value })
                    }
                  >
                    {f.allowed.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    step="any"
                    value={valores[f.name] ?? ""}
                    onChange={(e) =>
                      setValores({ ...valores, [f.name]: e.target.value })
                    }
                  />
                )}

                {f.type === "num" && (
                  <span className="ayuda-campo">
                    entre {f.min.toLocaleString()} y {f.max.toLocaleString()}
                  </span>
                )}
              </label>
            ))}
          </div>

          <button type="submit" className="primario" disabled={enviando}>
            {enviando ? "Consultando el modelo..." : "Predecir"}
          </button>
        </form>

        <div className="panel">
          <h2>Resultado</h2>

          {error && (
            <div className="aviso-error">
              <strong>No se pudo predecir.</strong>
              <p>{error}</p>
            </div>
          )}

          {!error && !resultado && (
            <p className="vacio">
              Llena el formulario y presiona <em>Predecir</em>.
            </p>
          )}

          {resultado && (
            <>
              {contrato.task === "clasificacion" ? (
                <>
                  <div className="precio">{String(resultado.prediction)}</div>
                  <p className="subtitulo">
                    {pct(resultado.confidence)} de probabilidad de{" "}
                    <code>{contrato.target} = {String(contrato.clase_positiva)}</code>
                    {" · "}umbral {resultado.threshold}
                  </p>

                  {/* La barra importa: una clase sola esconde la diferencia
                      entre 0.51 y 0.99, que para quien decide no es lo mismo. */}
                  <div className="barras" style={{ margin: "14px 0" }}>
                    {Object.entries(resultado.probabilities).map(([clase, prob]) => (
                      <div className="barra-fila" key={clase}>
                        <span className="barra-etiqueta">{clase}</span>
                        <span className="barra-pista">
                          <span className="barra-relleno" style={{ width: `${prob * 100}%` }} />
                        </span>
                        <span className="barra-valor">{pct(prob)}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="precio">
                  {Number(resultado.prediction).toLocaleString("es-MX", {
                    maximumFractionDigits: 0,
                  })}
                </div>
              )}

              {resultado.warnings?.length > 0 && (
                <div className="aviso-cuidado">
                  {resultado.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </div>
              )}

              {referencia && (
                <p className="referencia">
                  {referencia.target.tipo === "categoria" ? (
                    <>
                      En <strong>{referencia.scope}</strong>, {referencia.count}{" "}
                      registros, la tasa base es{" "}
                      <strong>{pct(referencia.target.tasa)}</strong>. Este caso da{" "}
                      <strong>{pct(resultado.confidence)}</strong>.
                    </>
                  ) : (
                    <>
                      El promedio en <strong>{referencia.scope}</strong> es{" "}
                      {referencia.target.mean.toLocaleString("es-MX")} sobre{" "}
                      {referencia.count} registros.
                    </>
                  )}
                </p>
              )}

              {explicacion && <p className="explicacion">{explicacion}</p>}

              <dl className="ficha">
                <dt>modelo</dt>
                <dd>{resultado.model_version}</dd>
                <dt>id</dt>
                <dd className="mono">{resultado.prediction_id.slice(0, 8)}</dd>
              </dl>
            </>
          )}
        </div>
      </div>
    </>
  );
}
