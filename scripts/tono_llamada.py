"""
Crea un tono de llamada para iPhone (.m4r) a partir de cualquier video o audio local.

El tono resultante sirve a la vez para las llamadas normales y para las llamadas
de WhatsApp: en iOS WhatsApp usa el tono de llamada del sistema, asi que basta con
ponerlo como tono por defecto (los pasos estan en TONO_LLAMADA.md).

Uso basico (30 segundos desde el principio del fichero):
    python scripts/tono_llamada.py mi_video.mp4

Elegir el trozo exacto que quieres que suene:
    python scripts/tono_llamada.py cancion.mp3 --inicio 1:12 --duracion 25

Otras opciones utiles:
    --fin 1:40            en vez de --duracion, indica el segundo final
    --salida tono.m4r     nombre del fichero de salida
    --formato ambos       genera tambien un .mp3 (por si lo quieres en Android)
    --sin-normalizar      no iguala el volumen (deja el del original)
    --info                solo muestra la duracion del fichero de entrada y sale

Requisito: tener ffmpeg instalado (ver mensaje de ayuda si no lo esta).
"""
import argparse
import os
import shutil
import subprocess
import sys

# Apple no acepta tonos de llamada de mas de 30 segundos.
MAX_SEGUNDOS_M4R = 30.0
FUNDIDO_ENTRADA = 0.1
FUNDIDO_SALIDA = 1.0

AYUDA_FFMPEG = """No he encontrado ffmpeg, que es lo que recorta y convierte el audio.

Instalalo segun tu sistema:
  macOS    : brew install ffmpeg          (si no tienes brew: https://brew.sh)
  Windows  : winget install Gyan.FFmpeg   (y cierra y abre la terminal despues)
  Linux    : sudo apt install ffmpeg

Alternativa rapida sin instalar nada en el sistema:
  pip install imageio-ffmpeg
(este script lo detecta solo si esta instalado)"""


def buscar_ffmpeg(nombre):
    """Devuelve la ruta a ffmpeg/ffprobe: primero del sistema, si no del paquete imageio-ffmpeg."""
    ruta = shutil.which(nombre)
    if ruta:
        return ruta
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
    if nombre == "ffmpeg":
        return exe
    # imageio-ffmpeg solo trae ffmpeg; ffprobe se puede sustituir por el propio ffmpeg.
    return None


def parse_tiempo(valor):
    """Acepta segundos (90, 90.5) o mm:ss / hh:mm:ss (1:30, 0:01:30) y devuelve segundos."""
    texto = str(valor).strip().replace(",", ".")
    partes = texto.split(":")
    if len(partes) > 3:
        raise argparse.ArgumentTypeError(f"Tiempo no valido: {valor}")
    try:
        segundos = 0.0
        for parte in partes:
            segundos = segundos * 60 + float(parte)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Tiempo no valido: {valor} (usa 25, 1:12 o 0:01:12)")
    if segundos < 0:
        raise argparse.ArgumentTypeError("El tiempo no puede ser negativo")
    return segundos


def formatear(segundos):
    minutos, resto = divmod(segundos, 60)
    return f"{int(minutos)}:{resto:05.2f}"


def duracion_entrada(fichero):
    """Duracion en segundos del fichero de entrada, o None si no se puede averiguar."""
    ffprobe = buscar_ffmpeg("ffprobe")
    if not ffprobe:
        return None
    try:
        salida = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", fichero],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(salida)
    except (subprocess.CalledProcessError, ValueError):
        return None


def filtros_audio(duracion, normalizar):
    """Cadena de filtros de ffmpeg: fundidos de entrada/salida y volumen homogeneo."""
    filtros = []
    if normalizar:
        # loudnorm deja todos los tonos al mismo volumen percibido, sin saturar.
        filtros.append("loudnorm=I=-14:TP=-1.5:LRA=11")
    if duracion > FUNDIDO_ENTRADA * 2:
        filtros.append(f"afade=t=in:st=0:d={FUNDIDO_ENTRADA}")
    if duracion > FUNDIDO_SALIDA * 2:
        filtros.append(f"afade=t=out:st={duracion - FUNDIDO_SALIDA:.3f}:d={FUNDIDO_SALIDA}")
    return ",".join(filtros)


def convertir(ffmpeg, entrada, salida, inicio, duracion, normalizar, formato):
    orden = [ffmpeg, "-y", "-loglevel", "error", "-ss", f"{inicio:.3f}", "-i", entrada,
             "-t", f"{duracion:.3f}", "-vn", "-ar", "44100", "-ac", "2"]
    filtros = filtros_audio(duracion, normalizar)
    if filtros:
        orden += ["-af", filtros]
    if formato == "m4r":
        # -f ipod es el contenedor MP4/AAC que espera iOS para los tonos de llamada.
        orden += ["-c:a", "aac", "-b:a", "192k", "-f", "ipod"]
    else:
        orden += ["-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3"]
    orden.append(salida)

    resultado = subprocess.run(orden, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr.strip() or "ffmpeg fallo sin dar detalles")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convierte un trozo de un video o audio en un tono de llamada para iPhone (.m4r).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplo: python scripts/tono_llamada.py video.mp4 --inicio 1:12 --duracion 25",
    )
    parser.add_argument("entrada", help="Fichero de origen (mp4, mkv, mp3, wav, m4a, ogg...)")
    parser.add_argument("--inicio", type=parse_tiempo, default=0.0,
                        help="Segundo donde empieza el tono (25, 1:12...). Por defecto, el principio.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--duracion", type=parse_tiempo, help=f"Segundos de tono (maximo {MAX_SEGUNDOS_M4R:.0f}).")
    grupo.add_argument("--fin", type=parse_tiempo, help="Segundo donde termina el tono (alternativa a --duracion).")
    parser.add_argument("--salida", help="Fichero de salida. Por defecto, el mismo nombre con extension .m4r")
    parser.add_argument("--formato", choices=["m4r", "mp3", "ambos"], default="m4r",
                        help="m4r para iPhone (por defecto), mp3 para Android, ambos para los dos.")
    parser.add_argument("--sin-normalizar", dest="normalizar", action="store_false",
                        help="No igualar el volumen; deja el del original.")
    parser.add_argument("--info", action="store_true",
                        help="Solo mostrar la duracion del fichero de entrada y salir.")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.entrada):
        parser.error(f"No existe el fichero: {args.entrada}")

    ffmpeg = buscar_ffmpeg("ffmpeg")
    if not ffmpeg:
        print(AYUDA_FFMPEG, file=sys.stderr)
        return 1

    total = duracion_entrada(args.entrada)
    if args.info:
        if total is None:
            print("No he podido leer la duracion (falta ffprobe), pero el fichero se puede convertir igual.")
        else:
            print(f"{args.entrada}: {formatear(total)} ({total:.2f} segundos)")
        return 0

    if total is not None and args.inicio >= total:
        parser.error(f"--inicio ({formatear(args.inicio)}) es posterior al final del audio ({formatear(total)})")

    if args.fin is not None:
        if args.fin <= args.inicio:
            parser.error("--fin tiene que ser posterior a --inicio")
        duracion = args.fin - args.inicio
    elif args.duracion is not None:
        duracion = args.duracion
    else:
        duracion = MAX_SEGUNDOS_M4R

    if total is not None:
        duracion = min(duracion, total - args.inicio)
    if duracion <= 0:
        parser.error("El trozo seleccionado se queda en 0 segundos; revisa --inicio/--fin")

    formatos = ["m4r", "mp3"] if args.formato == "ambos" else [args.formato]
    if "m4r" in formatos and duracion > MAX_SEGUNDOS_M4R:
        print(f"Aviso: iOS no acepta tonos de mas de {MAX_SEGUNDOS_M4R:.0f} s; recorto a {MAX_SEGUNDOS_M4R:.0f} s.")
        duracion = MAX_SEGUNDOS_M4R

    base = args.salida or os.path.splitext(args.entrada)[0]
    if args.salida and len(formatos) == 1:
        salidas = {formatos[0]: args.salida}
    else:
        base = os.path.splitext(base)[0]
        salidas = {formato: f"{base}.{formato}" for formato in formatos}

    for formato, destino in salidas.items():
        try:
            convertir(ffmpeg, args.entrada, destino, args.inicio, duracion, args.normalizar, formato)
        except RuntimeError as error:
            print(f"Error convirtiendo a {formato}: {error}", file=sys.stderr)
            return 1
        tamano = os.path.getsize(destino) / 1024
        print(f"Listo: {destino} (duracion {formatear(duracion)}, {tamano:.0f} KB)")

    if "m4r" in salidas:
        print("Siguiente paso: pasarlo al iPhone y ponerlo como tono. Instrucciones en TONO_LLAMADA.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
