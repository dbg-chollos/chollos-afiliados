"""
Punto de entrada unico del pipeline: genera contenido a partir de data/products.csv
y construye el sitio estatico en /docs. Esto es lo que ejecuta GitHub Actions cada dia,
y lo que puedes correr tu mismo en local con: python scripts/run_pipeline.py
"""
from comprobar_separacion import revisar
from generate_content import generate
from build_site import build

if __name__ == "__main__":
    articles = generate()
    build(articles)

    # El sitio de ofertas y la app de la liga son cosas separadas. Si algo de la
    # app acaba dentro de docs/, esto para aqui y el sitio no se publica.
    problemas = revisar()
    if problemas:
        raise SystemExit(
            "LA APP DE LA LIGA SE HA COLADO EN EL SITIO:\n  - "
            + "\n  - ".join(problemas)
            + "\n\nEl sitio NO se publica asi."
        )

    print(f"Pipeline completado: {len(articles)} articulos publicados en /docs")
