/*
 * config.js — datos de conexion con Supabase.
 *
 * Mientras URL siga vacia, la app funciona exactamente igual que siempre: cada
 * liga vive en su movil y no se conecta a ningun sitio. En cuanto se rellena,
 * aparece la opcion de jugar la liga en comun.
 *
 * Los dos valores salen del panel de Supabase:
 *   - Project Settings -> Data API   -> "Project URL"
 *   - Project Settings -> API Keys   -> "Publishable key"
 *
 * La clave publicable esta pensada para ir dentro de la app, asi que no pasa
 * nada porque se vea: sin iniciar sesion no da acceso a nada, y quien inicia
 * sesion solo ve las ligas en las que esta. Lo que NO puede salir del panel
 * nunca es la "secret key": esa se salta todas las reglas.
 */
window.ConfigNube = {
  URL: 'https://arfiuoxsqgcnkwtalcwn.supabase.co',
  CLAVE_PUBLICA: 'sb_publishable_8VbyboEPPyPtAPhtz4_aow_1lVnEfLg'
};
