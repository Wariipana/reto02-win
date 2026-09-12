"""Ingesta de Google Trends (pulso primario, sin texto).

No produce Item (no hay texto/autor/url por punto), produce una serie temporal
cruda por marca que alimenta directo la Capa 4 (detección de anomalías).
"""
import datetime

from pytrends.request import TrendReq

MARCAS = ["WIN internet", "Movistar Peru", "Claro Peru"]

# Normaliza la keyword de búsqueda (lo que pytrends necesita) al mismo
# vocabulario de marca que usa items.marca ("WIN", "Movistar", "Claro", "Entel"
# — ver ingest/tiktok.py::_MARCA_POR_CUENTA). Sin esto, trends_series.marca
# quedaba con la frase completa de búsqueda y generate.py::generar_alertas
# (que filtra por marca == "WIN") nunca encontraba coincidencia — las
# tarjetas de Trends se generaban pero quedaban descartadas en silencio
# (encontrado por revisión externa, ver CLAUDE.md).
_MARCA_NORMALIZADA = {
    "WIN internet": "WIN",
    "Movistar Peru": "Movistar",
    "Claro Peru": "Claro",
}


def _normalizar_marca(keyword: str) -> str:
    return _MARCA_NORMALIZADA.get(keyword, keyword)


def fetch_hourly(marcas=None, geo="PE"):
    marcas = marcas or MARCAS
    pytrends = TrendReq(hl="es-PE", tz=-300)
    pytrends.build_payload(marcas, timeframe="now 7-d", geo=geo)
    df = pytrends.interest_over_time()
    if df.empty:
        return []
    df = df.drop(columns=["isPartial"], errors="ignore")
    rows = []
    for ts, row in df.iterrows():
        for marca in marcas:
            if marca not in row:
                continue
            rows.append(
                {
                    "fuente": "google_trends",
                    "marca": _normalizar_marca(marca),
                    "fecha": ts.tz_localize("UTC").isoformat()
                    if ts.tzinfo is None
                    else ts.isoformat(),
                    "valor": int(row[marca]),
                }
            )
    return rows


def fetch_daily(marcas=None, geo="PE", timeframe="today 3-m"):
    marcas = marcas or MARCAS
    pytrends = TrendReq(hl="es-PE", tz=-300)
    pytrends.build_payload(marcas, timeframe=timeframe, geo=geo)
    df = pytrends.interest_over_time()
    if df.empty:
        return []
    df = df.drop(columns=["isPartial"], errors="ignore")
    rows = []
    for ts, row in df.iterrows():
        for marca in marcas:
            if marca not in row:
                continue
            rows.append(
                {
                    "fuente": "google_trends",
                    "marca": _normalizar_marca(marca),
                    "fecha": ts.date().isoformat(),
                    "valor": int(row[marca]),
                }
            )
    return rows


if __name__ == "__main__":
    rows = fetch_hourly()
    print(f"{len(rows)} puntos horarios recolectados")
    for r in rows[:5]:
        print(r)
