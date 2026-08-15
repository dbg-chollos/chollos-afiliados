# Dónde estamos — La Liga

Apunte de situación para retomar el trabajo sin tener que reconstruirlo de
memoria (o para que otra sesión lo continúe). Actualizar al terminar cada paso.

## Hecho y comprobado

- **La app entera**, funcionando en local: registrar entradas en cuatro toques,
  puntos, cuatro clasificaciones, campeones del día/semana/mes, votaciones del
  1 al 10, exportar/importar. `node liga/pruebas.js` → 43 comprobaciones en
  verde, más recorridos completos en Chromium.
- **Foto por defecto** al registrar un lío o más lío, con modo alternativo de
  solo `@usuario` de Instagram y modo sin nada. Los ajustes que elige el
  usuario a mano se respetan; los que vienen de fábrica se actualizan solos.
- **Separada del sitio de chollos**, que es un requisito suyo explícito y
  firme: su familia entra en la web de ofertas. `docs/` no contiene ni una
  línea de la app, y `scripts/comprobar_separacion.py` lo verifica en cada
  build y en el workflow diario. Si algo se cuela, el despliegue falla.
- **Publicada** en <https://liga-de-los-pavos.netlify.app> (Netlify, gratis,
  desde la rama `claude/liga-ligues-app-xnp8da`, publicando `dist-liga/`).
  **Al tocar la app hay que regenerar esa carpeta** con
  `python scripts/preparar_web_liga.py` y hacer push, o el sitio no cambia.
- **Base de datos en Supabase**: creada y verificada por él con el esquema de
  `liga/supabase/esquema.sql` → 4 tablas, 12 políticas, bucket de fotos y sus
  3 políticas. Proyecto `arfiuoxsqgcnkwtalcwn`.
- **Liga compartida, entera y probada**: `liga/js/nube.js` (registro y entrada
  con correo y contraseña, crear/unirse por código, fotos, renovación de
  sesión), `liga/js/sincro.js` (subir lo propio, bajar lo de todos, fusionar) y
  las pantallas en Ajustes.
  Probada con un Supabase de mentira (`scratchpad/servidor-falso.js`) y dos
  navegadores a la vez: Dani crea la liga, Javi entra con el código, ve la
  clasificación, le baja la foto del servidor y la vota; Dani sincroniza y ve
  la nota. **Falta probarla contra el Supabase de verdad**, que solo puede
  hacerlo él: este entorno no puede salir a `*.supabase.co`.

## Lo siguiente

1. **Que lo pruebe él contra su Supabase**: registrarse, crear la liga, y que
   un amigo entre con el código. Es el único que puede: este entorno no llega
   a `*.supabase.co`.
2. **Conectar Netlify** a la rama y renombrar el sitio, para que sus amigos
   tengan una dirección propia que no dependa de nadie.
3. Ideas sueltas que quedaron apuntadas: rachas, mapa de sitios, exportar la
   clasificación como imagen para el grupo, histórico de ligas anteriores.

Ya hecho por él: base de datos creada y "Confirm email" desactivado.

## Cosas que no hay que deshacer sin pensarlo

- **Nada de la app en `docs/`.** Es lo que más le importa de todo esto.
- **Correo y contraseña, sin correos de por medio.** El plan gratuito manda muy
  pocos correos por hora: con código por email, si cuatro amigos se registran la
  misma noche, los últimos se quedan esperando. Un enlace mágico, además, abre
  el navegador en vez de la app instalada.
- La clave publicable va dentro de la app a propósito; la `service_role` no
  aparece en ningún sitio y no debe pedírsele.
- El código de liga se genera sin vocales ni caracteres confundibles: se dicta
  en voz alta de madrugada.
