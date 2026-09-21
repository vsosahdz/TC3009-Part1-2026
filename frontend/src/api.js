// La direccion del backend se deriva de donde se cargo esta pagina.
//
// No esta escrita a mano a proposito: la IP publica de la instancia EC2 cambia
// cada vez que el laboratorio la reinicia. Si aqui hubiera una IP literal, la
// aplicacion dejaria de funcionar en cada sesion nueva y el sintoma seria un
// error de red imposible de entender.
//
// Asi funciona igual en la instancia (IP publica) que en local (localhost),
// sin configurar nada.
//
// El puerto SI es distinto: el frontend vive en el 3000 y el backend en el
// 8080. Puertos distintos = origenes distintos = el navegador aplica CORS.
const API_BASE = `http://${window.location.hostname}:8080`;

async function get(path, params = {}) {
  const url = new URL(API_BASE + path);
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== null && valor !== undefined && valor !== "") {
      url.searchParams.set(clave, valor);
    }
  });

  const respuesta = await fetch(url);
  if (!respuesta.ok) {
    throw new Error(`${respuesta.status} al pedir ${path}`);
  }
  return respuesta.json();
}

export const getHealth = () => get("/api/health");
export const getStats = (neighborhood) => get("/api/stats", { neighborhood });
export const getData = (neighborhood, limit = 20) =>
  get("/api/data", { neighborhood, limit });
