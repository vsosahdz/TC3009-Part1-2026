export const meta = { titulo: "Historial", orden: 3 };

import { useEffect, useState } from "react";
import { getHistory } from "../api.js";

const cuando = (iso) => new Date(iso).toLocaleString("es-MX");

export default function Historial() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getHistory(50).then(setDatos).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="estado error">{error}</div>;
  if (!datos) return <div className="estado">Cargando...</div>;

  // Las primeras cuatro features, para que la tabla quepa. El input completo
  // esta guardado; esto es solo lo que se muestra.
  const columnas = datos.rows.length ? Object.keys(datos.rows[0].input).slice(0, 4) : [];

  return (
    <>
      <p className="subtitulo-vista">
        Lo que este modelo ha estado prediciendo. No es el dataset de
        entrenamiento: es el uso real del producto.
      </p>

      <div className="panel">
        <h2>Predicciones recientes</h2>
        <p className="subtitulo">{datos.count} registradas</p>

        {datos.rows.length === 0 ? (
          <div className="vacio">
            Todavía no hay ninguna. Ve a <strong>Predecir</strong> y estima un
            precio: va a aparecer aquí.
          </div>
        ) : (
          <div className="scroll-x">
            {/* Las columnas del input salen de la primera fila, no escritas
                a mano: el historial guarda el input COMPLETO, asi que sabe
                solo como se llama cada cosa. Cambiar de dataset no toca esto. */}
            <table>
              <thead>
                <tr>
                  <th className="txt">Cuándo</th>
                  <th>Predicción</th>
                  {columnas.map((c) => (
                    <th key={c} className="txt">{c}</th>
                  ))}
                  <th className="txt">Modelo</th>
                </tr>
              </thead>
              <tbody>
                {datos.rows.map((f) => (
                  <tr key={f.prediction_id}>
                    <td className="txt">{cuando(f.created_at)}</td>
                    <td>
                      {typeof f.prediction === "number"
                        ? f.prediction.toLocaleString("es-MX", { maximumFractionDigits: 2 })
                        : String(f.prediction)}
                    </td>
                    {columnas.map((c) => (
                      <td key={c} className="txt">{String(f.input[c])}</td>
                    ))}
                    <td className="txt mono">{f.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
