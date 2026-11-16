# Crear personaje desde el launcher — lo que hace falta (mapa, sin construir)

> 16-nov-2026. Para cuando el launcher tenga la ficha de GunBound. Benja: «poder elegir crear 2 char, ambos F o
> ambos M, nick, y primero empiezan de pollito»; «la bandera se seleccionaba por IP: ¿sigue andando o se deja para
> el menú de creación?».

## 1 · Lo que el CLIENTE permite (MEDIDO, `MAPA_DEL_CLIENTE.md`)

- **No tiene pantalla de crear personaje** ni de elegir género o nick: llega al mundo con lo que el server le
  manda en el login (0x1012: nick, byte de género, los 4 WORD de rango, GP, oro). ⇒ La creación vive TODA afuera:
  launcher + este server.
- **La bandera no la elige el cliente ni la saca de la IP**: es el 4.º WORD de rango que manda el server
  (`servidor/datos/paises.json`, 0 = «?»). En los servers viejos que tenemos (TorHammer) el país se elegía en el
  formulario de registro de la web; lo de «por IP» era del lado del server de Softnyx (no está en ningún binario
  ni base que tengamos). ⇒ Se puede hacer igual que antes — el server sugiere uno por la IP — pero lo natural es
  el menú de creación del launcher, con el país sugerido ya marcado.
- Rango, GP y país **sólo se leen al entrar al mundo**: cambiarlos desde el panel se ve al volver a entrar.

## 2 · Persona ≠ personaje (como R2Beat)

Hoy la base tiene UN jugador por Eñeños ID (`jugadores.enenos_id` es la clave). Para dos personajes:

```
personajes (id INTEGER PRIMARY KEY  ← el "usuario" del juego (dígitos), desde 10.000.000 como el Eñeños ID nuevo
            enenos_id               ← la persona; a lo sumo 2 por persona (GB_PERSONAJES_POR_CUENTA)
            nick UNIQUE NOCASE, genero, pais, gp=0, oro, cash, avatar, …)
```

- Cada personaje tiene su propio inventario, oro, GP y rango: nace **pollito** (GP 0 → rango 19).
- Género libre en cada uno: los dos varones, las dos mujeres o uno y uno.
- La cuenta vieja (hoy `jugadores` por Eñeños ID) se muda como su personaje 1.
- Lo que es de la PERSONA (baneo, cash comprado, GM) se decide aparte: ⚠ decisión de Benja (¿el cash es de la
  cuenta o del personaje?; ¿un baneo cae sobre los dos?).

## 3 · El contrato propuesto con el launcher

El pase de Cuenta Eñeños es de un solo uso (`jti`), así que el primer pedido lo canjea por una ficha corta de
launcher y el resto usa esa ficha.

```
POST /gunbound/personajes          {"pase": "<JWT>"}
→ 200 {"ficha": "<para los próximos 10 min>", "personajes": [{"id", "nick", "genero", "pais", "rango", "gp"}],
       "maximo": 2, "pais_sugerido": 9}

POST /gunbound/personajes/crear    {"ficha", "nick", "genero": "m"|"f", "pais": 1..241}
→ 200 {"personajes": [...]} · 409 nick ocupado · 400 nick inválido (3–12: letras, números, _) · 403 ya tiene 2

POST /gunbound/canje               {"ficha", "personaje": <id>}      (o {"pase"} como hoy, = el personaje 1)
→ 200 {"usuario": "<id del personaje>", "ticket", "servidor"}        ← igual que hoy: el resto no cambia
```

`pais_sugerido`: el país de la IP del pedido. Opciones, de menos a más trabajo: la cabecera de país que ya pone el
proxy si va detrás de Cloudflare (`CF-IPCountry`), o una base GeoIP chica (p. ej. DB-IP Lite, libre) en el
contenedor. Hace falta la tabla ISO-2 → número: las dos letras están dibujadas en `nationcode.img`
(`investigacion/paises_*.png`), en el mismo orden que `paises.json`.

## 4 · Para el panel (los comandos de hoy se vuelven botones)

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

## 5 · Lo que falta decidir (Benja)

1. ¿Dos personajes por cuenta, fijo, o configurable?
2. ¿El cash es de la persona (compartido) o de cada personaje?
3. ¿El país se puede cambiar después (y cuántas veces), o sólo un GM?
4. ¿Rangos altos por GP fijo (como ahora) o por PUESTO como el original (desde 6900 GP, actualización diaria)?
