#!/usr/bin/env python3
"""Empaqueta la app de la liga en un unico archivo HTML.

    python scripts/construir_liga_html.py

Genera `liga/la-liga.html`: un solo archivo con el HTML, los estilos, el codigo
y el icono dentro. Se abre con doble clic y funciona sin instalar nada, asi que
se puede mandar por WhatsApp o correo y cada uno lo abre en su movil.

Con --cuerpo escribe la version sin las etiquetas <html>/<head>/<body>, que es
la que piden algunos alojamientos que envuelven la pagina por su cuenta.
"""

import argparse
import base64
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIGA = RAIZ / "liga"
SALIDA = LIGA / "la-liga.html"


def leer(ruta: Path) -> str:
    if not ruta.is_file():
        sys.exit(f"No encuentro {ruta}")
    return ruta.read_text(encoding="utf-8")


def inserta_recursos(html: str) -> str:
    """Sustituye los <link> y <script src> por su contenido."""

    def mete_css(match):
        css = leer(LIGA / match.group(1))
        return "<style>\n" + css.strip() + "\n</style>"

    def mete_js(match):
        js = leer(LIGA / match.group(1))
        # Sin este guion partido, un "</script>" dentro del codigo cerraria
        # la etiqueta antes de tiempo. Aqui no hay ninguno, pero mas vale.
        return "<script>\n" + js.strip().replace("</script>", "<\\/script>") + "\n</script>"

    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', mete_css, html)
    html = re.sub(r'<script src="([^"]+)"></script>', mete_js, html)

    # El icono, metido como data URI para no depender de ningun archivo suelto.
    # Se usa el de 180 para los dos: el de 512 pesaria medio mega el solo.
    icono = (LIGA / "icono-180.png").read_bytes()
    data_uri = "data:image/png;base64," + base64.b64encode(icono).decode("ascii")
    for suelto in ("icono-180.png", "icono-192.png"):
        html = html.replace(f'href="{suelto}"', f'href="{data_uri}"')

    # El manifiesto y el service worker necesitan archivos aparte servidos por
    # http, asi que en la version de un solo archivo no pintan nada.
    html = re.sub(r'\s*<link rel="manifest"[^>]*>', "", html)

    return html


def solo_cuerpo(html: str) -> str:
    """Deja titulo, estilos y contenido, sin el esqueleto del documento."""
    titulo = re.search(r"<title>.*?</title>", html, re.S)
    cuerpo = re.search(r"<body>(.*)</body>", html, re.S)
    if not cuerpo:
        sys.exit("No encuentro el <body> en index.html")
    estilos = re.findall(r"<style>.*?</style>", html, re.S)
    partes = ([titulo.group(0)] if titulo else []) + estilos + [cuerpo.group(1).strip()]
    return "\n".join(partes) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuerpo", action="store_true",
                        help="sin las etiquetas <html>/<head>/<body>")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()

    html = inserta_recursos(leer(LIGA / "index.html"))
    if args.cuerpo:
        html = solo_cuerpo(html)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(html, encoding="utf-8")

    kb = len(html.encode("utf-8")) / 1024
    print(f"Escrito {args.salida} ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
