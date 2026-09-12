"""Capa 3 (provisional): clasificador de tema por reglas de keywords.

No reemplaza al fine-tuning de RoBERTuito descrito en CLAUDE.md (Capa NLP),
pero deja la columna `items.tema` poblada ya y genera candidatos etiquetados
para que un humano arme el dataset de entrenamiento.

Las ocho categorías son las del proyecto (ver CLAUDE.md). El matching es
case-insensitive y sin acentos: tanto el texto como las keywords pasan por
`normalize_text` de `normalize/dedup.py`.

Uso:
    python3 nlp/rules_classifier.py              # todos los items con tema NULL
    python3 nlp/rules_classifier.py --limit 100  # tope de items en esta corrida
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

from connection import get_conn  # noqa: E402
from normalize.dedup import normalize_text  # noqa: E402

KEYWORDS = {
    "averia_caida_servicio": [
        "se cae el internet",
        "se me cae el internet",
        "se cae a cada rato",
        "el internet se cae",
        "internet caido",
        "sin internet",
        "no tengo internet",
        "no hay internet",
        "me quede sin internet",
        "no funciona el internet",
        "no funciona internet",
        "no funciona el servicio",
        "no funciona la conexion",
        "internet lento",
        "esta lento",
        "muy lento",
        "lentitud",
        "intermitencia",
        "intermitente",
        "se corta",
        "se corta el internet",
        "cortes de internet",
        "corte de servicio",
        "corte de internet",
        "sin servicio",
        "sin senal",
        "no tengo senal",
        "no hay senal",
        "me quede sin senal",
        "averia",
        "averiado",
        "falla",
        "fallas",
        "fallando",
        "dejo de funcionar",
        "dejo de andar",
        "no carga",
        "se desconecta",
        "desconexion",
        "inestable",
        "inestabilidad",
        "problemas de conexion",
        "problema de conexion",
        "no navega",
        "no hay conexion",
        "se reinicia",
        "reinicia el modem",
        "el modem no funciona",
        "no llega la velocidad",
        "no cumple la velocidad",
        "velocidad no llega",
        "mas lento de lo contratado",
        "caida de servicio",
        "caida masiva",
        "se cae la red",
    ],
    "facturacion_cobros": [
        "me cobraron",
        "me cobraron de mas",
        "me cobran",
        "te cobran",
        "cobran de mas",
        "cobran carisimo",
        "cobran completo",
        "me siguen cobrando",
        "siguen cobrando",
        "siguen llegando recibos",
        "cobro indebido",
        "doble cobro",
        "cobro duplicado",
        "cobro",
        "cobros",
        "recibo",
        "recibos",
        "factura",
        "facturacion",
        "boleta",
        "pago",
        "pagos",
        "pagar",
        "pasarela de pago",
        "no puedo pagar",
        "no me deja pagar",
        "no se puede pagar",
        "mora",
        "deuda",
        "deudas",
        "corte por deuda",
        "suspension por deuda",
        "tarjeta",
        "yape",
        "descuento no aplicado",
        "no aplican el descuento",
        "me cobran el monto completo",
        "ajuste de facturacion",
    ],
    "instalacion": [
        "instalacion",
        "me instalaron",
        "instalaron",
        "instalar",
        "tecnico",
        "los tecnicos",
        "el tecnico nunca llego",
        "tecnico nunca llego",
        "nunca llego el tecnico",
        "no vino el tecnico",
        "visita tecnica",
        "cita tecnica",
        "reprogramar instalacion",
        "demora en la instalacion",
        "instalacion pendiente",
        "no han instalado",
        "nunca llegaron a instalar",
        "esperando la instalacion",
        "recojo de equipos",
        "recoger el router",
        "retiro de equipos",
        "dar de baja",
        "di de baja",
        "baja del servicio",
        "cancelar el servicio",
        "retirar el modem",
        "cableado",
        "activacion del servicio",
    ],
    "atencion_cliente": [
        "atencion al cliente",
        "mala atencion",
        "pesima atencion",
        "atencion pesima",
        "servicio al cliente",
        "soporte",
        "soporte tecnico",
        "asesor",
        "asesores",
        "call center",
        "centralita",
        "no me atienden",
        "no atienden",
        "me colgaron",
        "te cuelgan",
        "no dan respuesta",
        "no resuelven",
        "no me dan solucion",
        "sin solucion",
        "nunca contestan",
        "no contestan",
        "chat de soporte",
        "bot",
        "reclamo",
        "reclamos",
        "queja",
        "quejas",
        "no escalan",
        "me pasean",
        "personal incompetente",
        "maltrato",
        "trato pesimo",
    ],
    "cobertura": [
        "cobertura",
        "no hay cobertura",
        "sin cobertura",
        "no tienen cobertura",
        "zona sin cobertura",
        "fuera de cobertura",
        "no llega el servicio",
        "no hay servicio en mi zona",
        "no hay fibra en mi zona",
        "no esta disponible en mi zona",
        "disponibilidad",
        "expansion de cobertura",
        "ampliar cobertura",
        "zona rural",
        "llega la fibra",
        "no llega a mi zona",
    ],
    "precio_planes": [
        "precio",
        "precios",
        "tarifa",
        "tarifas",
        "plan",
        "planes",
        "plan contratado",
        "contrato",
        "contratos",
        "contrato toxico",
        "costo",
        "costoso",
        "caro",
        "carisimo",
        "mas barato",
        "aumento de precio",
        "subida de precio",
        "subio el precio",
        "promocion",
        "oferta",
        "ofertas",
        "paquete",
        "megas",
        "renta mensual",
        "precio justo",
        "mejores precios",
    ],
    "publicidad_reputacion": [
        "publicidad",
        "publicidad enganosa",
        "enganosa",
        "enganoso",
        "anuncio",
        "anuncios",
        "spot",
        "comercial",
        "campana",
        "marketing",
        "reputacion",
        "competencia desleal",
        "demanda",
        "indecopi",
        "multa",
        "multaron",
        "sancion",
        "sancionado",
        "sancionaron",
        "denuncia",
        "denuncian",
        "estafa",
        "estafadores",
        "fraude",
        "rata",
        "no lo contraten",
        "no recomiendo",
        "no la recomiendo",
        "pesima empresa",
        "mala empresa",
        "falso",
        "mentira",
        "mentirosos",
        "enganan",
        "enganado",
        "incumplen",
        "incumplimiento",
    ],
    "privacidad_datos": [
        "privacidad",
        "datos personales",
        "filtracion de datos",
        "filtraron mis datos",
        "filtraron datos",
        "filtracion",
        "filtrado de datos",
        "fuga de datos",
        "robo de datos",
        "robaron mis datos",
        "robo de informacion",
        "informacion personal",
        "proteccion de datos",
        "ley de proteccion de datos",
        "habeas data",
        "autorizacion de datos",
        "tratamiento de datos",
        "trata de datos",
        "ciberseguridad",
        "hackeo",
        "hackers",
        "hackearon",
        "expusieron mis datos",
        "exponen mis datos",
        "llamadas no deseadas",
        "correos no deseados",
    ],
}


def _compile_keywords():
    compiled = {}
    for categoria, frases in KEYWORDS.items():
        compiled[categoria] = [
            (frase, re.compile(r"\b" + re.escape(normalize_text(frase)) + r"\b"))
            for frase in frases
        ]
    return compiled


_COMPILED = _compile_keywords()


def _matches(texto_norm: str, frases) -> int:
    return sum(1 for _frase, regex in frases if regex.search(texto_norm))


def classify(texto: str) -> tuple[str | None, float]:
    """Devuelve (categoria, score). score = matches / total keywords de la
    categoría. Sin matches: (None, 0.0)."""
    if not texto:
        return None, 0.0
    texto_norm = normalize_text(texto)
    if not texto_norm:
        return None, 0.0

    mejor_categoria = None
    mejor_count = 0
    mejor_score = 0.0
    for categoria, frases in _COMPILED.items():
        count = _matches(texto_norm, frases)
        if count == 0:
            continue
        score = count / len(frases)
        if count > mejor_count or (count == mejor_count and score > mejor_score):
            mejor_categoria = categoria
            mejor_count = count
            mejor_score = score

    if mejor_categoria is None:
        return None, 0.0
    return mejor_categoria, round(mejor_score, 4)


def run_and_update(conn, limit=None):
    query = "SELECT id, texto FROM items WHERE texto <> '' AND tema IS NULL ORDER BY fecha DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    procesados = len(rows)
    clasificados = 0
    conteo = {categoria: 0 for categoria in KEYWORDS}
    actualizaciones = []

    for item_id, texto in rows:
        categoria, _score = classify(texto)
        if categoria is not None:
            actualizaciones.append((categoria, item_id))
            clasificados += 1
            conteo[categoria] += 1

    if actualizaciones:
        with conn.cursor() as cur:
            cur.executemany("UPDATE items SET tema = %s WHERE id = %s", actualizaciones)
        conn.commit()

    print(f"[rules_classifier] items procesados: {procesados}")
    print(f"[rules_classifier] clasificados: {clasificados}")
    print(f"[rules_classifier] sin match (quedan tema NULL): {procesados - clasificados}")
    print("[rules_classifier] conteo por categoría:")
    for categoria, n in sorted(conteo.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {categoria:24} {n}")

    return {
        "procesados": procesados,
        "clasificados": clasificados,
        "conteo": conteo,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = get_conn()
    try:
        run_and_update(conn, limit=args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
