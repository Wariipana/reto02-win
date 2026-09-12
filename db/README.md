# Instancia de Postgres del proyecto

Instancia propia, aislada de las instancias del sistema (`16/main`, puerto 5432) y
de las instancias experimentales de otro proyecto (`/config/.dbengine/pg18`,
`pg19a`). No usa Docker (no disponible en este entorno).

- Binario: PostgreSQL 18.6 (`/usr/lib/postgresql/18/bin`)
- Data dir: `/config/Projects/reto02-win/.pgdata/data` (fuera de git)
- Socket: `/config/Projects/reto02-win/.pgdata/run`
- Puerto: `5433`
- Usuario: `reto02` — `trust` auth sólo por socket Unix local (usado por el pipeline
  vía `connection.py`); las conexiones TCP (127.0.0.1/::1) requieren contraseña
  (`scram-sha-256`) desde que se habilitó el acceso remoto por túnel, ver
  `.cloudflared/README.md`
- Base de datos: `reto02_win`
- Extensión: `pgvector` 0.8.6 (paquete apt `postgresql-18-pgvector`, instalado a
  nivel de sistema pero sólo usado por esta base)

## Arrancar / parar

```bash
# arrancar
/usr/lib/postgresql/18/bin/pg_ctl -D /config/Projects/reto02-win/.pgdata/data \
    -l /config/Projects/reto02-win/.pgdata/logfile start

# parar
/usr/lib/postgresql/18/bin/pg_ctl -D /config/Projects/reto02-win/.pgdata/data stop

# conectar
PGHOST=/config/Projects/reto02-win/.pgdata/run PGPORT=5433 PGUSER=reto02 \
    /usr/lib/postgresql/18/bin/psql -d reto02_win
```

## Esquema

Ver `schema.sql`. Aplicar con:

```bash
PGHOST=/config/Projects/reto02-win/.pgdata/run PGPORT=5433 PGUSER=reto02 \
    /usr/lib/postgresql/18/bin/psql -d reto02_win -f schema.sql
```

`connection.py` expone `get_conn()` para el código Python del proyecto
(usa el DSN de arriba por defecto; sobreescribible con la env var `RETO02_DSN`).
