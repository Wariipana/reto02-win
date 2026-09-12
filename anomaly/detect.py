"""Capa 4: señal vs. ruido. Ver CLAUDE.md, arquitectura propuesta y sección
"Ajustes estadísticos por baja frecuencia".

Dos modelos distintos según el volumen de la fuente:
- Google Trends (volumen alto, granularidad horaria): baseline móvil + banda de
  desviación estándar, z-score gaussiano razonable aquí.
- Items de texto (volumen bajo por tema/fuente/día): modelo de conteos (Poisson),
  el z-score gaussiano falla con medias bajas (ver CLAUDE.md).

No se cruza todavía con velocidad de propagación (engagement/hora) — eso queda
para cuando haya más volumen de engagement real por fuente.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))

from connection import get_conn  # noqa: E402

BASELINE_DIAS = 30
MIN_DIAS_CONFIANZA_ALTA = 5
MIN_DIAS_CONFIANZA_BAJA = 3  # por debajo de esto, ni siquiera se reporta


@dataclass
class Anomalia:
    tipo: str  # "trends" o "conteo_tema"
    clave: str  # marca, o "fuente:tema"
    fecha: str
    valor_observado: float
    baseline: float
    desviacion: float
    z_score: float
    severidad: str  # "normal", "atencion", "alerta"
    confianza: str = "alta"  # "alta" (>=5 días de baseline) o "baja" (3-4 días)


def _severidad_desde_zscore(z: float) -> str:
    az = abs(z)
    if az >= 3:
        return "alerta"
    if az >= 2:
        return "atencion"
    return "normal"


def detectar_anomalias_trends(conn, marcas=None, ventana_baseline_dias=BASELINE_DIAS):
    """Banda de baseline móvil sobre la serie horaria de Trends. Compara el
    último punto de cada marca contra la media+desviación de la ventana previa
    (excluyendo el propio punto)."""
    with conn.cursor() as cur:
        if marcas:
            cur.execute("SELECT DISTINCT marca FROM trends_series WHERE marca = ANY(%s)", (marcas,))
        else:
            cur.execute("SELECT DISTINCT marca FROM trends_series")
        marcas_a_revisar = [r[0] for r in cur.fetchall()]

    resultados = []
    with conn.cursor() as cur:
        for marca in marcas_a_revisar:
            cur.execute(
                """
                SELECT fecha, valor FROM trends_series
                WHERE marca = %s AND fecha >= now() - (%s || ' days')::interval
                ORDER BY fecha
                """,
                (marca, ventana_baseline_dias),
            )
            rows = cur.fetchall()
            if len(rows) < 10:
                continue  # muy poco histórico para una banda confiable

            valores = np.array([r[1] for r in rows], dtype=float)
            fecha_actual, valor_actual = rows[-1]
            baseline_valores = valores[:-1]

            media = baseline_valores.mean()
            desv = baseline_valores.std(ddof=1) if len(baseline_valores) > 1 else 0.0
            z = (valor_actual - media) / desv if desv > 0 else 0.0

            resultados.append(
                Anomalia(
                    tipo="trends",
                    clave=marca,
                    fecha=fecha_actual.isoformat(),
                    valor_observado=float(valor_actual),
                    baseline=round(float(media), 2),
                    desviacion=round(float(desv), 2),
                    z_score=round(float(z), 2),
                    severidad=_severidad_desde_zscore(z),
                )
            )
    return resultados


def detectar_anomalias_conteo(conn, ventana_baseline_dias=BASELINE_DIAS, solo_ultimo_dia=False):
    """Modelo de conteos (Poisson) por (fuente, tema, día). Para cada día de la
    ventana (o sólo el más reciente si solo_ultimo_dia=True) compara su conteo
    contra la tasa esperada de Poisson estimada con el resto de días (leave-
    one-out) — así un pico real se detecta aunque ya no sea "hoy", necesario
    tanto para alertas en vivo sobre eventos recientes como para la validación
    retrospectiva de los tres eventos históricos (ver CLAUDE.md).

    Ver CLAUDE.md: con medias bajas, un z-score gaussiano marca como anomalía
    extrema cualquier día con 2-3 eventos más de lo normal, aunque sea azar —
    Poisson maneja esto correctamente."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT fuente, tema, fecha::date as dia, count(*) as n
            FROM items
            WHERE tema IS NOT NULL
              AND fecha >= now() - (%s || ' days')::interval
            GROUP BY fuente, tema, dia
            ORDER BY fuente, tema, dia
            """,
            (ventana_baseline_dias,),
        )
        rows = cur.fetchall()

    from collections import defaultdict

    series = defaultdict(list)
    for fuente, tema, dia, n in rows:
        series[(fuente, tema)].append((dia, n))

    resultados = []
    for (fuente, tema), puntos in series.items():
        if len(puntos) < MIN_DIAS_CONFIANZA_BAJA:
            continue  # ni con confianza baja alcanza para estimar nada razonable

        confianza = "alta" if len(puntos) >= MIN_DIAS_CONFIANZA_ALTA else "baja"
        puntos.sort(key=lambda p: p[0])

        indices_a_evaluar = [len(puntos) - 1] if solo_ultimo_dia else range(len(puntos))

        for i in indices_a_evaluar:
            dia_actual, n_actual = puntos[i]
            baseline_conteos = [n for j, (_dia, n) in enumerate(puntos) if j != i]
            if not baseline_conteos:
                continue

            lam = np.mean(baseline_conteos)
            if lam <= 0:
                lam = 0.1  # evita división por cero / p-valor degenerado en series muy dispersas

            # p-valor de observar n_actual o más, bajo Poisson(lam)
            p_valor = 1 - stats.poisson.cdf(n_actual - 1, lam)
            # z-score equivalente aproximado (para reportar en la misma escala que Trends)
            z_aprox = (n_actual - lam) / np.sqrt(lam)

            if p_valor < 0.01:
                severidad = "alerta"
            elif p_valor < 0.05:
                severidad = "atencion"
            else:
                severidad = "normal"

            resultados.append(
                Anomalia(
                    tipo="conteo_tema",
                    clave=f"{fuente}:{tema}",
                    fecha=dia_actual.isoformat(),
                    valor_observado=float(n_actual),
                    baseline=round(float(lam), 2),
                    desviacion=round(float(np.sqrt(lam)), 2),
                    z_score=round(float(z_aprox), 2),
                    severidad=severidad,
                    confianza=confianza,
                )
            )
    return resultados


def run(conn=None):
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        anomalias_trends = detectar_anomalias_trends(conn)
        anomalias_conteo = detectar_anomalias_conteo(conn)
        return anomalias_trends + anomalias_conteo
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    anomalias = run()
    if not anomalias:
        print("Sin anomalías detectadas.")
    for a in sorted(anomalias, key=lambda x: abs(x.z_score), reverse=True):
        marca_severidad = {"normal": " ", "atencion": "!", "alerta": "!!"}[a.severidad]
        conf = f"(confianza {a.confianza})" if a.tipo == "conteo_tema" else ""
        print(
            f"[{marca_severidad}] {a.tipo:14} {a.clave:30} fecha={a.fecha} "
            f"obs={a.valor_observado:>6.1f} baseline={a.baseline:>6.2f} z={a.z_score:>6.2f} "
            f"-> {a.severidad} {conf}"
        )
