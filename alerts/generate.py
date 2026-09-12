"""Capa 5: genera tarjetas de alerta a partir de las anomalías de la Capa 4.

Estructura de cada tarjeta (ver CLAUDE.md, "Zona central" del tablero de triaje):
  - titular en lenguaje humano
  - volumen y velocidad (vs. baseline, % de cambio)
  - ventana temporal
  - serie para el sparkline (banda de normalidad + valores reales)
  - hasta 3 publicaciones reales de ejemplo, textuales, con link
  - área asignada y urgencia (Capa 5 de enrutamiento)

Esto es el objeto de datos; el render a Slack/HTML/tablero es responsabilidad de
otro módulo (deliver.py) — aquí sólo se arma el contenido.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "anomaly"))

from connection import get_conn  # noqa: E402
from detect import Anomalia, run as detectar  # noqa: E402
from routing import enrutar  # noqa: E402

TITULOS_POR_TEMA = {
    "averia_caida_servicio": "Pico de reportes de caída/avería",
    "facturacion_cobros": "Pico de quejas por facturación o cobros",
    "atencion_cliente": "Pico de quejas por atención al cliente",
    "instalacion": "Pico de quejas por instalación",
    "cobertura": "Pico de quejas por cobertura",
    "precio_planes": "Pico de menciones sobre precios o planes",
    "publicidad_reputacion": "Pico de menciones de publicidad o reputación",
    "privacidad_datos": "Posible incidente de privacidad o filtración de datos",
}


@dataclass
class TarjetaAlerta:
    titular: str
    marca: str
    tema: str
    fuente_principal: str
    volumen: int
    baseline: float
    cambio_pct: float
    ventana: str
    severidad: str
    area: str
    urgencia: str
    ejemplos: list = field(default_factory=list)  # [{texto, url, fuente, fecha}]
    serie_sparkline: list = field(default_factory=list)  # [(fecha, valor)]

    def to_dict(self):
        return {
            "titular": self.titular,
            "marca": self.marca,
            "tema": self.tema,
            "fuente_principal": self.fuente_principal,
            "volumen": self.volumen,
            "baseline": self.baseline,
            "cambio_pct": self.cambio_pct,
            "ventana": self.ventana,
            "severidad": self.severidad,
            "area": self.area,
            "urgencia": self.urgencia,
            "ejemplos": self.ejemplos,
            "serie_sparkline": self.serie_sparkline,
        }


def _cambio_pct(observado: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if observado == 0 else 100.0
    return round((observado - baseline) / baseline * 100, 1)


def _titular(anomalia: Anomalia) -> str:
    if anomalia.tipo == "trends":
        direccion = "Pico" if anomalia.z_score > 0 else "Caída"
        return f"{direccion} de búsquedas de {anomalia.clave}"
    fuente, tema = anomalia.clave.split(":", 1)
    base = TITULOS_POR_TEMA.get(tema, f"Pico de menciones de {tema}")
    return f"{base} ({fuente})"


def _ejemplos_reales(conn, fuente: str, tema: str, fecha, limite=3):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT texto, url, fuente, fecha
            FROM items
            WHERE fuente = %s AND tema = %s AND fecha::date = %s
            ORDER BY fecha DESC
            LIMIT %s
            """,
            (fuente, tema, fecha, limite),
        )
        rows = cur.fetchall()
    return [
        {"texto": texto, "url": url, "fuente": f, "fecha": fecha_item.isoformat()}
        for texto, url, f, fecha_item in rows
    ]


def _serie_sparkline_trends(conn, marca, dias=14):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT fecha::date as dia, avg(valor) as promedio
            FROM trends_series
            WHERE marca = %s AND fecha >= now() - (%s || ' days')::interval
            GROUP BY dia ORDER BY dia
            """,
            (marca, dias),
        )
        return [(dia.isoformat(), round(float(v), 1)) for dia, v in cur.fetchall()]


def construir_tarjeta(conn, anomalia: Anomalia) -> TarjetaAlerta:
    cambio = _cambio_pct(anomalia.valor_observado, anomalia.baseline)

    if anomalia.tipo == "trends":
        # Trends no tiene tema clasificado (es puro volumen de búsqueda); se enruta
        # siempre a Comunicaciones/Marketing como responsable de monitoreo de marca,
        # con urgencia baja salvo que la severidad estadística ya sea alta.
        ruta = {
            "area": "Comunicaciones / Marketing",
            "urgencia": "P1" if anomalia.severidad == "alerta" else "P3",
        }
        return TarjetaAlerta(
            titular=_titular(anomalia),
            marca=anomalia.clave,
            tema="pulso_trends",
            fuente_principal="google_trends",
            volumen=int(anomalia.valor_observado),
            baseline=anomalia.baseline,
            cambio_pct=cambio,
            ventana=f"último punto: {anomalia.fecha}",
            severidad=anomalia.severidad,
            area=ruta["area"],
            urgencia=ruta["urgencia"],
            ejemplos=[],
            serie_sparkline=_serie_sparkline_trends(conn, anomalia.clave),
        )

    fuente, tema = anomalia.clave.split(":", 1)
    ejemplos = _ejemplos_reales(conn, fuente, tema, anomalia.fecha[:10])
    ruta = enrutar(
        tema=tema,
        texto=" ".join(e["texto"] for e in ejemplos),
        fuente=fuente,
        items_relacionados=ejemplos,
    )
    return TarjetaAlerta(
        titular=_titular(anomalia),
        marca="WIN",
        tema=tema,
        fuente_principal=fuente,
        volumen=int(anomalia.valor_observado),
        baseline=anomalia.baseline,
        cambio_pct=cambio,
        ventana=f"día: {anomalia.fecha}",
        severidad=anomalia.severidad,
        area=ruta["area"],
        urgencia=ruta["urgencia"],
        ejemplos=ejemplos,
        serie_sparkline=[],  # requiere más profundidad histórica por tema (ver detect.py)
    )


def generar_alertas(conn=None, solo_relevantes=True):
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        anomalias = detectar(conn)
        if solo_relevantes:
            anomalias = [a for a in anomalias if a.severidad != "normal"]
        return [construir_tarjeta(conn, a) for a in anomalias]
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    tarjetas = generar_alertas(solo_relevantes=False)
    if not tarjetas:
        print("Sin tarjetas de alerta (nada por encima del umbral de severidad).")
    for t in tarjetas:
        print(f"\n=== {t.titular} ===")
        print(f"  {t.area} · {t.urgencia} · severidad={t.severidad}")
        print(f"  volumen={t.volumen} baseline={t.baseline} cambio={t.cambio_pct}%")
        print(f"  ventana: {t.ventana}")
        for e in t.ejemplos:
            print(f"  - \"{e['texto'][:80]}\" ({e['fuente']}, {e['fecha']})")
