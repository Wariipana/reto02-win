"""Orquesta Capa 1 (ingesta) -> Capa 2 (normalización/dedup) -> Postgres.

Uso:
    python3 pipeline.py            # corre todas las fuentes seguras (sin TikTok)
    python3 pipeline.py --tiktok urls.txt   # además procesa una lista de URLs de TikTok
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingest"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))

from connection import get_conn  # noqa: E402
from dedup import DedupIndex  # noqa: E402


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
    print(f"[trends] {n} puntos horarios upserted")


def run_news(conn, idx: DedupIndex):
    import news

    items = news.fetch_google_news() + news.fetch_prensa_directa()
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    print(f"[news] {len(items)} recolectados, {len(kept)} tras dedup, {n} insertados")


def run_play_store(conn, idx: DedupIndex):
    import play_store

    items = play_store.fetch_reviews()
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    print(f"[play_store] {len(items)} recolectados, {len(kept)} tras dedup, {n} insertados")


def run_tiktok(conn, idx: DedupIndex, urls_file: str):
    import tiktok

    urls = Path(urls_file).read_text().split()
    items = tiktok.fetch_video_details_batch(urls)
    kept = _filter_new(items, idx)
    n = _insert_items(conn, kept)
    print(f"[tiktok] {len(items)} recolectados, {len(kept)} tras dedup, {n} insertados")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiktok", help="archivo con URLs de video de TikTok, una por línea")
    parser.add_argument("--skip-trends", action="store_true")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-play", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    idx = DedupIndex()
    idx.seen_hashes_persisted = _existing_hashes(conn)

    if not args.skip_trends:
        run_trends(conn)
    if not args.skip_news:
        run_news(conn, idx)
    if not args.skip_play:
        run_play_store(conn, idx)
    if args.tiktok:
        run_tiktok(conn, idx, args.tiktok)

    conn.close()


if __name__ == "__main__":
    main()
