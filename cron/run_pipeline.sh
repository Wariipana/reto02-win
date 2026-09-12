#!/usr/bin/env bash
# Wrapper invocado por cron. Recibe la fuente como $1 (trends|news|play).
# cron corre con un PATH mínimo y sin el entorno interactivo del usuario,
# así que fijamos rutas absolutas explícitamente.
set -euo pipefail

PROJECT_DIR="/config/Projects/reto02-win"
PG_BIN="/usr/lib/postgresql/18/bin"
PG_DATA="$PROJECT_DIR/.pgdata/data"
FUENTE="${1:?uso: run_pipeline.sh <trends|news|play|enrich>}"

# La instancia de Postgres del proyecto no es un servicio systemd (se levantó
# a mano con pg_ctl), así que no arranca sola tras un reinicio de la máquina.
# La levantamos aquí si hace falta, de forma idempotente.
if ! "$PG_BIN/pg_ctl" -D "$PG_DATA" status >/dev/null 2>&1; then
    "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$PROJECT_DIR/.pgdata/logfile" start
    sleep 2
fi

if [ "$FUENTE" = "enrich" ]; then
    cd "$PROJECT_DIR/nlp"
    exec python3 enrich.py
else
    cd "$PROJECT_DIR/normalize"
    exec python3 pipeline.py --only "$FUENTE"
fi
