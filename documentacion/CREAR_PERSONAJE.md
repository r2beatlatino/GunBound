# Crear personaje desde el launcher — hecho

> 16-nov-2026. Implementado en el server (`ajustes.py`, `base.py`, `boletos.py`, `web.py`, `comandos.py`, `mundo.py` y
> `datos/paises_iso.json`). Queda listo para que el launcher conecte la pantalla de personajes.

## 1 · Lo que el CLIENTE permite (MEDIDO, `MAPA_DEL_CLIENTE.md`)

- **No tiene pantalla de crear personaje** ni de elegir género o nick: llega al mundo con lo que el server le
  manda en el login (0x1012: nick, byte de género, los 4 WORD de rango, GP, oro). ⇒ La creación vive TODA afuera:
  launcher + este server.
- **La bandera no la elige el cliente ni la saca de la IP**: es el 4.º WORD de rango que manda el server
  (`servidor/datos/paises.json`, 0 = «?»). El server sugiere un país a partir de la cabecera `CF-IPCountry`
  (tabla `servidor/datos/paises_iso.json`), y el menú de creación del launcher lo trae ya marcado.
- Rango, GP y país **sólo se leen al entrar al mundo**: cambiarlos desde el launcher, el chat (`/pais`) o el panel
  se ve al volver a entrar.

## 2 · Decisiones (16-nov) y modelo en `base.py`

- **2 personajes por cuenta** (`PERSONAJES_POR_CUENTA = 2` en `ajustes.py`, configurable con `GB_PERSONAJES`).
- **Cada personaje tiene lo suyo**: nick (`^[A-Za-z0-9_]{3,12}$`, único sin distinguir mayúsculas), género (`m` o `f`,
  los dos iguales o distintos), país, inventario, oro y cash propios (`GB_ORO_INICIAL`, `GB_CASH_INICIAL`). Todos
  nacen **pollito** (GP 0 → rango 19).
- **El país se puede cambiar después**: desde el launcher (`POST /personajes/pais`) o dentro del juego con
  `/pais <0-241>` (se ve al volver a entrar).
- **GM por cuenta**: `es_gm` se evalúa sobre `cuenta in self.gm`, así que los dos personajes de una cuenta GM tienen
  rango 20 y comandos de GM.
- **Rangos por GP fijo** (`servidor/rangos.py`). Opción futura: rangos altos «por puesto, como el original» (desde
  6900 GP, actualización diaria; la tabla está en `investigacion/CUENTA_RANGOS_BANDERA_OPCODES.md` §1.3).

En SQLite (`jugadores`), por historia la clave `enenos_id` pasa a ser el **id del personaje** (es el «usuario» del
juego que usan sesiones, boletos e inventario) y se agrega la columna `cuenta INTEGER` (el Eñeños ID de la persona,
con índice `jugadores_cuenta`):

```
personaje 1:  id = cuenta                      (las cuentas anteriores conservan el mismo id)
personaje 2:  id = 1_000_000_000 + cuenta      (DESPLAZAMIENTO_2; entra cómodo en 16 dígitos)
```

El canje directo viejo (`POST /canje {"pase"}`) llama a `crear_si_falta`: crea el personaje 1 con nick `GB<cuenta>`
si la cuenta todavía no tiene ninguno.

## 3 · El contrato HTTP con el launcher (`servidor/web.py`)

El pase de Cuenta Eñeños es de un solo uso (`jti`), así que `POST /personajes` lo canjea por una **ficha de launcher**
(`boletos.Fichas`: 24 caracteres alfanuméricos, válida **10 minutos** en memoria, `ficha → cuenta`). Todas las rutas
aceptan también el prefijo `/gunbound` o `/gunbound-prueba`.

```
POST /personajes                   {"pase": "<JWT>"}
→ 200 {"ficha": "<24 chars>",
       "personajes": [{"id": <int>, "nick": "...", "genero": "m"|"f", "pais": <int>, "rango": <int>, "gp": <int>}],
       "maximo": 2,
       "pais_sugerido": <int>}     (0 si no viene CF-IPCountry o no está en paises_iso.json)
→ 401 pase inválido · 409 pase ya usado · 403 cuenta suspendida · 503 sin clave pública

POST /personajes/crear             {"ficha": "...", "nick": "...", "genero": "m"|"f", "pais": <0..241>}
→ 200 {"personajes": [...]}
→ 400 datos inválidos · 401 ficha vencida · 403 ya tiene el máximo (o suspendida) · 409 nick ocupado

POST /personajes/pais              {"ficha": "...", "personaje": <id>, "pais": <0..241>}
→ 200 {"personajes": [...]}
→ 400 datos inválidos · 401 ficha vencida · 403 el personaje no es de esa cuenta (o suspendida)

POST /canje                        {"ficha": "...", "personaje": <id>}   (o {"pase"} como antes → personaje 1)
→ 200 {"usuario": "<id del personaje>", "ticket": "<12>", "servidor": "host:puerto", "nick": "...", "nuevo": false}
→ 400 datos inválidos · 401 ficha vencida · 403 el personaje no es de esa cuenta (o suspendida)
```

## 4 · Pendiente para el panel (los comandos de hoy se vuelven botones)

| hoy, en el chat del juego (GM) | en el panel |
|---|---|
| `/gp <nick> <n\|+n\|-n>` | fijar o sumar GP (el rango se recalcula solo) |
| `/rangofijo <nick> <n\|auto>` | íconos especiales (VIP, coronas, 21+) o volver al automático |
| `/pais <nick> <n>` | corregir la bandera |
| `/dar <nick> <oro> [cash]` · `/aviso <texto>` · `/quien` | saldo · aviso a todos · quién está |
| (falta) echar: **0x1FFF** `[motivo]` | el cliente corta y muestra el cartel |
| (falta) mantenimiento: **0x1FFA** `[segundos]` | el cliente muestra la cuenta regresiva |
| (falta) avisos de color: 0x5101 con `!` `@` `#` `$` `%` `^` | aviso en rojo, verde… |

Como en R2Beat (allá el panel sólo habla con `api_web.py`): el panel no toca la base, llama a una API del server
(`GET/POST /gunbound/admin/...` en 127.0.0.1, detrás de Caddy con permisos).
