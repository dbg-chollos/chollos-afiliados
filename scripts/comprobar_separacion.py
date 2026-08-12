#!/usr/bin/env python3
"""Comprueba que la app de la liga NO se ha colado en el sitio de chollos.

    python scripts/comprobar_separacion.py

Se ejecuta solo al final del pipeline y en GitHub Actions. Si algun dia alguien
(yo incluido) vuelve a meter la app dentro de `docs/`, esto para el proceso y el
sitio NO se publica. Es a proposito que reviente en vez de avisar por lo bajo:
mas vale un despliegue fallido que una web publicada con lo que no toca.

El sitio de ofertas y la app son dos cosas separadas y tienen que seguir asi.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"

# Nombres de archivo que solo existen en la app.
ARCHIVOS_DE_LA_APP = {
    "reglas.js",
    "estadisticas.js",
    "datos.js",
    "manifest.webmanifest",
    "icono.svg",
    "la-liga.html",
    "esquema.sql",
}

# Trozos de texto que no aparecen en ninguna pagina de ofertas ni por casualidad.
# Se buscan en minusculas dentro de los archivos de texto de docs/.
HUELLAS = [
    "mas_lio",
    "modofoto",
    "djcuentacomodiscoteca",
    "unirse_a_liga",
    "la liga —",
]

EXTENSIONES_DE_TEXTO = {".html", ".js", ".css", ".json", ".xml", ".txt", ".webmanifest", ".sql", ".md"}


def revisar():
    problemas = []

    if not DOCS.is_dir():
        return ["No existe docs/: ejecuta antes el pipeline"]

    carpeta_liga = DOCS / "liga"
    if carpeta_liga.exists():
        problemas.append(f"Existe {carpeta_liga.relative_to(RAIZ)}: la app esta dentro del sitio")

    for ruta in DOCS.rglob("*"):
        if not ruta.is_file():
            continue
        relativa = ruta.relative_to(RAIZ)

        if ruta.name in ARCHIVOS_DE_LA_APP:
            problemas.append(f"{relativa}: es un archivo de la app")
            continue

        if ruta.suffix.lower() not in EXTENSIONES_DE_TEXTO:
            continue
        try:
            texto = ruta.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for huella in HUELLAS:
            if huella in texto:
                problemas.append(f"{relativa}: contiene '{huella}', que solo esta en la app")
                break

    return problemas


def main():
    problemas = revisar()
    if problemas:
        print("LA APP DE LA LIGA SE HA COLADO EN EL SITIO DE CHOLLOS:\n", file=sys.stderr)
        for p in problemas:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nEl sitio NO se publica asi. Saca eso de docs/ y vuelve a intentarlo.",
            file=sys.stderr,
        )
        sys.exit(1)

    total = sum(len(f) for _, _, f in os.walk(DOCS))
    print(f"Separacion correcta: {total} archivos en docs/ y ni rastro de la app.")


if __name__ == "__main__":
    main()
