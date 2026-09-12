# Ingesta continua (Capa 1/2)

## Estado real: parcialmente automatizada

| Fuente | Automatizada vía cron | Intervalo |
|---|---|---|
| Google Trends | Sí | cada 15 min |
| Google News + prensa | Sí | cada 30 min |
| Google Play | Sí | cada 30 min |
| TikTok | **No** — manual | requiere sesión de navegador para descubrir posts nuevos (ver `ingest/tiktok.py`, notas al final del archivo, y CLAUDE.md sección "TikTok: cómo se resolvió el bloqueo del WAF") |
| Enriquecimiento NLP (Capa 3: sentimiento + embeddings) | Sí | minutos 5 y 35 (5 min después del ciclo de ingesta de 30 min) |

Trends corre más seguido porque su propia granularidad es horaria — cada 15 min
sólo re-consulta la ventana de 7 días, upsert por `(marca, fecha, granularidad)`
evita duplicar puntos.

## Cómo está instalado

`crontab -l` tiene, además de lo que ya hubiera en el sistema:

```
*/15 * * * * /config/Projects/reto02-win/cron/run_pipeline.sh trends  >> .../logs/cron.log 2>&1
*/30 * * * * /config/Projects/reto02-win/cron/run_pipeline.sh news    >> .../logs/cron.log 2>&1
*/30 * * * * /config/Projects/reto02-win/cron/run_pipeline.sh play    >> .../logs/cron.log 2>&1
5,35 * * * * /config/Projects/reto02-win/cron/run_pipeline.sh enrich  >> .../logs/cron.log 2>&1
```

`run_pipeline.sh` es el único punto de entrada que cron invoca: fija rutas
absolutas (cron no hereda el shell interactivo del usuario) y **levanta la
instancia de Postgres del proyecto si no está corriendo**, porque esa instancia
no es un servicio systemd — se administra a mano con `pg_ctl` (ver `db/README.md`).
Si la máquina se reinicia, la primera corrida de cron la vuelve a levantar sola;
no hace falta intervención manual salvo que `pg_ctl` mismo falle (revisar
`logs/cron.log` en ese caso).

## Logs

- `logs/pipeline.log` — log estructurado del propio pipeline Python (qué se
  insertó, cuántos duplicados se filtraron, excepciones con traceback si una
  fuente falla)
- `logs/cron.log` — stdout/stderr crudo de cada invocación de cron, incluye
  el arranque de Postgres cuando ocurre

Una fuente que falla (timeout de red, cambio de formato de la API, etc.) no
tumba a las demás: `pipeline.py` aísla cada fuente con `_safe()` y loguea el
traceback completo en vez de propagar la excepción.

## TikTok: cómo correrlo manualmente mientras no esté automatizado

```bash
# 1. Con sesión iniciada en un navegador real, ir al perfil de la cuenta y
#    hacer scroll acumulando URLs de video (ver ingest/tiktok.py, comentario
#    final "Flujo de descubrimiento con sesión").
# 2. Guardar las URLs, una por línea, en un archivo.
# 3. Correr (necesita el intérprete con Playwright instalado):
/lsiopy/bin/python3 /config/Projects/reto02-win/normalize/pipeline.py \
    --skip-trends --skip-news --skip-play \
    --tiktok /ruta/a/urls.txt
```

Dado que la cuenta postea a ~0.5-1 videos/día (ver medición en CLAUDE.md),
correr este paso 1 vez al día es suficiente para no perder continuidad.
