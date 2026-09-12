# Túnel de Cloudflare para Postgres (acceso remoto)

Expone la instancia de Postgres del proyecto (ver `db/README.md`) a través de
un túnel de Cloudflare, para conectarse con un cliente SQL desde fuera de
este entorno. No usa Cloudflare Access (decisión explícita del usuario) —
la única barrera es la contraseña de Postgres.

## Qué se cambió para permitir esto con seguridad mínima

La instancia usaba `trust` auth (sin contraseña) en todas las conexiones,
incluidas las TCP por `127.0.0.1` — el túnel de Cloudflare termina
localmente y reenvía exactamente a esa dirección, así que dejar `trust` ahí
habría expuesto la base sin ninguna protección real. Se cambió:

1. `ALTER USER reto02 WITH PASSWORD '...'` — contraseña real generada
   (no se guarda en ningún archivo del repo; pídesela al usuario si la
   perdiste, o genera una nueva con `ALTER USER` y reinicia el túnel)
2. `pg_hba.conf`: las líneas `host ... 127.0.0.1/32` y `::1/128` pasaron de
   `trust` a `scram-sha-256`. La línea `local` (socket Unix, usada por el
   pipeline del proyecto vía `db/connection.py`) se queda en `trust` — no
   afecta la seguridad del túnel porque un socket Unix no es alcanzable
   remotamente

## Túnel

- Nombre: `reto02-win-postgres` (id `e617796a-f7b6-4b45-b36b-15a3323f0dc5`)
- Hostname: `pg-reto02.wariipana.de` (CNAME creado en la zona `wariipana.de`,
  que ya gestiona otro proyecto del usuario — no se tocó ningún registro
  existente, como `note.wariipana.de`)
- Config: `tunnel.yml` en este directorio, reenvía TCP crudo (no HTTP) al
  puerto 5433 local
- Credenciales del túnel: `/config/.cloudflared/e617796a-....json` (fuera
  de este repo, en la config global de cloudflared)

## Arrancar / parar

```bash
# arrancar (queda corriendo en background)
nohup cloudflared tunnel --config /config/Projects/reto02-win/.cloudflared/tunnel.yml run \
    > /config/Projects/reto02-win/.cloudflared/tunnel.log 2>&1 &

# ver que está conectado
tail -f /config/Projects/reto02-win/.cloudflared/tunnel.log

# parar
pkill -f "cloudflared tunnel --config /config/Projects/reto02-win/.cloudflared/tunnel.yml"
```

No se dejó como servicio persistente (systemd/cron) — es un túnel bajo
demanda para sesiones de acceso puntual, no para que quede expuesto de
forma indefinida.

## Cómo conectarse desde otra máquina

Cloudflare Tunnel para TCP crudo (no HTTP) requiere el cliente `cloudflared`
también del lado de quien se conecta — no es una URL que un cliente SQL
pueda usar directamente.

```bash
# 1. Instalar cloudflared en la máquina cliente:
#    https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

# 2. Abrir un proxy local hacia el túnel:
cloudflared access tcp --hostname pg-reto02.wariipana.de --url 127.0.0.1:15433

# 3. En otra terminal, conectar cualquier cliente Postgres a localhost:15433:
psql -h 127.0.0.1 -p 15433 -U reto02 -d reto02_win
# pedirá la contraseña de reto02
```

## Riesgo aceptado

Sin Cloudflare Access, cualquiera que descubra el hostname y tenga la
contraseña de Postgres puede leer/escribir los datos reales de terceros que
contiene la base (reseñas de Google Play, mensajes de Discord, tuits — ver
CLAUDE.md). Mitigación mínima aplicada: contraseña fuerte generada
aleatoriamente, autenticación `scram-sha-256` (no envía la contraseña en
claro), y el túnel no queda corriendo permanentemente. Si se necesita acceso
más allá de una sesión puntual, conviene añadir Cloudflare Access encima.
