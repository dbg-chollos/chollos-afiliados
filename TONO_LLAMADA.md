# Tono de llamada personalizado en el iPhone (llamadas normales + WhatsApp)

Objetivo: que cuando te llamen suene **el audio que tu elijas**, tanto en una llamada
normal como en una llamada de WhatsApp.

**Lo importante que debes saber antes de empezar:** en iPhone, WhatsApp **no tiene** un
ajuste propio de tono de llamada (en Android si lo tiene, en iOS no). Las llamadas de
WhatsApp suenan con **el tono de llamada del sistema**. Eso en realidad juega a tu favor:
poniendo tu audio como tono por defecto del iPhone, **suena en los dos casos** y solo
tienes que hacerlo una vez.

El proceso son 3 pasos:

1. Crear el tono (`.m4r`) a partir de tu video o audio → lo hace el script de este repo.
2. Pasarlo al iPhone.
3. Ponerlo como tono por defecto en Ajustes.

---

## Paso 1 — Crear el tono desde tu fichero

Necesitas **ffmpeg** instalado (es lo que recorta y convierte el audio):

| Sistema | Comando |
|---|---|
| macOS | `brew install ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` (cierra y abre la terminal despues) |
| Linux | `sudo apt install ffmpeg` |

Si no quieres instalarlo en el sistema, vale con `pip install imageio-ffmpeg`: el script
lo detecta solo.

Ahora genera el tono. Vale cualquier fichero local: `.mp4`, `.mkv`, `.mp3`, `.wav`,
`.m4a`, `.ogg`, un audio de WhatsApp, un video que hayas descargado...

```bash
# 30 segundos desde el principio del fichero
python scripts/tono_llamada.py mi_video.mp4

# el trozo exacto que quieres: 25 segundos empezando en el minuto 1:12
python scripts/tono_llamada.py cancion.mp3 --inicio 1:12 --duracion 25

# o marcando principio y final
python scripts/tono_llamada.py cancion.mp3 --inicio 1:12 --fin 1:35

# si vas a usar la via de GarageBand (paso 2, opcion A), genera tambien el mp3
python scripts/tono_llamada.py mi_video.mp4 --inicio 0:40 --duracion 28 --formato ambos
```

Opciones:

| Opcion | Para que sirve |
|---|---|
| `--inicio` | Segundo donde empieza el tono (`25`, `1:12`, `0:01:12`). |
| `--duracion` / `--fin` | Cuanto dura, o en que segundo termina. |
| `--salida` | Nombre del fichero resultante. |
| `--formato` | `m4r` (iPhone, por defecto), `mp3` (Android/GarageBand) o `ambos`. |
| `--sin-normalizar` | No igualar el volumen; deja el del original. |
| `--info` | Solo dice cuanto dura el fichero de entrada, para localizar el trozo. |

Detalles que ya hace el script por ti:

- **Maximo 30 segundos**: iOS no acepta tonos mas largos. Si pides mas, avisa y recorta.
- **Volumen igualado** para que no suene ni bajito ni saturado.
- **Fundido de entrada y de salida** para que no corte de golpe.
- Formato correcto para iOS: AAC a 44,1 kHz en contenedor `.m4r`.

Consejo: elige un trozo con "gancho" desde el segundo 0 (el estribillo, el grito, la
frase). Un tono empieza a sonar y a los 5 segundos ya lo has cogido, asi que lo que este
en el segundo 20 casi nunca lo vas a oir.

---

## Paso 2 — Pasar el tono al iPhone

Elige **una** de las tres vias segun lo que tengas a mano.

### Opcion A — Sin ordenador, con GarageBand (app gratuita de Apple)

Es la unica forma de hacerlo si solo tienes el iPhone. Usa el **`.mp3`** (GarageBand no
importa `.m4r`), por eso conviene generar `--formato ambos`.

1. Instala **GarageBand** desde la App Store (gratis).
2. Pasa el `.mp3` al iPhone: AirDrop desde el Mac, o guardandolo en **Archivos**
   (iCloud Drive, Google Drive, Telegram... vale cualquiera, pero que quede en Archivos).
3. Abre GarageBand → **+** → **Grabadora de audio** → toca el icono de **pistas**
   (los tres cuadraditos, arriba a la izquierda).
4. Toca el icono de **bucle** (arriba a la derecha) → pestaña **Archivos** →
   **Explorar elementos de la app Archivos** → elige tu mp3 → arrastralo a la pista.
5. Ajusta el trozo si hace falta (ya viene recortado por el script) y toca la flecha
   hacia abajo → **Mis canciones**.
6. En **Mis canciones**, manten pulsado el proyecto → **Compartir** → **Tono de llamada**
   → ponle nombre → **Exportar**.
7. Cuando termine, elige **Usar sonido como… → Tono de llamada estandar**. Con eso el
   paso 3 ya esta hecho.

### Opcion B — Con un Mac (macOS Catalina o posterior)

1. Conecta el iPhone por cable y desbloquealo (acepta **Confiar en este ordenador**).
2. Abre **Finder**: el iPhone aparece en la barra lateral.
3. Arrastra el fichero **`.m4r`** encima del iPhone en la barra lateral (o a la pestaña
   **General** del dispositivo). Se copia solo, sin sincronizar nada mas.

En macOS Mojave o anterior se hace igual pero desde **iTunes**, seccion **Tonos**.

### Opcion C — Con un PC Windows

1. Instala la app **Dispositivos Apple** desde la Microsoft Store (en Windows antiguos,
   **iTunes**).
2. Conecta el iPhone, desbloquealo y acepta **Confiar**.
3. En la app, entra en el iPhone → seccion **Tonos** → arrastra ahi el **`.m4r`** →
   **Sincronizar**.

---

## Paso 3 — Ponerlo como tono (esto es lo que cubre WhatsApp)

En el iPhone: **Ajustes → Sonidos y vibraciones → Tono de llamada** → selecciona tu tono
(aparece arriba del todo, encima de los de Apple).

Con eso ya suena tu audio:

- en las **llamadas normales** (telefonia), y
- en las **llamadas de WhatsApp**, porque WhatsApp en iOS usa este mismo tono.

Comprueba que funciona pidiendo a alguien que te llame por WhatsApp, o llamandote tu
desde otro telefono.

---

## Extras opcionales

- **Un tono distinto para una persona concreta** (llamadas normales): app **Contactos** →
  abre el contacto → **Editar** → **Tono de llamada**. Ojo: este tono por contacto se
  aplica a las llamadas de telefonia; las llamadas de WhatsApp siguen usando el tono
  general del sistema.
- **Sonido de los mensajes de WhatsApp** (no de las llamadas): **Ajustes → Notificaciones
  → WhatsApp → Sonidos**. Los tonos que has instalado tambien salen ahi, pero como aviso
  de mensaje conviene usar algo corto (2-3 segundos): genera otro con
  `--duracion 3`.
- **Android**, por si acaso: genera el `.mp3` (`--formato mp3`), copialo a la carpeta
  `Ringtones` del movil y seleccionalo en Ajustes → Sonido → Tono de llamada. En Android
  WhatsApp **si** tiene tono propio: WhatsApp → Ajustes → Notificaciones → **Llamadas →
  Tono**.

---

## Si algo no sale bien

| Problema | Causa habitual |
|---|---|
| El tono no aparece en Ajustes | Dura mas de 30 s, o no se copio (repite el paso 2 con el iPhone desbloqueado). |
| Aparece en "Musica" y no en "Tonos" | El fichero no es `.m4r`; regeneralo con `--formato m4r`. |
| Suena el tono de Apple en WhatsApp | No has cambiado el tono **por defecto** en Ajustes → Sonidos y vibraciones → Tono de llamada. |
| No suena nada al llamar | Interruptor de silencio activado, o un **Modo de concentracion** activo. |
| Se oye muy bajo o distorsionado | Prueba `--sin-normalizar`, o elige un trozo con menos picos. |
| `No he encontrado ffmpeg` | Instalalo con la tabla del paso 1 (o `pip install imageio-ffmpeg`). |
