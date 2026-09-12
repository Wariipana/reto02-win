"""Capa 5: matriz tema -> área dueña + urgencia. Ver CLAUDE.md, sección "Enrutamiento"."""

RUTAS = {
    "averia_caida_servicio": ("Operaciones / Red", "P1"),  # P1 si hay cluster geográfico
    "cobertura": ("Operaciones / Red", "P2"),
    "facturacion_cobros": ("Experiencia Cliente", "P2"),
    "atencion_cliente": ("Experiencia Cliente", "P2"),
    "instalacion": ("Experiencia Cliente", "P3"),
    "precio_planes": ("Experiencia Cliente", "P3"),
    "publicidad_reputacion": ("Comunicaciones / Marketing", "P2"),  # P1 si hay prensa
    "privacidad_datos": ("Comunicaciones + Legal", "P1"),  # siempre
}

# Señales que suben la urgencia automáticamente (ver CLAUDE.md, "Enrutamiento")
SENALES_ESCALAMIENTO = [
    "indecopi",
    "osiptel",
    "voy a denunciar",
    "cambio de operador",
    "me cambio de operador",
    "denuncia",
    "denunciar",
]

FUENTES_PRENSA = {"google_news", "prensa_rpp", "prensa_gestion", "prensa_el_comercio",
                   "prensa_infobae_peru", "prensa_diario_correo", "prensa_andina"}


def _sube_urgencia(texto: str, fuente: str, tema: str) -> bool:
    texto_low = (texto or "").lower()
    if any(senal in texto_low for senal in SENALES_ESCALAMIENTO):
        return True
    if tema == "publicidad_reputacion" and fuente in FUENTES_PRENSA:
        return True
    return False


def _es_cluster_geografico(items_relacionados) -> bool:
    """Placeholder simple: 2+ items del mismo tema con geo no-nulo distinto entre sí,
    o simplemente 3+ items en la misma ventana temporal (proxy hasta tener NER de geo
    con cobertura real — ver CLAUDE.md, sección de mapa de calor)."""
    return len(items_relacionados) >= 3


def enrutar(tema: str, texto: str = "", fuente: str = "", items_relacionados=None) -> dict:
    """Devuelve {area, urgencia} para un tema dado. items_relacionados es opcional,
    una lista de items del mismo incidente (para el criterio de cluster geográfico
    de avería/caída)."""
    if tema not in RUTAS:
        return {"area": "Sin clasificar", "urgencia": "P3"}

    area, urgencia_base = RUTAS[tema]
    items_relacionados = items_relacionados or []

    if tema == "averia_caida_servicio":
        urgencia = "P1" if _es_cluster_geografico(items_relacionados) else "P2"
    else:
        urgencia = urgencia_base

    if _sube_urgencia(texto, fuente, tema):
        urgencia = "P1"

    return {"area": area, "urgencia": urgencia}
