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
- **Publicación propia** preparada: `dist-liga/` (ya construida en el repo) y
  `netlify.toml`. Pendiente de que él conecte Netlify.
- **Base de datos en Supabase**: creada y verificada por él con el esquema de
  `liga/supabase/esquema.sql` → 4 tablas, 12 políticas, bucket de fotos y sus
  3 políticas. Proyecto `arfiuoxsqgcnkwtalcwn`.
- **Capa de conexión** (`liga/js/nube.js`): registro y entrada con correo y
  contraseña, crear/unirse a liga, subir y bajar fotos, renovación de sesión. **Escrita
  pero sin probar contra el servidor.**

## Lo siguiente

1. **Acceso de red.** El entorno de la sesión bloquea `*.supabase.co`
   (`CONNECT tunnel failed, 403`), así que no se puede probar nada contra el
   servidor real. Él tiene que ponerlo en Network access → Custom.
2. **Probar `nube.js`** de punta a punta: pedir código, entrar, crear liga,
   unirse con el código, subir foto, votar.
3. **Pantallas de la nube en la app**: entrar con el correo, crear liga o meter
   código, y estado de sincronización. Aún no existen.
4. **Sincronizar** el estado local con el servidor (subir lo que falte, bajar
   lo de los demás, fusionar por id como ya hace `Datos.importar`).
5. **Desactivar "Confirm email"** en Supabase (Authentication → Sign In /
   Providers → Email). Sin eso nadie puede entrar tras registrarse.
6. Conectar Netlify a la rama y renombrar el sitio.

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
