"""Ingesta de Discord (WIN server, #general). Ver CLAUDE.md sección "Discord"
para el análisis completo de riesgo de ToS.

MODELO DELIBERADAMENTE NO AUTOMATIZADO EN TIEMPO REAL:
Discord prohíbe explícitamente automatizar una cuenta de usuario personal para
conectarse a su WebSocket Gateway ("self-bot"), sea para enviar o sólo para
escuchar mensajes — la prohibición es sobre el tipo de token/cuenta usado, no
sobre si el bot escribe o sólo lee (confirmado investigando la documentación
oficial de Discord: un bot con permisos de sólo lectura es legítimo, pero debe
ser un bot de aplicación invitado por un admin del servidor, no la cuenta de
un usuario). No tenemos ese acceso admin hoy.

Lo que SÍ es legítimo: un humano (el usuario del proyecto) abre el canal en su
propio cliente de Discord, como cualquier miembro normal, y lee lo que ve en
pantalla. Este módulo no automatiza esa lectura — sólo estructura y normaliza
los mensajes que un humano ya extrajo del DOM (vía Claude in Chrome u otro
método manual), y los deja listos para el pipeline de Capa 2/3.

Flujo de uso:
  1. Un humano entra a #general con su cuenta, hace scroll hacia atrás lo que
     considere necesario (sesión por sesión, no continuo).
  2. Se listan manualmente los mensajes visibles con su timestamp — por
     ejemplo, pegando el texto+fecha que un asistente leyó del DOM en esa
     sesión de navegador, o copiándolos directamente.
  3. Se llama a parse_manual_batch() con esa lista para convertirla a Item.
  4. Se repite el proceso periódicamente (ej. 1x/día) — es polling
     humano-asistido, no un listener de eventos.

Esto es más lento que un ingestor automático, y es la limitación aceptada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import Item, hash_author  # noqa: E402

CANAL_URL = "https://discord.com/channels/1215716246172213398/1215716247870898290"  # #general


def parse_manual_batch(mensajes: list[dict]) -> list[dict]:
    """mensajes: lista de {texto, fecha_iso, autor} extraídos manualmente
    (fecha_iso en ISO 8601; autor es cualquier identificador visible, sólo se
    usa para hashear — nunca se persiste en claro).

    Devuelve Items listos para _insert_items() del pipeline. No hace red, no
    toca Discord — es sólo la capa de normalización de datos ya extraídos
    manualmente."""
    items = []
    for m in mensajes:
        if not m.get("texto") or not m.get("fecha_iso"):
            continue
        items.append(
            Item(
                fuente="discord_win_general",
                texto=m["texto"],
                fecha=m["fecha_iso"],
                url=CANAL_URL,
                autor_hash=hash_author(m.get("autor", "")),
            ).to_dict()
        )
    return items


if __name__ == "__main__":
    ejemplo = [
        {
            "texto": "ejemplo: no me anda el internet hace 2 horas",
            "fecha_iso": "2026-09-12T13:00:00-05:00",
            "autor": "usuario_ejemplo",
        }
    ]
    import json

    print(json.dumps(parse_manual_batch(ejemplo), indent=2, ensure_ascii=False))
