"""Clasificador de tema por few-shot con Claude Haiku 4.5 (Capa 3).

Reemplaza el enfoque de reglas de keywords (nlp/rules_classifier.py) para
nuevos items: con sólo 12-45 ejemplos reales por categoría (muy por debajo
del mínimo de 150-250 que requiere un fine-tuning de RoBERTuito, ver
CLAUDE.md), un LLM con few-shot generaliza mejor que reglas de keywords sin
necesitar ese volumen — Haiku 4.5 ya "sabe" español y el dominio de quejas de
telecom por su preentrenamiento, así que el few-shot solo necesita fijar las
fronteras exactas entre categorías, no enseñarle el idioma desde cero.

Se eligió Haiku 4.5 sobre alternativas más baratas (Groq/GPT-OSS-20B, ~13-17x
más barato) por decisión explícita del usuario: con un corpus de este tamaño
(~788 items) la diferencia de costo total es despreciable, y priorizamos
calidad de clasificación en español coloquial peruano sobre el ahorro.

Los ejemplos few-shot están curados a mano (no tomados automáticamente de
rules_classifier.py) porque las reglas tienen ruido conocido — ej. "sigue
caido por que no me deja ingresar ningun juego" es claramente
averia_caida_servicio pero las reglas lo etiquetaron app_tecnico por
superposición de keywords. Usar esos casos como "ground truth" para el LLM
propagaría el mismo error.
"""
import json
import os
import re
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))
from connection import get_conn  # noqa: E402

# Carga .env si existe (no usar python-dotenv como dependencia nueva; el
# formato es simple KEY=VALUE)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists() and "ANTHROPIC_API_KEY" not in os.environ:
    for line in _ENV_PATH.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

MODEL = "claude-haiku-4-5"

CATEGORIAS = [
    "averia_caida_servicio",
    "facturacion_cobros",
    "instalacion",
    "atencion_cliente",
    "cobertura",
    "precio_planes",
    "publicidad_reputacion",
    "privacidad_datos",
    "app_tecnico",
]

# Ejemplos few-shot curados a mano — verificados uno por uno, no tomados
# directamente de la salida de rules_classifier.py (ver docstring del módulo).
EJEMPLOS_FEW_SHOT = [
    ("Cayó el internet en Valle Hermoso Surco, alguien más?", "averia_caida_servicio"),
    ("Se cae el internet todas las noches entre las 9 y las 11", "averia_caida_servicio"),
    ("sigue caido por que no me deja ingresar ningun juego", "averia_caida_servicio"),
    ("Me cobraron doble este mes, ya llamé pero nadie me da fecha para la devolución", "facturacion_cobros"),
    ("no me deja pagar mi recibo, la app se queda cargando en la pasarela de pago", "facturacion_cobros"),
    ("recién me instalaron ayer y estoy agotado con esto de las configuraciones", "instalacion"),
    ("Cuando genero mi ticket nunca viene el técnico a mi casa", "instalacion"),
    ("no responden a reclamos pero para llamarte a casa rato si son buenos", "atencion_cliente"),
    ("no me dejan presentar un reclamo en el libro de reclamaciones", "atencion_cliente"),
    ("liberen mi ticket y por favor atiendanme, con todo respeto el servicio es una cochinada", "atencion_cliente"),
    ("no hay cobertura de WIN en mi zona todavía, cuando van a expandir?", "cobertura"),
    ("creo que es por zonas porque a mi en particular me va de maravilla", "cobertura"),
    ("aumentó el precio de mi plan sin avisarme", "precio_planes"),
    ("alguien sabe cuanto sale el plan normal + exitlag aparte?", "precio_planes"),
    ("Indecopi sancionó a Win por publicidad engañosa sobre su servicio", "publicidad_reputacion"),
    ("no la recomiendo, pésima empresa, puro marketing y nada de calidad real", "publicidad_reputacion"),
    ("Threat Alert: actor de amenaza filtró base de datos de clientes de WIN", "privacidad_datos"),
    ("el tratamiento a los datos personales deja mucho que desear", "privacidad_datos"),
    ("la app no funciona, jamás abre", "app_tecnico"),
    ("código de verificación nunca llega y la contraseña que coloco no la reconoce", "app_tecnico"),
    ("Su App es muy mala, no entiendo cómo si tienen buen servicio no arreglan la app", "app_tecnico"),
]


def _build_system_prompt():
    ejemplos_texto = "\n".join(f'- "{texto}" -> {tema}' for texto, tema in EJEMPLOS_FEW_SHOT)
    categorias_texto = "\n".join(f"- {c}" for c in CATEGORIAS)
    return f"""Eres un clasificador de temas para quejas y menciones de WIN, un ISP peruano de fibra óptica.
Clasifica el texto del usuario en UNA sola categoría de esta lista, o "ninguna" si no aplica:

{categorias_texto}

Definiciones clave para no confundir categorías:
- averia_caida_servicio: el INTERNET no funciona o está lento/inestable (el servicio en sí).
- app_tecnico: la APP/aplicación móvil de WIN falla (login, códigos, errores de la app) — el internet puede estar funcionando bien.
- atencion_cliente: quejas sobre el soporte/servicio al cliente, tickets no resueltos, mal trato.
- cobertura: el servicio no está disponible en una zona geográfica.
- privacidad_datos: filtración/venta/robo de datos personales, hackeo, brechas de seguridad.
- publicidad_reputacion: publicidad engañosa, sanciones de Indecopi, reputación de marca (no reclamos individuales).

Ejemplos verificados:
{ejemplos_texto}

Responde ÚNICAMENTE con JSON: {{"tema": "<categoria_o_ninguna>"}}. Sin texto adicional."""


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def classify_llm(texto: str) -> str | None:
    """Devuelve una de CATEGORIAS o None. Usa Haiku 4.5 con few-shot (ver
    docstring del módulo para por qué Haiku sobre alternativas más baratas)."""
    if not texto or not texto.strip():
        return None

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=50,
        system=_build_system_prompt(),
        messages=[{"role": "user", "content": texto[:1000]}],
    )
    text_block = next((b for b in response.content if b.type == "text"), None)
    if not text_block:
        return None

    raw = text_block.text.strip()
    # Haiku a veces envuelve la respuesta en un bloque de código markdown
    # (```json ... ```) a pesar de la instrucción de responder sólo JSON.
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
        tema = data.get("tema")
    except (json.JSONDecodeError, AttributeError):
        return None

    if tema == "ninguna" or tema not in CATEGORIAS:
        return None
    return tema


def run_and_update(conn, limit=None):
    query = "SELECT id, texto FROM items WHERE texto <> '' AND tema IS NULL ORDER BY fecha DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    procesados = len(rows)
    clasificados = 0
    conteo = {c: 0 for c in CATEGORIAS}
    fallos = 0

    for item_id, texto in rows:
        try:
            tema = classify_llm(texto)
        except Exception as e:
            print(f"FAIL id={item_id}: {e}")
            fallos += 1
            continue

        if tema:
            with conn.cursor() as cur:
                cur.execute("UPDATE items SET tema = %s WHERE id = %s", (tema, item_id))
            conn.commit()
            clasificados += 1
            conteo[tema] += 1

    print(f"[llm_classifier] items procesados: {procesados}")
    print(f"[llm_classifier] clasificados: {clasificados}")
    print(f"[llm_classifier] sin categoría (ninguna): {procesados - clasificados - fallos}")
    print(f"[llm_classifier] fallos de API: {fallos}")
    print("[llm_classifier] conteo por categoría:")
    for c, n in sorted(conteo.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {c:24} {n}")

    return {"procesados": procesados, "clasificados": clasificados, "conteo": conteo}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = get_conn()
    try:
        run_and_update(conn, limit=args.limit)
    finally:
        conn.close()
