/*
 * config.js — datos de conexion con Supabase.
 *
 * Mientras esto siga vacio, la app funciona exactamente igual que hasta ahora:
 * cada liga vive en su movil y no se conecta a ningun sitio. En cuanto se
 * rellenan los dos valores, aparece la opcion de jugar la liga en comun.
 *
 * Los dos valores salen de Supabase → Project Settings → API:
 *   - "Project URL"        -> URL
 *   - "anon public" (key)  -> CLAVE_PUBLICA
 *
 * La clave "anon public" esta pensada para ir dentro de la app, asi que no pasa
 * nada porque se vea: sin iniciar sesion no da acceso a nada, y quien inicia
 * sesion solo ve las ligas en las que esta. Lo que NO puede salir de tu panel
 * de Supabase nunca es la clave "service_role": esa se salta todas las reglas.
 */
window.ConfigNube = {
  URL: '',
  CLAVE_PUBLICA: ''
};
