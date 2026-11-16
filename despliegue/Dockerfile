# El server de GunBound (Eñeños) en un contenedor Linux. Python puro: corre igual en amd64 y en arm64.
# El juego sigue en Windows, en la PC de cada jugador (el launcher de Eñeños lo abre con el boleto del canje).
#
#   docker compose -p gunbound-prod --env-file /opt/gunbound/prod.env -f despliegue/docker-compose.yml up -d --build
#
# EL CONTRATO con el que lo levanta (el conjunto de Eñeños o este compose):
#   · el volumen /datos       — la base de los jugadores (gunbound.db). Es lo ÚNICO que hay que llevar al mudarse
#   · las variables GB_*      — ver despliegue/ejemplo.env
#   · los puertos             — GB_PUERTO_BROKER (TCP) · GB_PUERTO_MUNDO (TCP y UDP) · GB_PUERTO_HTTP (canje; detrás de HTTPS)
#   · ¿anda?                  — GET http://127.0.0.1:$GB_PUERTO_HTTP/salud
FROM python:3.13-slim

WORKDIR /gunbound
RUN pip install --no-cache-dir "pycryptodome==3.24.1"

COPY servidor/ servidor/
COPY pruebas/ pruebas/

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    GB_ESTADO=/datos

# ¿anda? = el banco entero (sin el cliente de Windows: esa prueba se salta sola). Si falla, la imagen NO se arma
# y el contenedor que andaba sigue andando.
RUN python pruebas/correr_todas.py > /tmp/banco.txt 2>&1 || (cat /tmp/banco.txt; exit 1)

HEALTHCHECK --interval=2m --timeout=10s --start-period=15s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/salud' % (os.environ.get('GB_PUERTO_HTTP') or 8371), timeout=5)"

VOLUME ["/datos"]
CMD ["python", "-m", "servidor"]
