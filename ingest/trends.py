"""Ingesta de Google Trends (pulso primario, sin texto).

No produce Item (no hay texto/autor/url por punto), produce una serie temporal
cruda por marca que alimenta directo la Capa 4 (detección de anomalías).
"""
import datetime

from pytrends.request import TrendReq

MARCAS = ["WIN internet", "Movistar Peru", "Claro Peru"]


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
                    "marca": marca,
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
                    "marca": marca,
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
