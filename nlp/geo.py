"""Extracción de geo por keywords (Capa 3, NER simplificado).

Ver CLAUDE.md, advertencia sobre el mapa de calor: la mayoría de publicaciones
no trae geoetiqueta, y un NER real tiene cobertura estimada de 20-40%. Esto es
un primer corte por lista cerrada de distritos de Lima/Callao (donde vive la
mayoría de la base de clientes de WIN) — más simple que un NER entrenado, con
el mismo techo de cobertura: si el texto no menciona un distrito explícito, no
hay señal geo, y eso es la mayoría de los casos.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "normalize"))

from dedup import normalize_text  # noqa: E402

# Distritos de Lima y Callao donde WIN opera (ver CLAUDE.md: Lima, Callao, y
# provincias como Trujillo/Chiclayo — se listan aquí sólo los de Lima/Callao,
# que es donde concentra la mayoría de su base). Lista no exhaustiva.
DISTRITOS = [
    "ate", "barranco", "bellavista", "breña", "callao", "carabayllo",
    "chorrillos", "chosica", "cieneguilla", "comas", "el agustino",
    "independencia", "jesus maria", "la molina", "la victoria", "lince",
    "los olivos", "lurigancho", "lurin", "magdalena", "miraflores",
    "pachacamac", "pucusana", "pueblo libre", "puente piedra", "punta hermosa",
    "rimac", "san bartolo", "san borja", "san isidro", "san juan de lurigancho",
    "san juan de miraflores", "san luis", "san martin de porres", "san miguel",
    "santa anita", "santa maria del mar", "santa rosa", "santiago de surco",
    "surco", "surquillo", "villa el salvador", "villa maria del triunfo",
    "ventanilla", "ancon", "carmen de la legua", "valle hermoso",
]

_DISTRITO_RE = [
    (d, re.compile(r"\b" + re.escape(d) + r"\b")) for d in DISTRITOS
]


def extraer_geo(texto: str) -> str | None:
    """Devuelve el primer distrito mencionado en el texto, o None si no hay
    ninguno. No intenta desambiguar múltiples menciones — para eso hace falta
    NER real, fuera de alcance aquí (ver docstring del módulo)."""
    if not texto:
        return None
    texto_norm = normalize_text(texto)
    for distrito, regex in _DISTRITO_RE:
        if regex.search(texto_norm):
            return distrito
    return None


if __name__ == "__main__":
    ejemplos = [
        "se cayo el internet en Puente Piedra el Roble alguien por ahi?",
        "Cayó el internet en Valle Hermoso Surco?",
        "por pueblo libre tmb se cayo",
        "no tengo internet hace dos horas",
    ]
    for e in ejemplos:
        print(extraer_geo(e), "<-", e)
