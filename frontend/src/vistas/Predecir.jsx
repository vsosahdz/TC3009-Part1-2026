export const meta = { titulo: "Predecir", orden: 2 };

import { useEffect, useState } from "react";
import { explicar, getModel, getStats, predecir } from "../api.js";

const pesos = (n) =>
  new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

export default function Predecir() {
  const [contrato, setContrato] = useState(null);
  const [valores, setValores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [explicacion, setExplicacion] = useState(null);
  const [referencia, setReferencia] = useState(null);
  const [error, setError] = useState(null);

  // El formulario NO tiene una lista de campos escrita a mano: se construye
  // con lo que dice el contrato del modelo. Si el modelo gana una feature,
  // aqui aparece un campo. Si cambia el rango, cambia la ayuda.
  // TODO 6 sesion 3: leer el contrato al montar la vista.
  //
  // Pide /api/model con getModel(), guardalo en 'contrato', y arma los valores
  // iniciales: la mediana si la feature es numerica, el primer valor permitido
  // si es categorica. Un fallo aqui deja la vista inservible, asi que tiene que
  // acabar en setError con un mensaje que diga que no se pudo leer el contrato.
  useEffect(() => {}, []);

  // TODO 7 sesion 3: enviar el formulario.
  //
  // Tres estados, y los tres tienen que verse: enviando, error, resultado.
  //
  //   · evento.preventDefault(), o el navegador recarga la pagina
  //   · si ya hay un envio en curso, no mandes otro
  //   · limpia el resultado anterior antes de pedir el nuevo
  //   · la explicacion y la referencia se piden DESPUES y por separado: si
  //     cualquiera falla, el usuario se queda con su precio igual
  async function enviar(evento) {
    evento.preventDefault();
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
          <h2>Datos de la casa</h2>
          <p className="subtitulo">
            Diez campos. Son los que un vendedor conoce sin medir nada.
          </p>

          {/* TODO 8 sesion 3: los campos.
              Recorre contrato.features. Cada una trae 'name' y 'type'.
              Las 'cat' llevan <select> con f.allowed; las 'num' un
              <input type="number"> y debajo la ayuda con f.min y f.max.
              Son inputs controlados: value sale de 'valores', onChange lo
              actualiza. */}
          <div className="campos"></div>

          <button type="submit" className="primario" disabled={enviando}>
            {enviando ? "Consultando el modelo..." : "Estimar precio"}
          </button>
        </form>

        <div className="panel">
          <h2>Estimación</h2>

          {error && (
            <div className="aviso-error">
              <strong>No se pudo estimar.</strong>
              <p>{error}</p>
            </div>
          )}

          {!error && !resultado && (
            <p className="vacio">
              Llena el formulario y presiona <em>Estimar precio</em>.
            </p>
          )}

          {resultado && (
            <>
              <div className="precio">{pesos(resultado.prediction)}</div>

              {resultado.warnings?.length > 0 && (
                <div className="aviso-cuidado">
                  {resultado.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </div>
              )}

              {referencia && (
                <p className="referencia">
                  El promedio en <strong>{referencia.scope}</strong> es{" "}
                  {pesos(referencia.target.mean)} sobre {referencia.count} casas
                  vendidas — esta casa está{" "}
                  <strong>
                    {Math.abs(
                      Math.round(
                        ((resultado.prediction - referencia.target.mean) /
                          referencia.target.mean) *
                          100,
                      ),
                    )}
                    %{" "}
                    {resultado.prediction >= referencia.target.mean
                      ? "arriba"
                      : "abajo"}
                  </strong>
                  .
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
