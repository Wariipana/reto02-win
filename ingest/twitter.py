"""Ingesta de X/Twitter vía scraping con sesión de cookies (ver
CLAUDE.md, sección X/Twitter: por qué no hay atajo gratuito). No usa la API
oficial (sin tier gratuito desde feb-2026) ni twikit (requiere credenciales
de app además de cuenta) — directamente Playwright + storage_state, igual
patrón que ya funcionó para TikTok.

A diferencia de TikTok, la sesión de X no mostró ningún captcha/verificación
anti-bot en la primera prueba (ver CLAUDE.md para el detalle). Riesgo de ToS
documentado: X prohíbe el scraping de forma similar a las demás plataformas;
se acepta el mismo tipo de riesgo ya asumido con TikTok.
"""
import datetime
import re
import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import Item, hash_author  # noqa: E402

SESSION_STATE_PATH = Path(__file__).resolve().parent.parent / ".sessions" / "twitter_state.json"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

QUERIES = ["WIN internet Peru", "WIN fibra Peru", "WIN OSIPTEL", "Wi-Net Telecom"]

_STATS_LABELS = ["replies", "reposts", "likes", "views"]  # orden aproximado en el DOM de X


def _search_url(query, modo="live"):
    q = urllib.parse.quote(query)
    return f"https://x.com/search?q={q}&f={modo}"


_METRICAS_RE = re.compile(
    r"^\d+([.,]\d+)?\s*(mil|k|m)?$|^\d{1,2}:\d{2}$", re.IGNORECASE
)


def _es_linea_de_metadata(linea: str) -> bool:
    """Filtra líneas de fecha/hora/métricas (vistas, likes, etc.) que Playwright
    trae mezcladas con el cuerpo del tuit al usar inner_text() sobre <article>."""
    l = linea.strip()
    if not l:
        return True
    if l.startswith("@"):
        return True
    if _METRICAS_RE.match(l):
        return True
    if re.match(r"^\d{1,2}\s+\w{3}\.?(\s+\d{4})?$", l):  # "19 may.", "2 ago. 2024"
        return True
    if l in {"·"}:
        return True
    return False


def _parse_article_text(raw_text: str, query: str):
    """El texto de <article> viene todo junto (autor, handle, fecha, cuerpo,
    métricas) separado por saltos de línea. No hay una API estructurada
    disponible sin backend propio de X, así que se parsea heurísticamente:
    se descarta el handle (@usuario), la fecha y las métricas numéricas al
    final, y se reconstruye el cuerpo uniendo el resto — necesario porque un
    tuit que menciona a otra cuenta a mitad de texto (@otra_cuenta) partía el
    cuerpo en dos antes de esta corrección."""
    lines = [l for l in raw_text.split("\n")]
    if len(lines) < 3:
        return None

    handle = next((l for l in lines if l.strip().startswith("@")), None)
    autor_hash = hash_author(handle.strip()) if handle else None

    # las primeras 2-3 líneas son siempre autor/handle/fecha; el resto puede
    # mezclar cuerpo con métricas al final — se descartan por patrón, no por
    # posición, porque el cuerpo puede tener cualquier longitud
    cuerpo_lineas = [l for l in lines[2:] if not _es_linea_de_metadata(l)]
    texto = " ".join(l.strip() for l in cuerpo_lineas if l.strip())

    return {"texto": texto, "autor_hash": autor_hash}


def fetch_search_results(query, max_scrolls=8, scroll_wait_ms=1500, modo="live"):
    """Requiere sesión guardada (ver ingest/save_session.py o
    ingest/convert_cookies.py). Devuelve lista de Items."""
    if not SESSION_STATE_PATH.exists():
        raise FileNotFoundError(
            f"No existe {SESSION_STATE_PATH}. Generar la sesión primero — ver "
            "ingest/save_session.py o ingest/convert_cookies.py."
        )

    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(SESSION_STATE_PATH), user_agent=_UA)
        page = ctx.new_page()
        page.goto(_search_url(query, modo), timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        for _ in range(max_scrolls):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(scroll_wait_ms)

        articles = page.query_selector_all("article")
        vistos = set()
        for a in articles:
            raw = a.inner_text()
            key = raw[:120]
            if key in vistos:
                continue
            vistos.add(key)

            parsed = _parse_article_text(raw, query)
            if not parsed or not parsed["texto"]:
                continue

            link_el = a.query_selector('a[href*="/status/"]')
            url = None
            if link_el:
                href = link_el.get_attribute("href")
                url = f"https://x.com{href}" if href and href.startswith("/") else href
            if not url:
                continue  # sin URL no podemos deduplicar de forma estable

            time_el = a.query_selector("time")
            fecha_attr = time_el.get_attribute("datetime") if time_el else None
            fecha = fecha_attr or ""

            items.append(
                Item(
                    fuente="twitter",
                    texto=parsed["texto"],
                    fecha=fecha,
                    url=url,
                    autor_hash=parsed["autor_hash"],
                ).to_dict()
            )

        ctx.storage_state(path=str(SESSION_STATE_PATH))
        browser.close()

    return items


def fetch_all_queries(queries=None, max_scrolls=8):
    queries = queries or QUERIES
    resultados = []
    for q in queries:
        try:
            resultados.extend(fetch_search_results(q, max_scrolls=max_scrolls))
        except Exception as e:
            print(f"FAIL query={q!r}: {e}")
    return resultados


if __name__ == "__main__":
    items = fetch_search_results("WIN internet Peru")
    print(f"{len(items)} tuits recolectados")
    for it in items[:5]:
        print(it["fecha"], "-", it["texto"][:100])
