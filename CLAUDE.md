# GunBound (Eñeños) — la guía

> Server de GunBound para la plataforma Eñeños, en Python, para Linux (Docker). Lo lee **Claude al empezar cada
> sesión**: acá van las reglas y los punteros. Las historias, en `documentacion/`.
> Arrancado el **2026-11-16** desde el laboratorio de Codex (`D:\Gunbound\Legacy-Laboratorio`, ver
> `documentacion/CREDITOS.md`).

## 0 · Las reglas que no se negocian

```
⛔ NADA SE SUBE A PROD SIN QUE BENJA LO PIDA.  prod = rama main; el de prueba = develop (se actualiza solo).
⛔ EL REPO NO SE PUBLICA NI SE EMPUJA SIN SU ORDEN.  Hoy vive sólo en esta PC.
⛔ NINGUNA BASE DE JUGADORES VA AL REPO.  `estado/` y los *.db están gitignorados.
⛔ EL CLIENTE NO VA AL REPO.  Es de Softnyx/Legacy: se arma en la PC con herramientas/parchar_cliente.py.
⛔ LA CLAVE DE PRUEBA (estado/clave_prueba.json) NO VA A NINGÚN SERVER DE VERDAD: con ella cualquiera se firma un pase.
```

## 1 · Qué es, en una pantalla

```
launcher ──usuario y clave──▶ Cuenta Eñeños ──pase (aud=gunbound | gunbound-prueba)──▶ launcher
launcher ──POST /canje {pase}──▶ ESTE server ──{usuario: Eñeños ID, ticket: 12 letras, servidor: broker}
launcher ──registro de Windows (IP/puerto del broker) + GunBound.exe <usuario+ticket cifrados>──▶ el juego
juego ──TCP──▶ broker (lista de mundos) ──▶ mundo (login con el ticket, canal, salas, tienda, partida)
juego ◀──▶ juego : la partida va por el TÚNEL del server (0x4500 → 0x4501), no por UDP directo
```

Es el MISMO modelo que EDA: el pase se canjea por un boleto corto, cada server comprueba la firma solo, y hay dos
servers por juego (prod y prueba) con el mismo código y otro `.env`.

## 2 · Bajo qué guiarse

| archivo | para qué |
|---|---|
| **este archivo** | las reglas y el terreno |
| `servidor/MAPA.md` | qué módulo abrir para cada cosa |
| `documentacion/PROTOCOLO_LEGACY.md` | ★ los formatos MEDIDOS del cliente Legacy v179 (dónde está cada lector en el exe) |
| `documentacion/COMO_ENTRA_UN_JUGADOR.md` | el contrato con el launcher y con Cuenta Eñeños |
| `documentacion/CLIENTE.md` | el cliente: los 7 parches, DxWnd, varias instancias |
| `documentacion/MAPA_DEL_CLIENTE.md` | ★ viento, rangos (19 = pollito), bandera = país, GM, comandos «/», los plazos de la red vieja; el detalle en `investigacion/` |
| `documentacion/PROBAR_CON_EL_JUEGO.md` | la mesa: varios clientes manejados por API, sin tocar el mouse |
| `despliegue/LEEME.md` | Docker, prod y prueba, mudarse de máquina |
| `documentacion/CREAR_PERSONAJE.md` | lo que hace falta para crear 2 personajes desde el launcher (contrato propuesto, decisiones pendientes) |
| `documentacion/PENDIENTE.md` | lo que falta, en orden |

## 3 · El banco

```bash
python pruebas/correr_todas.py        # todas, con resumen (fuerza utf-8: la consola de esta PC está en cp949)
python pruebas/correr_todas.py -v     # y la salida de las rojas
```

★ **Toda prueba tiene su control al revés** (el caso que DEBE fallar). El Dockerfile corre el banco: si falla, la
imagen no se arma y el contenedor que andaba sigue andando.
⚠ El robot (`pruebas/robot.py`) prueba que el server es coherente con lo MEDIDO. Que ande con el juego de verdad se
prueba con la mesa (`documentacion/PROBAR_CON_EL_JUEGO.md`).

## 4 · Cómo se trabaja acá

- **Medir antes que deducir.** Cada formato del protocolo se sacó del LECTOR del cliente (dirección en el exe) o
  de una traza (`GB_TRAZA=1`). El formato del Serv2 o del emulador viejo NO es la ley: el Legacy difiere en casi todo.
- **El cliente se toca último.** Los parches del exe son 5 y están medidos; antes de sumar uno, buscar si el server
  puede hacerlo.
- **Explicar en criollo.** El desensamblado va a la documentación, no a la respuesta.
- ⚠ En Git Bash, un texto que empieza con `/` (un comando del chat como `/practica`) se convierte en ruta de
  Windows: anteponer `MSYS_NO_PATHCONV=1`.
- ⚠ Docker vive DENTRO del WSL (`wsl -d Ubuntu-26.04 -u root`). El WSL se apaga solo si nadie lo usa (y con él los
  contenedores): para probar, dejar un `wsl … sleep 86400` corriendo. Y el reenvío de `localhost` de Windows al WSL
  pasa TCP pero NO UDP: los clientes van a la IP del WSL (`ip -4 addr show eth0`), no a 127.0.0.1.

## 5 · El terreno

```
servidor/       el server (Python puro + pycryptodome). Entra entero en la imagen
  datos/          mapas.json (lugares de salida) · precios_avatar.json (el catálogo del Legacy)
pruebas/        el banco (correr_todas.py) + robot.py + arnes.py
herramientas/   lo de escritorio (Windows): parchar_cliente, jugar (launcher de mesa), laboratorio, mesa, ventanas
despliegue/     Dockerfile · docker-compose.yml (prod y prueba) · ejemplo.env · actualizar.sh
documentacion/  las guías
integracion/    cambios para OTROS repos (Cuenta Eñeños), sin aplicar
estado/         (gitignorado) la base local, la clave de prueba, fotos y guiones de prueba
```

Carpetas de sólo lectura: `C:\GunBound-Legacy` (el cliente original: NO se toca), `D:\Gunbound\GB` (el respaldo
entero, catalogado en `D:\Gunbound\CATALOGO_GUNBOUND.md`), `D:\Gunbound\Legacy-Laboratorio` y
`D:\Gunbound\Legacy-Analisis` (el trabajo de Codex). El cliente armado: `D:\Gunbound\Cliente-Enenos`.
