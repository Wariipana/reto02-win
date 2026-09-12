"""Conexión a la instancia de Postgres propia del proyecto (aislada de las
instancias del sistema/DBEngine). Ver README para cómo levantarla/pararla."""
import os

import psycopg

DEFAULT_DSN = (
    "host=/config/Projects/reto02-win/.pgdata/run "
    "port=5433 "
    "dbname=reto02_win "
    "user=reto02"
)


def get_conn():
    dsn = os.environ.get("RETO02_DSN", DEFAULT_DSN)
    return psycopg.connect(dsn)
