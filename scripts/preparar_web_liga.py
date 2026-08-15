#!/usr/bin/env python3
"""Deja la app de la liga lista para subir a un alojamiento propio.

    python scripts/preparar_web_liga.py

Escribe la carpeta `dist-liga/` con lo justo para servirla: el index, los
estilos, el codigo, el icono, el manifiesto y el service worker. Se queda fuera
todo lo que no pinta nada en un sitio publicado (el README, las pruebas, el SQL
de Supabase y la version de archivo unico).

Esta carpeta es la que se sube a Netlify, Vercel o donde sea. NO se publica en
el sitio de ofertas: son cosas distintas y comparten dominio con nada.
"""

import os
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIGA = RAIZ / "liga"
SALIDA = RAIZ / "dist-liga"

# Lo que se sube. Cualquier cosa que no este aqui, no viaja.
CONTENIDO = [
    "index.html",
    "icono-180.png",
    "icono-192.png",
    "icono-512.png",
    "manifest.webmanifest",
    "sw.js",
    "css",
    "js",
]


def main():
    if not LIGA.is_dir():
        sys.exit(f"No encuentro {LIGA}")

    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SALIDA.mkdir(parents=True)

    for nombre in CONTENIDO:
        origen = LIGA / nombre
        destino = SALIDA / nombre
        if origen.is_dir():
            shutil.copytree(origen, destino)
        elif origen.is_file():
            shutil.copy2(origen, destino)
        else:
            sys.exit(f"Falta {origen}")

    # Que ningun buscador la indexe aunque alguien enlace la direccion.
    (SALIDA / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    archivos = sum(len(f) for _, _, f in os.walk(SALIDA))
    peso = sum(p.stat().st_size for p in SALIDA.rglob("*") if p.is_file()) / 1024
    print(f"Listo: {SALIDA} ({archivos} archivos, {peso:.0f} KB)")


if __name__ == "__main__":
    main()
