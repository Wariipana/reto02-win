"""Extracción de geo por keywords (Capa 3, NER simplificado).

Ver CLAUDE.md, advertencia sobre el mapa de calor: la mayoría de publicaciones
no trae geoetiqueta, y un NER real tiene cobertura estimada de 20-40%. Esto es
un primer corte por lista cerrada de distritos de Lima/Callao (donde vive la
mayoría de la base de clientes de WIN) — más simple que un NER entrenado, con
el mismo techo de cobertura: si el texto no menciona un distrito explícito, no
hay señal geo, y eso es la mayoría de los casos.

Cobertura real medida sobre el corpus completo (598 items, 12-sep-2026): 1.7%
(10 items) — más baja que el 20-40% estimado en el CLAUDE.md. Se revisó el
corpus buscando patrones indirectos de zona ("norte/sur de Lima", "mi
distrito", nombres de calles) para ampliar el diccionario, y NO aparecieron —
Google Play y TikTok (73% del corpus) simplemente no traen esa señal en el
texto, no es un problema del extractor. La única mención geo adicional que sí
aparece en el corpus son ciudades de provincia (Trujillo, Arequipa, Chiclayo),
pero sólo en contenido de marketing de TikTok (eventos patrocinados), nunca en
quejas — se agregan por completitud, no porque mejoren la cobertura hoy.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "normalize"))

from dedup import normalize_text  # noqa: E402

# Distritos de Lima y Callao donde WIN opera, más provincias donde tiene
# presencia (ver CLAUDE.md, "Sobre la empresa": Trujillo, Chiclayo). Lista no
# exhaustiva.
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
    "trujillo", "chiclayo",
]

_DISTRITO_RE = [
    (d, re.compile(r"\b" + re.escape(d) + r"\b")) for d in DISTRITOS
]


# Ciudades de provincia que sólo aparecen en el corpus como contenido de
# marketing (eventos patrocinados de TikTok), nunca en quejas reales — se
# exigen junto a una señal de queja/problema para no contar un post
# promocional como "incidencia en esa ciudad" (ver docstring del módulo).
_CIUDADES_SOLO_CON_SENAL_DE_QUEJA = {"trujillo", "chiclayo"}
_SENAL_QUEJA_RE = re.compile(
    r"\b(no funciona|no anda|caido|cayo|se cayo|sin internet|sin servicio|"
    r"reclamo|queja|malo|pesimo|problema|falla|lento|corte)\b"
)


def extraer_geo(texto: str) -> str | None:
    """Devuelve el primer distrito/ciudad mencionado en el texto, o None si no
    hay ninguno. No intenta desambiguar múltiples menciones — para eso hace
    falta NER real, fuera de alcance aquí (ver docstring del módulo)."""
    if not texto:
        return None
    texto_norm = normalize_text(texto)
    for lugar, regex in _DISTRITO_RE:
        if not regex.search(texto_norm):
            continue
        if lugar in _CIUDADES_SOLO_CON_SENAL_DE_QUEJA and not _SENAL_QUEJA_RE.search(texto_norm):
            continue  # ej. "Rally de Arequipa" (marketing), no una queja real
        return lugar
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
