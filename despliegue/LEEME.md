# El server en Linux (Docker) — prod y prueba

El **juego** corre en Windows (en la PC de cada jugador). El **server** es Python puro y corre donde haya Docker,
amd64 o arm64, con dos copias del mismo código:

| entorno | rama | broker · mundo (TCP+UDP) · canje | se actualiza |
|---|---|---|---|
| **prod** | `main` | 8372 · 8370 · 8371 | a mano, cuando Benja lo aprueba (`actualizar.sh prod`) |
| **prueba** | `develop` | 9372 · 9370 · 9371 | solo, cada 5 min (cron `actualizar.sh prueba`), si el banco pasa |

Es el mismo molde que EDA (`r2beatlatino/EDA`, `despliegue/`). ⛔ Nada de esto está en ningún VPS todavía.

## Levantar

```bash
cp despliegue/ejemplo.env /opt/gunbound/prod.env      # y completar (la IP pública, la clave de Cuenta Eñeños)
docker compose -p gunbound-prod --env-file /opt/gunbound/prod.env -f despliegue/docker-compose.yml up -d --build
curl http://127.0.0.1:8371/salud
```

La imagen corre el banco al armarse: si falla, no se arma y el contenedor anterior sigue andando.

## Afuera

- El broker (8372/9372) y el mundo (8370/9370, TCP **y UDP**) van abiertos en el firewall.
- El canje (8371/9371) escucha en 127.0.0.1: afuera va detrás de Caddy con HTTPS (el boleto es un secreto):
  `/gunbound/*` → 127.0.0.1:8371 y `/gunbound-prueba/*` → 127.0.0.1:9371 (el server acepta las rutas con prefijo).
- Los jugadores se hablan por UDP directo (8363 en cada PC) y, si no anda en 2 s, por el túnel del server
  (`GB_P2P`, ejemplo.env). Para probar varios clientes en una misma PC: `GB_P2P=tunel`.
- `GB_IP_PUBLICA` es la IP (o nombre) que el broker le anuncia al juego para el mundo. En un VPS detrás de NAT
  (Oracle) hay que ponerla: la máquina no ve su IP pública.

## Mudarse de máquina

Llevar la carpeta `GB_ESTADO_DIR` (la base: `gunbound.db`; con WAL, respaldarla con `.backup()` como hace
`actualizar.sh`, no copiando el archivo en caliente) y el `.env`. En la máquina nueva: `docker compose up`.

## Probado (16-nov-2026, en el Docker del WSL de esta PC)

- prod y prueba a la vez, cada uno rechaza el pase del otro (401).
- Dos clientes de verdad: canje → login → canal → sala → partida con turnos y disparo, por el túnel.
- ⚠ Para probar desde Windows, los clientes van a la IP del WSL (UDP no pasa por el `localhost` de Windows).
