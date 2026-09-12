"""Ingesta de Google News RSS + feeds de prensa directos (Capa de escalamiento).

Sin ToS: son feeds RSS públicos. No entra al z-score de la Capa 4;
dispara alerta por el hecho de existir (ver CLAUDE.md, "Estrategia de fuentes por rol").
"""
import re
import urllib.parse

import feedparser

from schema import Item

GOOGLE_NEWS_QUERIES = ["WIN internet Peru", "WIN fibra óptica", "Wi-Net Telecom"]

# RSS de prensa confirmados funcionando (ver CLAUDE.md, sección "RSS de prensa directos")
PRENSA_FEEDS = {
    "rpp": "https://rpp.pe/feed",
    "gestion": "https://gestion.pe/arc/outboundfeeds/rss/",
    "el_comercio": "https://elcomercio.pe/arc/outboundfeeds/rss/",
    "infobae_peru": "https://www.infobae.com/arc/outboundfeeds/rss/category/peru/",
    "diario_correo": "https://diariocorreo.pe/feed/",
    "andina": "https://andina.pe/agencia/rss.aspx",
}


def _google_news_url(query, geo_gl="PE"):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl={geo_gl}&ceid={geo_gl}:es-419"


def fetch_google_news(queries=None, geo_gl="PE"):
    queries = queries or GOOGLE_NEWS_QUERIES
    items = []
    for q in queries:
        feed = feedparser.parse(_google_news_url(q, geo_gl))
        for entry in feed.entries:
            items.append(
                Item(
                    fuente="google_news",
                    texto=entry.get("title", ""),
                    fecha=entry.get("published", ""),
                    url=entry.get("link", ""),
                ).to_dict()
            )
    return items


_WORD_BOUNDARY_RE_CACHE = {}


def _matches_keyword(text, keyword):
    pattern = _WORD_BOUNDARY_RE_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        _WORD_BOUNDARY_RE_CACHE[keyword] = pattern
    return bool(pattern.search(text))


def fetch_prensa_directa(keyword="WIN", feeds=None):
    feeds = feeds or PRENSA_FEEDS
    items = []
    for nombre, url in feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titulo = entry.get("title", "")
            resumen = entry.get("summary", "")
            if not _matches_keyword(titulo, keyword) and not _matches_keyword(resumen, keyword):
                continue
            items.append(
                Item(
                    fuente=f"prensa_{nombre}",
                    texto=titulo,
                    fecha=entry.get("published", ""),
                    url=entry.get("link", ""),
                ).to_dict()
            )
    return items


if __name__ == "__main__":
    news_items = fetch_google_news()
    print(f"Google News: {len(news_items)} notas")
    for it in news_items[:5]:
        print(it["fecha"], "-", it["texto"])

    prensa_items = fetch_prensa_directa()
    print(f"\nPrensa directa (filtrado por 'WIN'): {len(prensa_items)} notas")
    for it in prensa_items[:5]:
        print(it["fuente"], it["fecha"], "-", it["texto"])
