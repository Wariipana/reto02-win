# Datos de ejemplo (sintéticos)

**Todo el contenido en `items_sample.json` y `trends_sample.json` es ficticio.**
Ningún texto proviene de una fuente real — fue escrito a mano en
`generate_synthetic.py` para ilustrar el esquema y los patrones observados
(ver `CLAUDE.md`), sin exponer reseñas, mensajes de Discord o posts reales de
terceros.

## Por qué existen

El proyecto procesa contenido real de clientes (reseñas de Google Play,
mensajes de un servidor de Discord, comentarios de TikTok). Ese contenido vive
sólo en la base de datos Postgres local del proyecto (ver `db/README.md`),
nunca en este repositorio. Estos archivos de ejemplo permiten que otro agente
o colaborador entienda:

- El esquema exacto de `items` (ver `db/schema.sql`)
- Qué aspecto tiene cada fuente (`fuente`: `google_play`, `google_news`,
  `tiktok`, `discord_win_general`)
- Cómo se ven los campos derivados de la Capa 3 (`tema`, `sentimiento`, `geo`)
- El formato de `engagement` (JSONB, varía por fuente) y de la serie de
  `trends_series`

## Cómo regenerarlos

```bash
python3 generate_synthetic.py
```

Es determinístico (semilla fija) — regenerarlo produce el mismo resultado. Si
agregas más ejemplos, edita las listas `GOOGLE_PLAY_SAMPLE`,
`GOOGLE_NEWS_SAMPLE`, `TIKTOK_SAMPLE`, `DISCORD_SAMPLE` en
`generate_synthetic.py`, no los JSON directamente.

## Lo que NO es esto

No es una muestra aleatoria de la base real, no tiene ninguna relación con
usuarios reales de WIN, Google Play, TikTok o el servidor de Discord, y no
debe usarse para inferir nada sobre el volumen o contenido real del proyecto
más allá de lo que ya está descrito en `CLAUDE.md` (que sí reporta cifras
agregadas reales, sin texto de terceros).
