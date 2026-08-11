#!/usr/bin/env python3
"""Sirve la carpeta liga/ en la red local para poder abrirla desde el movil.

    python scripts/servir_liga.py

Imprime la direccion a la que hay que entrar desde el movil (mismo wifi).
Hace falta servirla por http (y no abrir el archivo directamente) para que el
movil deje instalarla como app y funcione sin cobertura.
"""

import http.server
import os
import socket
import socketserver
import sys

PUERTO = int(os.environ.get("PUERTO", "8765"))
RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "liga")


def ip_local():
    """IP de esta maquina en el wifi (sin llegar a enviar nada)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=RAIZ, **kwargs)

    def end_headers(self):
        # Sin cache: si toco el codigo, al recargar quiero ver el cambio.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        pass


def main():
    if not os.path.isdir(RAIZ):
        sys.exit(f"No encuentro la carpeta {RAIZ}")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PUERTO), Handler) as httpd:
        print("La Liga esta servida en:")
        print(f"  este ordenador -> http://localhost:{PUERTO}/")
        print(f"  desde el movil -> http://{ip_local()}:{PUERTO}/   (mismo wifi)")
        print("\nCtrl+C para parar.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nParado.")


if __name__ == "__main__":
    main()
