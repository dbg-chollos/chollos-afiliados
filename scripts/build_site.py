"""
Construye el sitio estatico final en /docs a partir de la lista de articulos.
Se sirve directamente con GitHub Pages (gratis) apuntando a la carpeta /docs
de la rama main, sin necesidad de servidor propio.

Estructura del sitio generado:
  docs/index.html                  -> portada con buscador, destacados y categorias
  docs/categorias/{slug}.html      -> listado completo de una categoria
  docs/articulos/{slug}.html       -> ficha de producto con relacionados
  docs/products.json               -> indice para el buscador en vivo (cliente)
  docs/static/                     -> css/js compartidos
  docs/legal/                      -> aviso legal, privacidad, cookies
"""
import json
import os
import shutil
from datetime import date
from html import escape

from generate_content import CATEGORY_LABELS

BUILD_DATE = date.today().isoformat()


def jsonld(data):
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
SITE_NAME = "ChollosTech"
# Cambia esto si compras un dominio propio y lo apuntas a GitHub Pages.
SITE_URL = "https://dbg-chollos.github.io/chollos-afiliados"

# Archivo de verificacion de Google Search Console (metodo "Archivo HTML").
# Se regenera en cada build para que sobreviva al borrado de /docs.
GOOGLE_SITE_VERIFICATION_FILE = "google14138022b28dc005.html"

# Astronomia va primera mientras dure el tiron del eclipse del 12/08/2026.
# Este orden manda en el menu de categorias y en las secciones de la portada.
CATEGORY_ORDER = ["astronomia", "tecnologia", "hogar-limpieza", "deportes", "moda-belleza", "bebe-ninos", "mascotas"]

# Valoracion minima para que un producto salga destacado en la portada.
# Debe coincidir con la de post_telegram.py.
MIN_RATING = 3.5

BASE_CSS = """
:root {
  --bg: #f3f4f6;
  --surface: #ffffff;
  --ink: #16181d;
  --ink-muted: #5b616e;
  --line: #e4e6ea;
  --brand: #16213e;
  --accent: #ff9900;
  --accent-ink: #3d2604;
  --ok: #1c7a4d;
  --radius: 12px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; background: var(--bg); color: var(--ink); line-height: 1.5; }
a { color: inherit; }
img { max-width: 100%; display: block; }

/* Header + buscador */
.site-header { position: sticky; top: 0; z-index: 50; background: var(--brand); color: white; padding: 0.8rem 1rem; }
.site-header-inner { max-width: 1180px; margin: 0 auto; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.logo { color: white; text-decoration: none; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.01em; white-space: nowrap; }
.logo span { color: var(--accent); }
.search-wrap { position: relative; flex: 1; min-width: 220px; max-width: 520px; }
.search-input { width: 100%; padding: 0.6rem 0.9rem; border-radius: 999px; border: none; font-size: 0.95rem; outline: none; }
.search-results { position: absolute; top: calc(100% + 6px); left: 0; right: 0; background: var(--surface); color: var(--ink); border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.18); overflow: hidden; display: none; max-height: 60vh; overflow-y: auto; z-index: 60; }
.search-results.open { display: block; }
.search-result-item { display: flex; gap: 0.7rem; align-items: center; padding: 0.55rem 0.8rem; text-decoration: none; color: var(--ink); border-bottom: 1px solid var(--line); }
.search-result-item:last-child { border-bottom: none; }
.search-result-item:hover { background: #f7f7f9; }
.search-result-item img { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
.search-result-empty { padding: 0.9rem; color: var(--ink-muted); font-size: 0.9rem; }
.search-result-meta { font-size: 0.78rem; color: var(--ink-muted); }
.search-result-price { margin-left: auto; font-weight: 700; color: var(--accent); white-space: nowrap; }

/* Nav de categorias */
.cat-nav { background: #1f2a4d; padding: 0.6rem 1rem; }
.cat-nav-inner { max-width: 1180px; margin: 0 auto; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.cat-pill { color: #dfe3ee; text-decoration: none; font-size: 0.85rem; padding: 0.32rem 0.85rem; border-radius: 999px; background: rgba(255,255,255,0.08); white-space: nowrap; }
.cat-pill:hover, .cat-pill.active { background: var(--accent); color: var(--accent-ink); font-weight: 700; }

main { max-width: 1180px; margin: 0 auto; padding: 1.6rem 1rem 3rem; }

/* Breadcrumb */
.breadcrumb { font-size: 0.82rem; color: var(--ink-muted); margin-bottom: 1rem; }
.breadcrumb a { text-decoration: none; color: var(--ink-muted); }
.breadcrumb a:hover { text-decoration: underline; }

/* Secciones y grid de productos */
.section { margin: 2.2rem 0; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin-bottom: 0.9rem; }
.section-head h2 { font-size: 1.25rem; margin: 0; }
.section-head .see-all { font-size: 0.85rem; color: var(--accent-ink); background: #fff3e0; padding: 0.3rem 0.7rem; border-radius: 999px; text-decoration: none; font-weight: 600; white-space: nowrap; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }

.card { background: var(--surface); border-radius: var(--radius); padding: 0.9rem; text-decoration: none; color: inherit; border: 1px solid var(--line); transition: box-shadow .15s, transform .15s; display: flex; flex-direction: column; }
.card:hover { box-shadow: 0 10px 24px rgba(16,24,40,.10); transform: translateY(-2px); }
.card img { border-radius: 8px; aspect-ratio: 4/3; object-fit: cover; margin-bottom: 0.6rem; }
.card h3 { font-size: 0.95rem; margin: 0 0 0.5rem; line-height: 1.35; }
.card .cat-tag { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-muted); font-weight: 700; margin-bottom: 0.3rem; }
.rating { font-size: 0.8rem; color: var(--ink-muted); margin-bottom: 0.4rem; }
.rating b { color: var(--ink); }

.price-box { display: flex; align-items: center; gap: .5rem; margin-top: auto; padding-top: .5rem; flex-wrap: wrap; }
.price-old { text-decoration: line-through; color: var(--ink-muted); font-size: 0.85rem; }
.price-new { font-size: 1.25rem; font-weight: 800; color: var(--ink); }
.discount { background: #ffe4b8; color: var(--accent-ink); padding: .12rem .5rem; border-radius: 6px; font-size: .78rem; font-weight: 700; }

/* Pagina de producto */
.article-head h1 { font-size: 1.6rem; text-wrap: balance; margin-bottom: .3rem; }
.article-meta { color: var(--ink-muted); font-size: 0.85rem; margin-bottom: 1.2rem; }
.article-body img { border-radius: var(--radius); margin-bottom: 1rem; max-width: 360px; }
.cta-button { display: inline-block; background: var(--accent); color: var(--accent-ink); padding: .8rem 1.4rem; border-radius: 10px; text-decoration: none; font-weight: 800; margin-top: .5rem; }
.cta-button:hover { filter: brightness(1.05); }
.disclosure { font-size: .8rem; color: var(--ink-muted); margin-top: 1.5rem; border-top: 1px solid var(--line); padding-top: .8rem; }

.related-grid { margin-top: 2rem; }

/* Filtro y orden */
.filter-bar { display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 1.2rem; }
.filter-group { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.filter-label { font-size: 0.82rem; color: var(--ink-muted); font-weight: 600; }
.filter-btn { border: 1px solid var(--line); background: var(--bg); color: var(--ink); font-size: 0.82rem; padding: 0.32rem 0.75rem; border-radius: 999px; cursor: pointer; }
.filter-btn.active { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 700; }
.filter-select { border: 1px solid var(--line); background: var(--bg); color: var(--ink); font-size: 0.82rem; padding: 0.32rem 0.6rem; border-radius: 8px; }
.filter-count { margin-left: auto; font-size: 0.8rem; color: var(--ink-muted); }
.load-more-wrap { text-align: center; margin-top: 1.6rem; }
#load-more { border: 1px solid var(--line); background: var(--surface); color: var(--ink); font-weight: 700; padding: 0.7rem 1.6rem; border-radius: 10px; cursor: pointer; font-size: 0.9rem; }
#load-more:hover { border-color: var(--accent); }

footer { text-align: center; padding: 2rem 1rem; font-size: .85rem; color: var(--ink-muted); }
footer a { color: var(--ink-muted); }
footer p { max-width: 70ch; margin: 0 auto .7rem; font-size: .8rem; line-height: 1.5; }
.afiliado-aviso { font-weight: 700; color: var(--ink); }
.price-note { font-size: .8rem; color: var(--ink-muted); margin-top: -.4rem; }

#cookie-banner { position: fixed; bottom: 0; left: 0; right: 0; background: var(--brand); color: white; padding: 1rem; display: none; z-index: 999; }
#cookie-banner button { background: var(--accent); color: var(--accent-ink); border: none; padding: .5rem 1rem; border-radius: 6px; margin-left: 1rem; cursor: pointer; font-weight: bold; }

@media (max-width: 640px) {
  .search-wrap { order: 3; flex-basis: 100%; }
}
"""

SEARCH_JS = """
(function () {
  var input = document.getElementById('site-search');
  var box = document.getElementById('search-results');
  var root = window.SITE_ROOT || '';
  var data = null;

  function ensureData(cb) {
    if (data) return cb();
    fetch(root + 'products.json').then(function (r) { return r.json(); }).then(function (json) {
      data = json;
      cb();
    });
  }

  function render(query) {
    var q = query.trim().toLowerCase();
    if (!q) { box.classList.remove('open'); box.innerHTML = ''; return; }
    var matches = data.filter(function (p) {
      return p.name.toLowerCase().indexOf(q) !== -1 || p.category_label.toLowerCase().indexOf(q) !== -1;
    }).slice(0, 8);

    if (matches.length === 0) {
      box.innerHTML = '<div class="search-result-empty">Sin resultados para "' + query + '"</div>';
    } else {
      box.innerHTML = matches.map(function (p) {
        return '<a class="search-result-item" href="' + root + 'articulos/' + p.slug + '.html">' +
          '<img src="' + p.image_url + '" alt="">' +
          '<span><div>' + p.name + '</div><div class="search-result-meta">' + p.category_label + '</div></span>' +
          '<span class="search-result-price">' + p.price.toFixed(2) + '€</span>' +
          '</a>';
      }).join('');
    }
    box.classList.add('open');
  }

  input.addEventListener('input', function () {
    ensureData(function () { render(input.value); });
  });
  input.addEventListener('focus', function () {
    if (input.value) ensureData(function () { render(input.value); });
  });
  document.addEventListener('click', function (e) {
    if (!box.contains(e.target) && e.target !== input) box.classList.remove('open');
  });
})();
"""

FILTER_JS = """
(function () {
  var bar = document.querySelector('.filter-bar');
  if (!bar) return;
  var grid = document.querySelector('.card-grid');
  var buttons = Array.prototype.slice.call(bar.querySelectorAll('[data-min]'));
  var sortSelect = bar.querySelector('#sort-select');
  var loadMoreBtn = document.getElementById('load-more');
  var countEl = document.getElementById('result-count');
  var pageSize = 24;
  var shown = pageSize;

  function apply() {
    var activeBtn = bar.querySelector('[data-min].active') || buttons[0];
    var min = parseInt(activeBtn.dataset.min, 10);
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
    var visible = cards.filter(function (c) { return parseInt(c.dataset.discount, 10) >= min; });

    if (sortSelect) {
      var by = sortSelect.value;
      visible.sort(function (a, b) {
        if (by === 'discount') return parseInt(b.dataset.discount, 10) - parseInt(a.dataset.discount, 10);
        if (by === 'price-asc') return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
        if (by === 'price-desc') return parseFloat(b.dataset.price) - parseFloat(a.dataset.price);
        return 0;
      });
    }

    cards.forEach(function (c) { c.style.display = 'none'; });
    visible.forEach(function (c, i) {
      grid.appendChild(c);
      c.style.display = i < shown ? '' : 'none';
    });
    if (loadMoreBtn) loadMoreBtn.style.display = visible.length > shown ? '' : 'none';
    if (countEl) countEl.textContent = visible.length;
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      buttons.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      shown = pageSize;
      apply();
    });
  });
  if (sortSelect) sortSelect.addEventListener('change', function () { shown = pageSize; apply(); });
  if (loadMoreBtn) loadMoreBtn.addEventListener('click', function () { shown += pageSize; apply(); });

  apply();
})();
"""

COOKIE_JS = """
document.addEventListener('DOMContentLoaded', function () {
  if (!localStorage.getItem('cookie_ok')) {
    document.getElementById('cookie-banner').style.display = 'block';
  }
  document.getElementById('cookie-accept').addEventListener('click', function () {
    localStorage.setItem('cookie_ok', '1');
    document.getElementById('cookie-banner').style.display = 'none';
  });
});
"""

DISCOUNT_PLACEHOLDER = "https://via.placeholder.com/40x40?text=%20"


def cookie_banner_html(root):
    return f"""
<div id="cookie-banner">
  Usamos cookies propias y de terceros (enlaces de afiliado) para el funcionamiento de la web.
  Mas info en nuestra <a href="{root}legal/cookies.html" style="color:#ff9900">politica de cookies</a>.
  <button id="cookie-accept">Vale</button>
</div>
"""


def category_nav_html(root, active=None):
    pills = [f'<a class="cat-pill{" active" if active is None else ""}" href="{root}index.html">Inicio</a>']
    pills.append(f'<a class="cat-pill{" active" if active == "ofertas" else ""}" href="{root}ofertas.html">🔥 Todas las ofertas</a>')
    for slug in CATEGORY_ORDER:
        label = CATEGORY_LABELS[slug]
        cls = "cat-pill active" if slug == active else "cat-pill"
        pills.append(f'<a class="{cls}" href="{root}categorias/{slug}.html">{label}</a>')
    return f'<nav class="cat-nav"><div class="cat-nav-inner">{"".join(pills)}</div></nav>'


def header_html(root):
    return f"""
<header class="site-header">
  <div class="site-header-inner">
    <a class="logo" href="{root}index.html">Chollos<span>Tech</span></a>
    <div class="search-wrap">
      <input id="site-search" class="search-input" type="text" placeholder="Busca un producto o categoria (ej. auriculares, yoga...)" autocomplete="off">
      <div id="search-results" class="search-results"></div>
    </div>
  </div>
</header>
"""


def page_shell(title, body, description="", root="", active_category=None,
                canonical_path="", og_image=None, structured_data=""):
    """
    root = prefijo relativo hacia la carpeta docs/. "" si la pagina esta en la
    raiz (index.html), "../" si esta un nivel mas abajo (articulos/, categorias/, legal/).
    Rutas relativas porque GitHub Pages sirve este sitio bajo una subcarpeta
    (/chollos-afiliados/), no en la raiz del dominio.

    canonical_path = ruta desde la raiz del sitio (ej. "articulos/foo.html")
    usada para <link rel="canonical">, Open Graph y datos estructurados.
    """
    full_title = escape(f"{title} | {SITE_NAME}")
    desc = escape(description)
    canonical_url = f"{SITE_URL}/{canonical_path}"
    og_image_tag = f'<meta property="og:image" content="{og_image}">\n<meta name="twitter:image" content="{og_image}">' if og_image else ""
    og_type = "product" if canonical_path.startswith("articulos/") else "website"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical_url}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical_url}">
<meta name="twitter:card" content="{'summary_large_image' if og_image else 'summary'}">
<meta name="twitter:title" content="{full_title}">
<meta name="twitter:description" content="{desc}">
{og_image_tag}
<link rel="stylesheet" href="{root}static/style.css">
{structured_data}
</head>
<body>
<script>window.SITE_ROOT = "{root}";</script>
{header_html(root)}
{category_nav_html(root, active_category)}
<main>
{body}
</main>
<footer>
  <p class="afiliado-aviso">En calidad de Afiliado de Amazon, obtengo ingresos por las compras
  adscritas que cumplen los requisitos aplicables.</p>
  <p>Los precios y la disponibilidad mostrados son los vigentes en la fecha indicada en cada ficha
  y pueden cambiar en cualquier momento. El precio que aplica es el que figura en Amazon al
  completar la compra.</p>
  &copy; {SITE_NAME}. <a href="{root}legal/aviso-legal.html">Aviso legal</a> ·
  <a href="{root}legal/privacidad.html">Privacidad</a> ·
  <a href="{root}legal/cookies.html">Cookies</a>
</footer>
{cookie_banner_html(root)}
<script src="{root}static/cookie-consent.js"></script>
<script src="{root}static/search.js"></script>
<script src="{root}static/filter.js"></script>
</body>
</html>"""


def price_box_html(a):
    """
    Los productos sin rebaja se muestran solo con su precio, sin tachado ni
    etiqueta de descuento. Nunca inventamos un precio anterior para simular
    una oferta que no existe: eso es publicidad enganosa.
    """
    if a["discount_pct"] <= 0:
        return f'<div class="price-box"><span class="price-new">{a["price"]:.2f}€</span></div>'
    return (
        '<div class="price-box">'
        f'<span class="price-old">{a["old_price"]:.2f}€</span>'
        f'<span class="price-new">{a["price"]:.2f}€</span>'
        f'<span class="discount">-{a["discount_pct"]}%</span>'
        "</div>"
    )


def product_card(a, root):
    return f"""
    <a class="card" href="{root}articulos/{a['slug']}.html" data-discount="{a['discount_pct']}" data-price="{a['price']:.2f}">
      <img src="{a['image_url']}" alt="{a['name']}" loading="lazy">
      <div class="cat-tag">{a['category_label']}</div>
      <h3>{a['name']}</h3>
      <div class="rating">⭐ <b>{a['rating']}</b>/5</div>
      {price_box_html(a)}
    </a>"""


def filter_bar_html():
    return """
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Descuento minimo:</span>
        <button class="filter-btn active" data-min="0">Todos</button>
        <button class="filter-btn" data-min="10">10%+</button>
        <button class="filter-btn" data-min="25">25%+</button>
        <button class="filter-btn" data-min="40">40%+</button>
        <button class="filter-btn" data-min="60">60%+</button>
      </div>
      <div class="filter-group">
        <label class="filter-label" for="sort-select">Ordenar:</label>
        <select id="sort-select" class="filter-select">
          <option value="discount">Mayor descuento</option>
          <option value="price-asc">Precio: menor a mayor</option>
          <option value="price-desc">Precio: mayor a menor</option>
        </select>
      </div>
      <span class="filter-count"><span id="result-count"></span> productos</span>
    </div>
    """


def load_more_html():
    return '<div class="load-more-wrap"><button id="load-more">Cargar mas</button></div>'


def section_html(title, items, root, see_all_href=None):
    cards = "".join(product_card(a, root) for a in items)
    see_all = f'<a class="see-all" href="{see_all_href}">Ver todas →</a>' if see_all_href else ""
    return f"""
    <section class="section">
      <div class="section-head"><h2>{title}</h2>{see_all}</div>
      <div class="card-grid">{cards}</div>
    </section>"""


def rating_de(a):
    try:
        return float(a["rating"])
    except (TypeError, ValueError):
        return 0.0


def build_index(articles):
    # En portada solo destacamos productos bien valorados. Los demas siguen
    # accesibles desde su categoria, el buscador y "Todas las ofertas": no se
    # ocultan, simplemente no se promocionan en el escaparate.
    recomendables = [a for a in articles if rating_de(a) >= MIN_RATING]
    ofertas_dia = sorted(recomendables, key=lambda a: -a["discount_pct"])[:8]
    mas_demandados = [a for a in recomendables if a["featured"]][:8]

    body = f"""
    <div class="section" style="margin-top:0;">
      <p style="color:var(--ink-muted); max-width:60ch;">Reunimos en un solo sitio las mejores ofertas de Amazon
      seleccionadas cada dia: tecnologia, hogar, deporte, moda, bebe y mascotas. Usa el buscador de arriba o
      explora por categoria.</p>
    </div>
    {section_html("🔥 Ofertas del dia", ofertas_dia, root="")}
    {section_html("⭐ Los mas demandados", mas_demandados, root="")}
    """
    for slug in CATEGORY_ORDER:
        items = [a for a in articles if a["category"] == slug][:4]
        if items:
            body += section_html(CATEGORY_LABELS[slug], items, root="", see_all_href=f"categorias/{slug}.html")

    website_schema = jsonld({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL + "/",
    })
    return page_shell(
        "Inicio", body,
        "Las mejores ofertas de Amazon en tecnologia, hogar, deporte, moda, bebe y mascotas, seleccionadas cada dia.",
        root="", canonical_path="", structured_data=website_schema,
    )


def breadcrumb_schema(items):
    """items = lista de (nombre, url_absoluta)"""
    return jsonld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    })


def build_category_page(slug, items):
    label = CATEGORY_LABELS[slug]
    breadcrumb = f'<div class="breadcrumb"><a href="../index.html">Inicio</a> / {label}</div>'
    cards = "".join(product_card(a, root="../") for a in items)
    body = f"""
    {breadcrumb}
    <h1>{label}: todas las ofertas</h1>
    {filter_bar_html()}
    <div class="card-grid">{cards}</div>
    {load_more_html()}
    """
    schema = breadcrumb_schema([("Inicio", SITE_URL + "/"), (label, f"{SITE_URL}/categorias/{slug}.html")])
    return page_shell(
        label, body, f"Todas las ofertas de {label} seleccionadas cada dia.",
        root="../", active_category=slug, canonical_path=f"categorias/{slug}.html",
        structured_data=schema,
    )


def build_all_offers_page(articles):
    breadcrumb = '<div class="breadcrumb"><a href="index.html">Inicio</a> / Todas las ofertas</div>'
    cards = "".join(product_card(a, root="") for a in articles)
    body = f"""
    {breadcrumb}
    <h1>Todas las ofertas</h1>
    <p style="color:var(--ink-muted);">{len(articles)} productos con descuento en todas las categorias. Filtra por descuento minimo o cambia el orden.</p>
    {filter_bar_html()}
    <div class="card-grid">{cards}</div>
    {load_more_html()}
    """
    schema = breadcrumb_schema([("Inicio", SITE_URL + "/"), ("Todas las ofertas", f"{SITE_URL}/ofertas.html")])
    return page_shell(
        "Todas las ofertas", body, "Todas las ofertas de Amazon en un solo listado, filtrable por descuento.",
        root="", active_category="ofertas", canonical_path="ofertas.html", structured_data=schema,
    )


def build_article(a, all_articles):
    label = a["category_label"]
    breadcrumb = (
        f'<div class="breadcrumb"><a href="../index.html">Inicio</a> / '
        f'<a href="../categorias/{a["category"]}.html">{label}</a> / {a["name"]}</div>'
    )
    related = [x for x in all_articles if x["category"] == a["category"] and x["slug"] != a["slug"]][:4]
    related_html = f'<div class="related-grid">{section_html("Tambien te puede interesar", related, root="../")}</div>' if related else ""

    body = f"""
    {breadcrumb}
    <div class="article-head">
      <h1>{a['title']}</h1>
      <div class="article-meta">Publicado el {a['published']} · {label} · ⭐ {a['rating']}/5</div>
    </div>
    <div class="article-body">{a['body_html']}</div>
    {related_html}
    """
    canonical_path = f"articulos/{a['slug']}.html"
    schema_parts = [
        breadcrumb_schema([
            ("Inicio", SITE_URL + "/"),
            (label, f"{SITE_URL}/categorias/{a['category']}.html"),
            (a["name"], f"{SITE_URL}/{canonical_path}"),
        ]),
        jsonld({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": a["name"],
            "image": a["image_url"],
            "category": label,
            "offers": {
                "@type": "Offer",
                "url": a["affiliate_link"],
                "priceCurrency": "EUR",
                "price": f"{a['price']:.2f}",
                "availability": "https://schema.org/InStock",
            },
        }),
    ]
    return page_shell(
        a["title"], body, a["meta_description"], root="../", active_category=a["category"],
        canonical_path=canonical_path, og_image=a["image_url"], structured_data="\n".join(schema_parts),
    )


LEGAL_PAGES = {
    "aviso-legal.html": """
<h1>Aviso legal</h1>
<p><strong>[PLACEHOLDER: rellena con tus datos reales antes de publicar]</strong></p>
<p>Titular del sitio: [Tu nombre o razon social]<br>
NIF/DNI: [Tu NIF]<br>
Domicilio: [Tu direccion]<br>
Email de contacto: [tu email]</p>
<p>Este sitio participa en el Programa de Afiliados de Amazon EU, un programa de
publicidad para afiliados diseñado para ofrecer a sitios web un medio para obtener
comisiones por publicidad, publicitando e incluyendo enlaces a Amazon.es.</p>
""",
    "privacidad.html": """
<h1>Politica de privacidad</h1>
<p><strong>[PLACEHOLDER: revisa y completa antes de publicar]</strong></p>
<p>Este sitio no recopila datos personales mas alla de los estrictamente necesarios
para su funcionamiento tecnico (el buscador funciona en tu navegador, sin enviar tus
busquedas a ningun servidor). Si en el futuro se anaden formularios, analitica o
publicidad personalizada, esta politica debera actualizarse en consecuencia y,
si corresponde, solicitarse consentimiento explicito conforme al RGPD.</p>
""",
    "cookies.html": """
<h1>Politica de cookies</h1>
<p>Este sitio usa cookies propias tecnicas (para recordar tu eleccion sobre este aviso)
y cookies de terceros derivadas de los enlaces de afiliado a Amazon u otras tiendas,
que pueden usarse para atribuir correctamente las comisiones. Puedes deshabilitar las
cookies desde la configuracion de tu navegador.</p>
""",
}


def copy_liga_app():
    """Copia la app de la liga (carpeta liga/) dentro de docs/liga/.

    build() borra y regenera docs/ entero en cada ejecucion, asi que la app hay
    que volver a copiarla aqui: si se dejase a mano en docs/, el pipeline diario
    se la llevaria por delante. La app no lleva ningun dato dentro — cada movil
    guarda el suyo — asi que lo unico que se publica es el programa.
    """
    origen = os.path.join(os.path.dirname(__file__), "..", "liga")
    if not os.path.isdir(origen):
        return

    destino = os.path.join(OUT_DIR, "liga")
    shutil.copytree(
        origen,
        destino,
        # Ni las pruebas ni el README hacen falta en el sitio publicado.
        ignore=shutil.ignore_patterns("pruebas.js", "README.md", "la-liga.html"),
    )


def build(articles):
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(os.path.join(OUT_DIR, "static"))
    os.makedirs(os.path.join(OUT_DIR, "articulos"))
    os.makedirs(os.path.join(OUT_DIR, "categorias"))
    os.makedirs(os.path.join(OUT_DIR, "legal"))

    with open(os.path.join(OUT_DIR, "static", "style.css"), "w", encoding="utf-8") as f:
        f.write(BASE_CSS)
    with open(os.path.join(OUT_DIR, "static", "cookie-consent.js"), "w", encoding="utf-8") as f:
        f.write(COOKIE_JS)
    with open(os.path.join(OUT_DIR, "static", "search.js"), "w", encoding="utf-8") as f:
        f.write(SEARCH_JS)
    with open(os.path.join(OUT_DIR, "static", "filter.js"), "w", encoding="utf-8") as f:
        f.write(FILTER_JS)

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(articles))

    with open(os.path.join(OUT_DIR, "ofertas.html"), "w", encoding="utf-8") as f:
        f.write(build_all_offers_page(articles))

    for slug in CATEGORY_ORDER:
        items = [a for a in articles if a["category"] == slug]
        if not items:
            continue
        with open(os.path.join(OUT_DIR, "categorias", f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(build_category_page(slug, items))

    for a in articles:
        with open(os.path.join(OUT_DIR, "articulos", f"{a['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(build_article(a, articles))

    for name, content in LEGAL_PAGES.items():
        with open(os.path.join(OUT_DIR, "legal", name), "w", encoding="utf-8") as f:
            f.write(page_shell(
                name.replace(".html", "").replace("-", " ").title(), content, root="../",
                canonical_path=f"legal/{name}",
            ))

    products_index = [
        {
            "slug": a["slug"], "name": a["name"], "category": a["category"],
            "category_label": a["category_label"], "price": a["price"],
            "old_price": a["old_price"], "discount_pct": a["discount_pct"],
            "image_url": a["image_url"],
        }
        for a in articles
    ]
    with open(os.path.join(OUT_DIR, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products_index, f, ensure_ascii=False)

    urls = [SITE_URL + "/", f"{SITE_URL}/ofertas.html"] + [f"{SITE_URL}/articulos/{a['slug']}.html" for a in articles]
    urls += [f"{SITE_URL}/categorias/{slug}.html" for slug in CATEGORY_ORDER if any(a["category"] == slug for a in articles)]
    sitemap = "<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
    sitemap += "".join(f"<url><loc>{u}</loc><lastmod>{BUILD_DATE}</lastmod></url>" for u in urls)
    sitemap += "</urlset>"
    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)

    # La app de la liga se publica en /liga/ pero no es parte del sitio de
    # ofertas: fuera del sitemap y fuera de los buscadores.
    copy_liga_app()

    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(
            f"User-agent: *\nAllow: /\nDisallow: /liga/\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n"
        )

    with open(os.path.join(OUT_DIR, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    if GOOGLE_SITE_VERIFICATION_FILE:
        with open(os.path.join(OUT_DIR, GOOGLE_SITE_VERIFICATION_FILE), "w", encoding="utf-8") as f:
            f.write(f"google-site-verification: {GOOGLE_SITE_VERIFICATION_FILE}\n")

    print(f"Sitio generado en {OUT_DIR} con {len(articles)} articulos en {len(CATEGORY_ORDER)} categorias.")


if __name__ == "__main__":
    from generate_content import generate
    build(generate())
