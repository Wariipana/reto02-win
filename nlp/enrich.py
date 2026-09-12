"""Capa 3 (parcial): sentimiento + embeddings sobre los items ya normalizados
en Postgres. No requiere datos etiquetados a mano (a diferencia del
clasificador de tema, que sí — ver CLAUDE.md, "Capa NLP").

Modelos usados (ver CLAUDE.md, tabla de modelos verificados en HuggingFace):
  - pysentimiento/robertuito-sentiment-analysis (preentrenado, NO se reentrena)
  - paraphrase-multilingual-MiniLM-L12-v2 (embeddings ligeros para clustering)

Uso:
    python3 enrich.py              # procesa todos los items sin sentimiento/embedding
    python3 enrich.py --batch 64   # tamaño de lote (default 32)
    python3 enrich.py --limit 500  # tope de items a procesar en esta corrida
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))

from connection import get_conn  # noqa: E402
from geo import extraer_geo  # noqa: E402

_analyzer = None
_embedder = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from pysentimiento import create_analyzer

        _analyzer = create_analyzer(task="sentiment", lang="es")
    return _analyzer


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embedder


def fetch_pending(conn, limit=None):
    """Items con texto no vacío que aún no tienen sentimiento o embedding."""
    query = """
        SELECT id, texto FROM items
        WHERE texto <> '' AND (sentimiento IS NULL OR embedding IS NULL)
        ORDER BY fecha DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def enrich_batch(conn, rows, batch_size=32):
    analyzer = _get_analyzer()
    embedder = _get_embedder()

    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        ids = [r[0] for r in chunk]
        textos = [r[1] for r in chunk]

        sentimientos = [analyzer.predict(t).output for t in textos]
        embeddings = embedder.encode(textos, show_progress_bar=False)
        geos = [extraer_geo(t) for t in textos]

        with conn.cursor() as cur:
            for item_id, sent, emb, geo in zip(ids, sentimientos, embeddings, geos):
                cur.execute(
                    "UPDATE items SET sentimiento = %s, embedding = %s, geo = %s WHERE id = %s",
                    (sent, emb.tolist(), geo, item_id),
                )
        conn.commit()
        total += len(chunk)
        print(f"[enrich] {total}/{len(rows)} procesados")

    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = get_conn()
    rows = fetch_pending(conn, limit=args.limit)
    print(f"[enrich] {len(rows)} items pendientes")
    if rows:
        enrich_batch(conn, rows, batch_size=args.batch)
    conn.close()


if __name__ == "__main__":
    main()
