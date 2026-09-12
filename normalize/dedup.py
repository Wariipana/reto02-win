"""Capa 2: dedup exacto por hash + near-duplicate por MinHash, y un filtro
básico de spam/bots/reventa. Ver CLAUDE.md, arquitectura propuesta, Capa 2.
"""
import hashlib
import re
import unicodedata

from datasketch import MinHash, MinHashLSH

NUM_PERM = 128
NGRAM_SIZE = 3
NEAR_DUP_THRESHOLD = 0.7

# Señales simples de spam/reventa/bot. No busca ser exhaustivo, es un primer filtro.
SPAM_PATTERNS = [
    r"\bwhats?app\b.{0,20}\d{7,9}",
    r"\bpromo(?:ci[oó]n)?\s+exclusiv[ao]\b",
    r"\bcont[aá]ctame\s+(?:al|por)\b",
    r"\brevendedor(?:es)?\b",
    r"\bg[aá]nate\s+un\b",
    r"(?:https?://\S+){3,}",  # 3+ links en el mismo texto
]
_SPAM_RE = re.compile("|".join(SPAM_PATTERNS), re.IGNORECASE)


def normalize_text(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def texto_hash(texto: str) -> str:
    return hashlib.sha256(normalize_text(texto).encode()).hexdigest()


def is_spam(texto: str) -> bool:
    return bool(_SPAM_RE.search(texto))


def _shingles(texto_norm: str, n=NGRAM_SIZE):
    tokens = texto_norm.split()
    if len(tokens) < n:
        return {texto_norm} if texto_norm else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def minhash_of(texto: str) -> MinHash:
    mh = MinHash(num_perm=NUM_PERM)
    for shingle in _shingles(normalize_text(texto)):
        mh.update(shingle.encode("utf8"))
    return mh


class DedupIndex:
    """Índice en memoria para una corrida de ingesta. Para dedup persistente
    entre corridas, comparar contra texto_hash ya almacenado en Postgres antes
    de llegar aquí (ver pipeline.py)."""

    def __init__(self, threshold=NEAR_DUP_THRESHOLD):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
        self.seen_hashes = set()
        self._count = 0

    def add_and_check(self, item: dict) -> str:
        """Devuelve 'exact_dup', 'near_dup', 'spam' o 'ok'."""
        texto = item.get("texto", "")
        if is_spam(texto):
            return "spam"

        h = texto_hash(texto)
        item["texto_hash"] = h
        if h in self.seen_hashes:
            return "exact_dup"

        mh = minhash_of(texto)
        key = f"item_{self._count}"
        near = self.lsh.query(mh)
        if near:
            return "near_dup"

        self.lsh.insert(key, mh)
        self.seen_hashes.add(h)
        self._count += 1
        return "ok"


def dedup_batch(items: list[dict]) -> list[dict]:
    """Filtra una lista de Items (dicts) dejando sólo los que pasan spam+dedup."""
    idx = DedupIndex()
    kept = []
    for item in items:
        verdict = idx.add_and_check(item)
        if verdict == "ok":
            kept.append(item)
    return kept
