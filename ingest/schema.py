"""Esquema único de ítem normalizado (Capa 2) compartido por todos los ingestores."""
import dataclasses
import hashlib
import typing


@dataclasses.dataclass
class Item:
    fuente: str
    texto: str
    fecha: str  # ISO 8601 UTC
    url: str
    autor_hash: typing.Optional[str] = None
    geo: typing.Optional[str] = None
    rating: typing.Optional[float] = None
    engagement: typing.Optional[dict] = None
    marca: str = "WIN"
    id: typing.Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            base = f"{self.fuente}|{self.url}|{self.fecha}"
            self.id = hashlib.sha256(base.encode()).hexdigest()[:24]

    def to_dict(self):
        return dataclasses.asdict(self)


def hash_author(raw_author: str) -> str:
    if not raw_author:
        return ""
    return hashlib.sha256(raw_author.encode()).hexdigest()[:16]
