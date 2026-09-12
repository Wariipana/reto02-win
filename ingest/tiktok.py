"""Ingesta de TikTok (@win_internet y competencia). Ver CLAUDE.md sección
"TikTok: cómo se resolvió el bloqueo del WAF" para el detalle de por qué
está partido en dos funciones con requisitos distintos.

fetch_video_detail(): sin sesión, evade el WAF vía SSR. Automatizable en el scheduler.
discover_ids_from_google(): sin sesión, pero incompleto y mezcla dark posts (ads).
Enumerar el catálogo completo de una cuenta requiere sesión de navegador real
(cookies) contra /api/post/item_list/ — no se automatiza aquí; ver notas al final
del archivo para el flujo manual/semi-manual de descubrimiento.
"""
import datetime
import json
import re

from playwright.sync_api import sync_playwright

from schema import Item, hash_author

CUENTAS = ["win_internet", "movistarperu_oficial", "entel_peru", "claro_peru"]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_REHYDRATION_RE = re.compile(
    r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.S
)


def _extract_universal_data(html):
    m = _REHYDRATION_RE.search(html)
    if not m:
        return None
    return json.loads(m.group(1))


def fetch_video_detail(video_url, page=None):
    """Devuelve un dict con desc/stats/createTime de un video ya conocido, o None
    si es un dark post (ad no orgánico) o si la página no cargó el detalle."""
    owns_browser = page is None
    ctx_cm = None
    if owns_browser:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=_UA)
        page = ctx.new_page()

    try:
        page.goto(video_url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        html = page.content()
        data = _extract_universal_data(html)
        if not data:
            return None
        vd = data.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {})
        item_info = vd.get("itemInfo")
        if not item_info:
            return None  # dark post u otro estado no disponible
        item = item_info["itemStruct"]
        stats = item.get("stats") or item.get("statsV2") or {}
        ct = item.get("createTime")
        fecha = (
            datetime.datetime.fromtimestamp(int(ct), datetime.timezone.utc).isoformat()
            if ct
            else ""
        )
        author = item.get("author", {})
        return Item(
            fuente="tiktok",
            texto=item.get("desc", ""),
            fecha=fecha,
            url=video_url,
            autor_hash=hash_author(author.get("uniqueId", "")),
            engagement={
                "diggCount": stats.get("diggCount", 0),
                "shareCount": stats.get("shareCount", 0),
                "commentCount": stats.get("commentCount", 0),
                "playCount": stats.get("playCount", 0),
            },
        ).to_dict()
    finally:
        if owns_browser:
            browser.close()
            pw.stop()


def fetch_video_details_batch(video_urls):
    """Reusa un solo browser/contexto para varias URLs (más rápido que abrir uno por video)."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=_UA)
        page = ctx.new_page()
        for url in video_urls:
            try:
                item = fetch_video_detail(url, page=page)
                if item:
                    results.append(item)
            except Exception as e:
                print(f"FAIL {url}: {e}")
        browser.close()
    return results


def discover_ids_from_google(cuenta, web_search_fn, max_results=20):
    """web_search_fn debe ser un callable(query) -> list[str] (URLs) provisto por
    el orquestador (ej. el tool WebSearch de Claude Code), ya que este módulo no
    trae su propio cliente de búsqueda. Filtra a URLs de video de la cuenta dada."""
    query = f"site:tiktok.com/@{cuenta}/video"
    urls = web_search_fn(query)
    return [u for u in urls if f"/@{cuenta}/video/" in u][:max_results]


if __name__ == "__main__":
    ejemplo = "https://www.tiktok.com/@win_internet/video/7678465298147691797"
    item = fetch_video_detail(ejemplo)
    print(json.dumps(item, indent=2, ensure_ascii=False))

# --- Flujo de descubrimiento con sesión (manual/semi-manual) ---
# 1. Iniciar sesión en TikTok en un navegador real (Chrome con extensión
#    Claude in Chrome, o cualquier navegador donde el usuario ya esté logueado).
# 2. Navegar a https://www.tiktok.com/@<cuenta> y hacer scroll para cargar el grid.
# 3. Ejecutar en la consola / vía javascript_tool:
#      document.querySelectorAll('a[href*="/video/"], a[href*="/photo/"]')
#        .forEach(a => window.__collected.add(a.href))
#    acumulando en un Set persistente en window mientras se hace scroll.
# 4. Exportar la lista de URLs y pasarlas a fetch_video_details_batch() de este
#    módulo, que ya no necesita la sesión.
# Cadencia sugerida: correr este paso 1x/día es suficiente dado que la cuenta
# postea a ~0.5-1 posts/día (ver medición en CLAUDE.md).
