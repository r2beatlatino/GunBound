#!/usr/bin/env bash
# despliegue/actualizar.sh — pone un entorno en lo último de SU rama y lo reinicia, sólo si cambió algo.
#
#   bash /opt/gunbound/prueba/despliegue/actualizar.sh prueba     # develop → gunbound-prueba (cron, cada 5 min)
#   bash /opt/gunbound/prod/despliegue/actualizar.sh prod         # main    → gunbound-prod   (a mano: lo aprueba Benja)
#   … --forzar                                                     # rearma aunque no haya cambios
#
# ★ Si el banco falla, la imagen NO se arma (el Dockerfile corre pruebas/correr_todas.py) y el contenedor que andaba
#   SIGUE andando: un PR roto en develop no tira el server de prueba.
# ★ Antes de cambiar nada: el RESPALDO de la base (/opt/gunbound/respaldos/, quedan los últimos 30). Después: que
#   conteste /salud; si no contesta, VUELVE al commit anterior y lo rearma.
set -euo pipefail

ENTORNO="${1:?uso: actualizar.sh prod|prueba [--forzar]}"
BASE=/opt/gunbound
case "$ENTORNO" in
    prod) RAMA=main ;;
    prueba) RAMA=develop ;;
    *) echo "⛔ entorno: prod o prueba"; exit 1 ;;
esac
DIR="$BASE/$ENTORNO"
ENV="$BASE/$ENTORNO.env"
cd "$DIR"
git rev-parse --verify --quiet "origin/$RAMA" >/dev/null || RAMA=main     # (develop todavía no existe)

git fetch --quiet origin "$RAMA"
ANTES="$(git rev-parse --short HEAD)"
AHORA="$(git rev-parse --short "origin/$RAMA")"
CORRIENDO="$(docker ps --filter "name=^gunbound-$ENTORNO$" --format '{{.Names}}')"
if [ "${2:-}" != "--forzar" ]; then
    [ "$ANTES" = "$AHORA" ] && [ -n "$CORRIENDO" ] && exit 0                     # nada nuevo
    [ "$AHORA" = "$(cat "$BASE/$ENTORNO.fallido" 2>/dev/null)" ] && exit 0      # ya falló: no reintentar
fi

echo "$(date '+%F %T') $ENTORNO ($RAMA): $ANTES → $AHORA"
ESTADO="$(sed -n 's/^GB_ESTADO_DIR=//p' "$ENV")"
if [ -n "$ESTADO" ] && [ -f "$ESTADO/gunbound.db" ]; then                # ★ el respaldo, ANTES (sqlite3 .backup: con WAL, copiar el archivo no alcanza)
    mkdir -p "$BASE/respaldos"
    docker run --rm -v "$ESTADO:/datos" -v "$BASE/respaldos:/r" python:3.13-slim \
        python -c "import sqlite3,sys; s=sqlite3.connect('/datos/gunbound.db'); d=sqlite3.connect(sys.argv[1]); s.backup(d)" \
        "/r/gunbound-$ENTORNO-$(date '+%Y%m%d-%H%M%S')-$ANTES.db"
    ls -1t "$BASE/respaldos/gunbound-$ENTORNO-"*.db | tail -n +31 | xargs -r rm -f
fi
armar() {
    docker compose -p "gunbound-$ENTORNO" --env-file "$ENV" -f despliegue/docker-compose.yml up -d --build --quiet-pull
}
git reset --hard --quiet "origin/$RAMA"
if ! armar; then
    echo "$(date '+%F %T') ⛔ $ENTORNO: no se pudo armar ($AHORA). Sigue el anterior."
    echo "$AHORA" > "$BASE/$ENTORNO.fallido"
    git reset --hard --quiet "$ANTES"
    exit 1
fi
sleep 5
PUERTO="$(sed -n 's/^GB_PUERTO_HTTP=//p' "$ENV")"
if ! curl -fsS "http://127.0.0.1:${PUERTO:-8371}/salud" >/dev/null; then
    echo "$(date '+%F %T') ⛔ $ENTORNO: $AHORA no contesta. Vuelvo a $ANTES."
    echo "$AHORA" > "$BASE/$ENTORNO.fallido"
    git reset --hard --quiet "$ANTES"
    armar || true
    exit 1
fi
rm -f "$BASE/$ENTORNO.fallido"
