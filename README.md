# ChollosTech — sitio de ofertas con afiliados (automatizado)

Sistema que publica automaticamente articulos de ofertas de productos con enlaces
de afiliado, sin coste de servidor. Corre entero sobre servicios gratuitos:
**GitHub Actions** genera el contenido cada dia y **GitHub Pages** lo publica.

## Como funciona (arquitectura)

```
data/products.csv  --->  scripts/generate_content.py  --->  scripts/build_site.py  --->  docs/
   (tus productos)          (crea los articulos)              (genera el HTML)      (lo que se publica)
```

GitHub Actions (`.github/workflows/build-deploy.yml`) ejecuta este pipeline
automaticamente todos los dias a las 06:00 UTC y sube los cambios. No necesitas
ningun servidor ni VPS: **coste de hosting = 0€**.

## Que he montado yo (ya hecho)

- Pipeline de generacion de contenido (plantillas variables, sin depender de ninguna API de pago).
- Generador de sitio estatico con paginas de producto, portada, sitemap.xml, robots.txt.
- Paginas legales (aviso legal, privacidad, cookies) — **con placeholders que debes rellenar**, ver mas abajo.
- Banner de cookies basico (GDPR).
- Automatizacion diaria con GitHub Actions.
- Datos de ejemplo en `data/products.csv` para que puedas ver el sitio funcionando ya.
- Probado localmente: `python scripts/run_pipeline.py` genera `docs/` sin errores.

## Lo que TU tienes que hacer (no lo puedo hacer yo por ti)

Esto no es pereza mia: crear cuentas, aceptar terminos legales o pagar con tu
tarjeta requiere tu identidad, así que son pasos que tienes que dar tu.

1. **Crear una cuenta de GitHub** (gratis) en github.com si no tienes.
2. **Crear un repositorio nuevo** (puede ser publico, asi Actions es 100% gratis sin limite)
   y subir esta carpeta:
   ```
   git remote add origin https://github.com/TU-USUARIO/chollos-afiliados.git
   git branch -M main
   git push -u origin main
   ```
3. **Activar GitHub Pages**: en el repo, Settings → Pages → Source: rama `main`, carpeta `/docs`.
   En unos minutos tu sitio estara en `https://TU-USUARIO.github.io/chollos-afiliados/`.
4. **Solicitar la cuenta de Amazon Afiliados (Amazon Associates)** en afiliados.amazon.es.
   - Importante: Amazon suele exigir que el sitio ya tenga contenido visible y, en 3 meses,
     al menos 3 ventas o revisan/cierran la cuenta. Por eso conviene tener el sitio ya
     publicado con contenido antes de solicitarlo.
   - Cuando te acepten, sustituye `TU-ID-AFILIADO-20` en `data/products.csv` por tu
     Tracking ID real.
5. **(Opcional, recomendado mas adelante) Comprar un dominio propio** (~10€/año) en
   Namecheap/IONOS/etc. y apuntarlo a GitHub Pages. Ayuda a la credibilidad y al SEO,
   pero no es obligatorio para empezar.
6. **Rellenar las paginas legales** en `docs/legal/` (o mejor, edita las plantillas en
   `scripts/build_site.py`, variable `LEGAL_PAGES`) con tu nombre/NIF/direccion/email real.
   Tener aviso legal y politica de privacidad es obligatorio en España para cualquier
   web con fines comerciales (LSSI-CE), independientemente de cuanto factures.
7. **Sustituir los productos de ejemplo** en `data/products.csv` por productos y precios
   REALES. Los que hay ahora son inventados solo para probar que el sistema funciona.

## Notas legales importantes (leelas, en serio)

- **No hagas scraping directo de las paginas de Amazon.** Sus terminos de servicio lo
  prohiben expresamente y pueden banearte la cuenta de afiliado. La via legitima es:
  1) rellenar `products.csv` a mano/con tus propias busquedas, o
  2) usar la API oficial "Product Advertising API" de Amazon (requiere cuenta de
     afiliado aprobada y activa con ventas — son sus reglas, no las mias).
- Todo enlace de afiliado debe llevar el aviso "contiene enlaces de afiliado" —
  ya esta incluido automaticamente en cada articulo.
- El banner de cookies incluido es una base minima, no un analisis legal completo.
  Si mas adelante añades Google Analytics o AdSense, revisa que cumples el RGPD
  (consentimiento previo antes de cargar esas cookies, no solo informar).

## Como anadir/actualizar ofertas

Edita `data/products.csv` (una fila = un producto/articulo) y haz commit + push.
GitHub Actions regenerara el sitio automaticamente en la siguiente ejecucion
programada, o puedes lanzarlo a mano desde la pestaña "Actions" del repo
("Run workflow").

## Publicacion automatica en Telegram (opcional, gratis)

`scripts/post_telegram.py` publica automaticamente cada producto NUEVO (no
repetido) en tu canal de Telegram, con foto, precio, descuento y enlace de
afiliado. Se ejecuta solo, dentro del mismo workflow diario de GitHub Actions.

Para activarlo:

1. Crea un canal de Telegram (publico, con un `@usuario`).
2. En Telegram, habla con **@BotFather** → `/newbot` → sigue los pasos → te da
   un token tipo `123456:ABC-...`.
3. Añade el bot como **administrador** de tu canal (para que pueda publicar).
4. En el repo de GitHub: Settings → Secrets and variables → Actions → **"New
   repository secret"**, y crea dos secretos:
   - `TELEGRAM_BOT_TOKEN` = el token que te dio BotFather
   - `TELEGRAM_CHAT_ID` = el `@usuario` publico de tu canal (ej. `@chollostech`)

**Importante:** el token del bot va SOLO en los secretos de GitHub, nunca en un
archivo del repo ni compartido por chat — quien tenga ese token puede publicar
en tu canal en tu nombre.

Sin esos dos secretos configurados, este paso simplemente no hace nada (no
rompe el resto del pipeline).

## Mejorar la calidad del texto (opcional, tiene un coste minimo)

Por defecto el texto se genera con plantillas, gratis. Si quieres texto mas
natural para mejorar el SEO, puedes activar el enriquecido con IA:

1. Instala la dependencia: `pip install anthropic`
2. Define la variable de entorno `ANTHROPIC_API_KEY` con tu clave.
3. Vuelve a correr el pipeline. El coste es de centimos de euro por articulo
   (modelo pequeno). Sin la clave definida, el sistema sigue funcionando igual,
   solo que con las plantillas base.

## App aparte: "La Liga" (carpeta `liga/`)

En este mismo repo, y sin ninguna relacion con el sitio de ofertas, esta la app
privada de la liga entre amigos: registrar entradas, puntos, clasificaciones y
campeon del dia/semana/mes. Instrucciones completas en
[`liga/README.md`](liga/README.md).

Arrancarla para usarla desde el movil (mismo wifi):

```bash
python scripts/servir_liga.py
```

**No se publica en este sitio.** El sitio de ofertas y la app son dos webs
distintas en dos dominios distintos, a proposito: `docs/` (lo que ve todo el
mundo) no contiene ni una linea de la app.

Para publicarla en su propio alojamiento, `scripts/preparar_web_liga.py` deja en
`dist-liga/` lo justo para servirla, y `netlify.toml` hace que Netlify lo coja
solo al conectar el repositorio. Ver `liga/README.md`.

## Que NO garantiza este sistema

Ningun ingreso esta garantizado. El trafico de un sitio nuevo tarda meses en
crecer con SEO, y no todo el que hace clic compra. Ver `PROYECCION.md` para
una estimacion realista mes a mes, con sus supuestos explicitos.
