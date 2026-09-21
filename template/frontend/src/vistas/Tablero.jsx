export const meta = { titulo: "Tablero", orden: 1 };

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getData, getStats } from "../api.js";

// Este archivo NO sabe de que trata tu dataset.
//
// En el curso, el tablero tenia "Colonia" y "Precio medio" escritos a mano por
// todos lados. Aqui los nombres llegan en el bloque 'meta' de /api/stats, que
// a su vez sale del AJUSTA 1 de backend/s1_tablero.py.
//
// Es la misma idea que ya viste con el formulario --derivarlo del contrato en
// vez de escribirlo a mano-- aplicada ahora a los datos. Si cambias de dataset,
// este archivo no se toca.

const SERIE = "#2a78d6";
const SERIE_APAGADA = "#86b6ef";
const EJE = "#c3c2b7";
const LINEA = "#e1e0d9";
const TINTA_APAGADA = "#898781";

const miles = (n) => new Intl.NumberFormat("es-MX").format(n);

/** Como se escribe la metrica depende del tipo de target, y solo de eso. */
function formatearMetrica(valor, tipo) {
  if (tipo === "categoria") return `${(valor * 100).toFixed(1)}%`;
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 0 }).format(valor);
}

/** Como se llama la metrica, para los ejes y los tooltips. */
function nombreMetrica(m) {
  return m.tipo_target === "categoria"
    ? `% ${m.target} = ${m.clase_positiva}`
    : `${m.target} promedio`;
}

function TooltipMetrica({ active, payload, label, m }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tooltip">
      <div className="t-titulo">{label}</div>
      <div className="t-linea">
        {nombreMetrica(m)}: {formatearMetrica(d.metrica, m.tipo_target)}
      </div>
      <div className="t-linea">{miles(d.count)} registros</div>
    </div>
  );
}

export default function Tablero() {
  const [grupo, setGrupo] = useState("");
  const [stats, setStats] = useState(null);
  const [filas, setFilas] = useState([]);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    Promise.all([getStats(grupo), getData(grupo, 20)])
      .then(([s, d]) => {
        if (!vigente) return;
        setStats(s);
        setFilas(d.rows);
        setError(null);
      })
      .catch((e) => vigente && setError(e.message))
      .finally(() => vigente && setCargando(false));
    return () => { vigente = false; };
  }, [grupo]);

  if (error) {
    return (
      <div className="estado error">
        <p>No se pudo hablar con la API: {error}</p>
        <p>
          Revisa que el backend este corriendo en el puerto 8080 y que la
          consola del navegador no muestre un error de CORS.
        </p>
      </div>
    );
  }
  if (cargando && !stats) return <div className="estado">Cargando...</div>;

  const m = stats.meta;
  const valores = stats.by_grupo.map((d) => String(d.valor)).sort();
  const esCategoria = m.tipo_target === "categoria";

  return (
    <>
      <div className="filtros">
        <label htmlFor="grupo">{m.grupo}</label>
        <select id="grupo" value={grupo} onChange={(e) => setGrupo(e.target.value)}>
          <option value="">Todos</option>
          {valores.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        {grupo && <button onClick={() => setGrupo("")}>Quitar filtro</button>}
        <span style={{ color: TINTA_APAGADA, fontSize: 13 }}>
          {miles(stats.count)} registros en el alcance actual
        </span>
      </div>

      {/* --- Las cifras grandes --- */}
      <div className="tarjetas">
        {esCategoria ? (
          <>
            <div className="tarjeta">
              <div className="etiqueta">{m.target} = {m.clase_positiva}</div>
              <div className="valor">{formatearMetrica(stats.target.tasa, "categoria")}</div>
            </div>
            {Object.entries(stats.target.clases).map(([clase, n]) => (
              <div className="tarjeta" key={clase}>
                <div className="etiqueta">clase {clase}</div>
                <div className="valor">{miles(n)}</div>
              </div>
            ))}
          </>
        ) : (
          <>
            <div className="tarjeta">
              <div className="etiqueta">{m.target} promedio</div>
              <div className="valor">{formatearMetrica(stats.target.mean, "numero")}</div>
            </div>
            <div className="tarjeta">
              <div className="etiqueta">mediana</div>
              <div className="valor">{formatearMetrica(stats.target.median, "numero")}</div>
            </div>
            <div className="tarjeta">
              <div className="etiqueta">maximo</div>
              <div className="valor">{formatearMetrica(stats.target.max, "numero")}</div>
            </div>
          </>
        )}
      </div>

      {/* --- Grafica 1: comparacion entre grupos. Siempre global: es el eje
            de comparacion, y filtrarlo a un solo grupo lo dejaria sin sentido. --- */}
      <div className="panel">
        <h2>{nombreMetrica(m)} por {m.grupo}</h2>
        <p className="subtitulo">
          Los {stats.by_grupo.length} valores de <code>{m.grupo}</code>, de mayor a menor.
          {grupo && " El seleccionado va resaltado."}
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={stats.by_grupo} margin={{ top: 4, right: 8, bottom: 40, left: 8 }}>
            <CartesianGrid stroke={LINEA} vertical={false} />
            <XAxis dataKey="valor" angle={-45} textAnchor="end" height={60}
              tick={{ fontSize: 11, fill: TINTA_APAGADA }} stroke={EJE} interval={0} />
            <YAxis tick={{ fontSize: 11, fill: TINTA_APAGADA }} stroke={EJE}
              tickFormatter={(v) => formatearMetrica(v, m.tipo_target)} width={62} />
            <Tooltip content={<TooltipMetrica m={m} />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
            <Bar dataKey="metrica" isAnimationActive={false}>
              {stats.by_grupo.map((d) => (
                <Cell key={String(d.valor)}
                  fill={!grupo || grupo === String(d.valor) ? SERIE : SERIE_APAGADA} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* --- Grafica 2: el corte ordinal. Este SI respeta el filtro: dentro de
            un grupo, la pregunta sigue teniendo sentido. --- */}
      <div className="panel">
        <h2>{nombreMetrica(m)} por {m.corte}</h2>
        <p className="subtitulo">
          {grupo ? `Solo ${m.grupo} = ${grupo}.` : "Sobre todos los registros."}
        </p>
        {stats.by_corte.length === 0 ? (
          <div className="vacio">Sin registros en este alcance.</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.by_corte} margin={{ top: 4, right: 8, bottom: 8, left: 8 }}>
              <CartesianGrid stroke={LINEA} vertical={false} />
              <XAxis dataKey="valor" tick={{ fontSize: 11, fill: TINTA_APAGADA }} stroke={EJE} />
              <YAxis tick={{ fontSize: 11, fill: TINTA_APAGADA }} stroke={EJE}
                tickFormatter={(v) => formatearMetrica(v, m.tipo_target)} width={62} />
              <Tooltip content={<TooltipMetrica m={m} />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
              <Bar dataKey="metrica" fill={SERIE} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* --- La tabla. Las columnas tambien salen del backend. --- */}
      <div className="panel">
        <h2>Registros</h2>
        <p className="subtitulo">
          Los primeros {filas.length}{grupo && ` de ${m.grupo} = ${grupo}`}.
        </p>
        {filas.length === 0 ? (
          <div className="vacio">Sin coincidencias.</div>
        ) : (
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  {Object.keys(filas[0]).map((c) => (
                    <th key={c} className={typeof filas[0][c] === "string" ? "txt" : ""}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filas.map((fila, i) => (
                  <tr key={i}>
                    {Object.keys(filas[0]).map((c) => (
                      <td key={c} className={typeof fila[c] === "string" ? "txt" : ""}>
                        {fila[c] === null ? "—" : String(fila[c])}
                      </td>
                    ))}
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
