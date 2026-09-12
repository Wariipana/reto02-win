"""Orquesta Capa 1 (ingesta) -> Capa 2 (normalización/dedup) -> Postgres.

Uso:
    python3 pipeline.py            # corre todas las fuentes seguras (sin TikTok)
    python3 pipeline.py --only trends   # corre sólo una fuente (para invocar desde cron)
    python3 pipeline.py --tiktok urls.txt   # además procesa una lista de URLs de TikTok

Pensado para invocarse repetidamente desde cron (ver cron/ en la raíz del
proyecto) — cada llamada es una corrida corta y se cierra sola, no es un
proceso de larga duración.
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingest"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))

from connection import get_conn  # noqa: E402
from dedup import DedupIndex  # noqa: E402

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "pipeline.log"
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("pipeline")


def _existing_hashes(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT texto_hash FROM items WHERE texto_hash IS NOT NULL")
        return {row[0] for row in cur.fetchall()}


def _insert_items(conn, items: list[dict]):
    if not items:
        return 0
    with conn.cursor() as cur:
        for it in items:
            cur.execute(
                """
                INSERT INTO items (id, fuente, marca, texto, fecha, url,
                                    autor_hash, geo, rating, engagement, texto_hash)
                VALUES (%(id)s, %(fuente)s, %(marca)s, %(texto)s, %(fecha)s, %(url)s,
                        %(autor_hash)s, %(geo)s, %(rating)s, %(engagement)s, %(texto_hash)s)
                ON CONFLICT (id) DO NOTHING
                """,
                {
                    "id": it["id"],
                    "fuente": it["fuente"],
                    "marca": it.get("marca", "WIN"),
                    "texto": it.get("texto", ""),
                    "fecha": it["fecha"] or None,
                    "url": it["url"],
                    "autor_hash": it.get("autor_hash"),
                    "geo": it.get("geo"),
                    "rating": it.get("rating"),
                    "engagement": _to_jsonb(it.get("engagement")),
                    "texto_hash": it.get("texto_hash"),
                },
            )
    conn.commit()
    return len(items)


def _to_jsonb(d):
    import json

    return json.dumps(d) if d is not None else None


def _insert_trends(conn, rows: list[dict], granularidad="hora"):
    if not rows:
        return 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(
                """
                INSERT INTO trends_series (marca, fecha, valor, granularidad)
                VALUES (%(marca)s, %(fecha)s, %(valor)s, %(granularidad)s)
                ON CONFLICT (marca, fecha, granularidad) DO UPDATE SET valor = EXCLUDED.valor
                """,
                {**r, "granularidad": granularidad},
            )
    conn.commit()
    return len(rows)


def run_trends(conn):
    import trends

    rows = trends.fetch_hourly()
    n = _insert_trends(conn, rows, granularidad="hora")
    log.info("[trends] %d puntos horarios upserted", n)


def run_news(conn, idx: DedupIndex):
    import news

    items = news.fetch_google_news() + news.fetch_prensa_directa()
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    log.info("[news] %d recolectados, %d tras dedup, %d insertados", len(items), len(kept), n)


def run_play_store(conn, idx: DedupIndex):
    import play_store

    items = play_store.fetch_reviews()
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    log.info(
        "[play_store] %d recolectados, %d tras dedup, %d insertados", len(items), len(kept), n
    )


def run_discord(conn, idx: DedupIndex, mensajes_file: str):
    """mensajes_file: JSON con una lista de {texto, fecha_iso, autor} extraída
    manualmente (ver ingest/discord_manual.py). No hay descubrimiento
    automático — Discord no se automatiza en tiempo real por ToS (ver
    CLAUDE.md, sección Discord)."""
    import json

    import discord_manual

    mensajes = json.loads(Path(mensajes_file).read_text())
    items = discord_manual.parse_manual_batch(mensajes)
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    log.info("[discord] %d recolectados, %d tras dedup, %d insertados", len(items), len(kept), n)


def run_tiktok(conn, idx: DedupIndex, urls_file: str = None):
    import tiktok

    if urls_file:
        urls = Path(urls_file).read_text().split()
    else:
        # usa la sesión guardada (ver ingest/tiktok.py, discover_ids_with_session)
        # en vez de requerir una lista manual de URLs
        urls = []
        for cuenta in tiktok.CUENTAS:
            try:
                urls.extend(tiktok.discover_ids_with_session(cuenta))
            except FileNotFoundError as e:
                log.warning("[tiktok] %s", e)
                return
            except Exception:
                log.exception("[tiktok] descubrimiento falló para @%s", cuenta)

    items = tiktok.fetch_video_details_batch(urls)
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    log.info("[tiktok] %d recolectados, %d tras dedup, %d insertados", len(items), len(kept), n)


def _filter_new(items, idx: DedupIndex):
    """Descarta spam/dedup dentro del batch (idx.add_and_check) y además lo que
    ya existía en Postgres de corridas anteriores (idx.seen_hashes_persisted)."""
    from dedup import texto_hash

    kept = []
    for it in items:
        if texto_hash(it.get("texto", "")) in idx.seen_hashes_persisted:
            continue
        verdict = idx.add_and_check(it)
        if verdict == "ok":
            kept.append(it)
    return kept


def _safe(nombre, fn):
    """Aísla la falla de una fuente para que no tumbe la corrida completa
    (crítico en cron: un timeout de una API no debe bloquear a las demás)."""
    try:
        fn()
    except Exception:
        log.exception("[%s] falló, se continúa con las demás fuentes", nombre)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiktok", help="archivo con URLs de video de TikTok, una por línea")
    parser.add_argument(
        "--discord",
        help="archivo JSON con mensajes de Discord extraídos manualmente "
        "(lista de {texto, fecha_iso, autor})",
    )
    parser.add_argument(
        "--only",
        choices=["trends", "news", "play", "tiktok"],
        help="correr sólo esta fuente (para invocar desde cron con su propio intervalo)",
    )
    parser.add_argument("--skip-trends", action="store_true")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-play", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    idx = DedupIndex()
    idx.seen_hashes_persisted = _existing_hashes(conn)

    do_trends = args.only == "trends" or (args.only is None and not args.skip_trends)
    do_news = args.only == "news" or (args.only is None and not args.skip_news)
    do_play = args.only == "play" or (args.only is None and not args.skip_play)

    if do_trends:
        _safe("trends", lambda: run_trends(conn))
    if do_news:
        _safe("news", lambda: run_news(conn, idx))
    if do_play:
        _safe("play_store", lambda: run_play_store(conn, idx))
    if args.only == "tiktok" or args.tiktok:
        _safe("tiktok", lambda: run_tiktok(conn, idx, args.tiktok))
    if args.discord:
        _safe("discord", lambda: run_discord(conn, idx, args.discord))

    conn.close()


if __name__ == "__main__":
    main()
