"""Convierte una TarjetaAlerta en el payload de Slack Block Kit que se enviaría
de verdad a un canal. Ver CLAUDE.md: "el entregable estrella es la alerta misma,
maquetada como llegaría de verdad: mensaje de Slack con titular, volumen,
mini-gráfica, tres citas reales y botón de escalamiento".

Este módulo sólo construye el JSON del mensaje — el envío real (webhook de
Slack) es un paso posterior que depende de que WIN provea la URL del webhook,
así que no hay credenciales ni llamada de red aquí.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate import TarjetaAlerta  # noqa: E402

EMOJI_URGENCIA = {"P1": "🔴", "P2": "🟠", "P3": "🟡"}


def _sparkline_texto(serie: list) -> str:
    """Sparkline ASCII simple (▁▂▃▄▅▆▇█) para representar la serie en un
    bloque de texto de Slack, ya que Block Kit no soporta gráficos nativos."""
    if not serie:
        return ""
    barras = "▁▂▃▄▅▆▇█"
    valores = [v for _f, v in serie]
    vmin, vmax = min(valores), max(valores)
    rango = vmax - vmin or 1
    return "".join(barras[int((v - vmin) / rango * (len(barras) - 1))] for v in valores)


def tarjeta_a_slack_blocks(t: TarjetaAlerta) -> dict:
    emoji = EMOJI_URGENCIA.get(t.urgencia, "⚪")
    signo = "+" if t.cambio_pct >= 0 else ""

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} {t.titular}", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Área:*\n{t.area}"},
                {"type": "mrkdwn", "text": f"*Urgencia:*\n{t.urgencia}"},
                {"type": "mrkdwn", "text": f"*Volumen:*\n{t.volumen} ({signo}{t.cambio_pct}% vs. baseline)"},
                {"type": "mrkdwn", "text": f"*Ventana:*\n{t.ventana}"},
            ],
        },
    ]

    spark = _sparkline_texto(t.serie_sparkline)
    if spark:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Tendencia (14d):* `{spark}`"},
            }
        )

    if t.ejemplos:
        citas = []
        for e in t.ejemplos[:3]:
            texto_corto = e["texto"][:180] + ("…" if len(e["texto"]) > 180 else "")
            link = f" (<{e['url']}|ver original>)" if e.get("url") else ""
            citas.append(f"> {texto_corto}{link}\n_— {e['fuente']}, {e['fecha']}_")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Ejemplos reales:*\n\n" + "\n\n".join(citas)},
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Esto es ruido"},
                    "style": "danger",
                    "action_id": "marcar_ruido",
                    "value": f"{t.tema}|{t.fuente_principal}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Ver en el tablero"},
                    "action_id": "abrir_tablero",
                },
            ],
        }
    )

    return {"blocks": blocks}


if __name__ == "__main__":
    import json
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "db"))
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from generate import generar_alertas

    tarjetas = generar_alertas(solo_relevantes=False)
    for t in tarjetas[:1]:
        print(json.dumps(tarjeta_a_slack_blocks(t), indent=2, ensure_ascii=False))
