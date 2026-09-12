"""Genera datos de ejemplo SINTÉTICOS (ficticios, no reales) que reflejan el
esquema y la variedad de contenido real del proyecto, para que otros agentes/
colaboradores puedan entender la estructura sin exponer datos reales de
terceros (reseñas, mensajes de Discord, posts de TikTok de clientes reales).

Ningún texto aquí proviene de una fuente real — está escrito a mano para
ilustrar los patrones observados (ver CLAUDE.md), no copiado de items.texto.

Uso:
    python3 generate_synthetic.py
Genera sample_data/items_sample.json y sample_data/trends_sample.json.
"""
import hashlib
import json
import random
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).resolve().parent


def _hash(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# --- Google Play: reseñas ficticias, mismo patrón que el real (65% NEG,
# facturación/avería/atención como temas dominantes) ---
GOOGLE_PLAY_SAMPLE = [
    {
        "texto": "Llevo tres días sin poder pagar mi recibo, la app se queda cargando en la pasarela de pago y nunca termina.",
        "tema": "facturacion_cobros", "sentimiento": "NEG", "rating": 1,
    },
    {
        "texto": "Muy buena atención cuando llamé por un problema con mi router, me lo cambiaron el mismo día.",
        "tema": "atencion_cliente", "sentimiento": "POS", "rating": 5,
    },
    {
        "texto": "El internet se cae todas las noches entre las 9 y las 11, ya reporté varias veces y no solucionan nada.",
        "tema": "averia_caida_servicio", "sentimiento": "NEG", "rating": 1,
    },
    {
        "texto": "App básica, no deja ver el detalle de consumo ni cambiar la contraseña del wifi desde acá.",
        "tema": "atencion_cliente", "sentimiento": "NEU", "rating": 3,
    },
    {
        "texto": "Me cobraron doble este mes, ya llamé pero nadie me da una fecha para la devolución.",
        "tema": "facturacion_cobros", "sentimiento": "NEG", "rating": 1,
    },
]

# --- Google News: notas de prensa ficticias, estilo titular ---
GOOGLE_NEWS_SAMPLE = [
    {
        "texto": "WIN es investigada por Indecopi tras denuncias de publicidad engañosa en sus planes gamer",
        "tema": "publicidad_reputacion", "sentimiento": "NEG",
    },
    {
        "texto": "Conexiones de fibra óptica en Lima y Callao crecen 12% según reporte trimestral de OSIPTEL",
        "tema": "precio_planes", "sentimiento": "NEU",
    },
    {
        "texto": "WIN anuncia expansión de cobertura a nuevos distritos del cono norte de Lima",
        "tema": "cobertura", "sentimiento": "NEU",
    },
]

# --- TikTok: posts de marca ficticios, tono promocional ---
TIKTOK_SAMPLE = [
    {
        "texto": "¿Tu internet no aguanta ni una partida? Cámbiate a WIN y juega sin lag 🎮⚡",
        "tema": "precio_planes", "sentimiento": "POS",
        "engagement": {"diggCount": 340, "shareCount": 22, "commentCount": 8, "playCount": 15200},
    },
    {
        "texto": "Así vivimos el evento de gamers en nuestro módulo de Miraflores 🧡",
        "tema": None, "sentimiento": "POS",
        "engagement": {"diggCount": 890, "shareCount": 45, "commentCount": 19, "playCount": 62000},
    },
]

# --- Discord: mensajes ficticios de #general, estilo coloquial peruano ---
DISCORD_SAMPLE = [
    {
        "texto": "se cayó el internet en San Juan de Lurigancho, alguien más por esa zona?",
        "tema": "averia_caida_servicio", "sentimiento": "NEG",
        "geo": "san juan de lurigancho",
    },
    {
        "texto": "a mi también se me fue hace rato, raro que sea la misma hora",
        "tema": "averia_caida_servicio", "sentimiento": "NEG", "geo": None,
    },
    {
        "texto": "alguien sabe si el plan gamer trae exitlag incluido o se paga aparte?",
        "tema": "precio_planes", "sentimiento": "NEU", "geo": None,
    },
]


def _make_item(fuente, url_base, texto, tema, sentimiento, geo=None, rating=None, engagement=None, i=0):
    fecha = f"2026-09-{(i % 12) + 1:02d}T{(10 + i) % 24:02d}:00:00-05:00"
    url = f"{url_base}/{1000 + i}"
    return {
        "id": _hash(f"{fuente}|{url}|{fecha}"),
        "fuente": fuente,
        "marca": "WIN",
        "texto": texto,
        "fecha": fecha,
        "url": url,
        "autor_hash": _hash(f"usuario_ficticio_{i}"),
        "geo": geo,
        "rating": rating,
        "engagement": engagement,
        "tema": tema,
        "sentimiento": sentimiento,
        "severidad": None,
        "es_ruido": False,
    }


def build_items():
    items = []
    i = 0
    for row in GOOGLE_PLAY_SAMPLE:
        items.append(_make_item(
            "google_play", "https://play.google.com/store/apps/details?id=com.win.miwin_app.example",
            row["texto"], row["tema"], row["sentimiento"], rating=row["rating"], i=i,
        ))
        i += 1
    for row in GOOGLE_NEWS_SAMPLE:
        items.append(_make_item(
            "google_news", "https://example-news.pe/nota",
            row["texto"], row["tema"], row["sentimiento"], i=i,
        ))
        i += 1
    for row in TIKTOK_SAMPLE:
        items.append(_make_item(
            "tiktok", "https://www.tiktok.com/@win_internet_ejemplo/video",
            row["texto"], row["tema"], row["sentimiento"], engagement=row["engagement"], i=i,
        ))
        i += 1
    for row in DISCORD_SAMPLE:
        items.append(_make_item(
            "discord_win_general", "https://discord.com/channels/example/general",
            row["texto"], row["tema"], row["sentimiento"], geo=row.get("geo"), i=i,
        ))
        i += 1
    return items


def build_trends_series():
    """Serie sintética de Google Trends, mismo formato que trends_series."""
    marcas = ["WIN internet", "Movistar Peru", "Claro Peru"]
    rows = []
    for marca in marcas:
        base = {"WIN internet": 15, "Movistar Peru": 25, "Claro Peru": 20}[marca]
        for h in range(24):
            valor = max(0, base + random.randint(-8, 8))
            rows.append({
                "marca": marca,
                "fecha": f"2026-09-12T{h:02d}:00:00-05:00",
                "valor": valor,
                "granularidad": "hora",
            })
    return rows


if __name__ == "__main__":
    items = build_items()
    trends = build_trends_series()

    (OUT_DIR / "items_sample.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "trends_sample.json").write_text(
        json.dumps(trends, indent=2, ensure_ascii=False)
    )
    print(f"{len(items)} items sintéticos -> items_sample.json")
    print(f"{len(trends)} puntos de trends sintéticos -> trends_sample.json")
