export const meta = { titulo: "Historial", orden: 3 };

import { useEffect, useState } from "react";
import { getHistory } from "../api.js";

const pesos = (n) =>
  new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const cuando = (iso) => new Date(iso).toLocaleString("es-MX");

export default function Historial() {
  // Arranca con una tabla vacia y no en null, para que la vista se vea desde
  // el primer momento en lugar de quedarse en "Cargando..." hasta que escribas
  // el TODO 5.
  const [datos, setDatos] = useState({ count: 0, rows: [] });
  const [error, setError] = useState(null);

  // TODO 5 sesion 4: pedir el historial al montar.
  //
  // Una sola linea con getHistory(50). El mismo patron que ya usaste en el
  // tablero de la sesion 1: pedir al montar, guardar, y manejar el error.
  useEffect(() => {}, []);

  if (error) return <div className="estado error">{error}</div>;
  if (!datos) return <div className="estado">Cargando...</div>;

  return (
    <>
      <p className="subtitulo-vista">
        Lo que este modelo ha estado prediciendo. No es el dataset de
        entrenamiento: es el uso real del producto.
      </p>

      <div className="panel">
        <h2>Predicciones recientes</h2>
        <p className="subtitulo">{datos.count} registradas</p>

        {/* TODO 6 sesion 4: la tabla.
            Si datos.rows viene vacio, un mensaje que diga que hacer, no un
            "sin datos" a secas: el usuario acaba de llegar y no sabe que el
            historial se llena desde la pestaña Predecir.
            Si trae filas, una <table> dentro de <div className="scroll-x">
            con cuando / colonia / superficie / calidad / estimado / modelo.
            Las columnas de texto llevan className="txt". */}
        <div className="vacio">Aquí va tu tabla (TODO 6).</div>
      </div>
    </>
  );
}
