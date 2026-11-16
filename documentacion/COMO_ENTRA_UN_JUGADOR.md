# Cómo entra un jugador — el contrato con el launcher y con Cuenta Eñeños

> ★ Para el agente del launcher, la guía completa (pantalla de personajes, registro con sus tipos, lista del
> cliente, cómo probar): `PARA_EL_LAUNCHER.md`.

Es el mismo camino que EDA (`launcher_tauri/src-tauri/src/eda.rs`: `canjear` + `abrir`). Lo que cambia es cómo se
le da al juego el usuario y el server.

## 1 · Cuenta Eñeños da el pase

`POST /cuentas/pase {"juego": "gunbound"}` (o `"gunbound-prueba"` si la casilla «Servidor de prueba» está marcada).
⚠ Cuenta Eñeños todavía no conoce esos dos `aud`: el cambio está en `integracion/cuenta_enenos_gunbound.patch`
(sin aplicar: esa rama la trabaja otra sesión).

## 2 · La ficha de personajes y el canje (este server)

El launcher puede entrar por el flujo nuevo de personajes (para elegir o crear hasta 2 personajes) o por el canje
directo con el pase (personaje 1). Todas las rutas aceptan el prefijo `/gunbound` o `/gunbound-prueba`.

### Flujo con selección/creación de personaje (ver `CREAR_PERSONAJE.md`)

1. `POST /gunbound/personajes` con `{"pase": "<JWT>"}` → devuelve `{"ficha", "personajes", "maximo", "pais_sugerido"}`.
   La `ficha` dura **10 minutos** y reemplaza al pase de un solo uso para los pedidos siguientes.
2. Si el jugador crea uno nuevo: `POST /gunbound/personajes/crear` con `{"ficha", "nick", "genero": "m"|"f", "pais"}`.
   Si cambia la bandera desde el launcher: `POST /gunbound/personajes/pais` con `{"ficha", "personaje", "pais"}`.
3. Al elegir personaje para jugar: `POST /gunbound/canje` con `{"ficha", "personaje": <id>}` → devuelve
   `{"usuario": "<id del personaje>", "ticket": "Ab3dEf…(12)", "servidor": "juego.eñeños.link:8372", "nick": "…", "nuevo": false}`.
   (Si el personaje no pertenece a esa cuenta, responde `403`.)

### Flujo directo (sin selector de personaje)

```
POST https://<host>/gunbound/canje            (o /gunbound-prueba/canje)    Content-Type: application/json
{"pase": "<JWT>"}
→ 200 {"usuario": "10000570", "ticket": "Ab3dEf…(12)", "servidor": "juego.eñeños.link:8372", "nick": "…", "nuevo": true}
→ 401 pase inválido (firma, aud, vencido) · 409 pase ya usado · 403 suspendido · 503 el server no tiene la clave
```

- `usuario` = el id del personaje (sólo dígitos: `cuenta` para el personaje 1, `1_000_000_000 + cuenta` para el 2).
  `ticket` = 12 letras y números (entra en la contraseña del juego).
- El boleto vale `GB_BOLETO_HORAS` (12 h) y se puede usar varias veces mientras el juego está abierto (el cliente
  re-entra al mundo con él). Un canje nuevo del mismo personaje lo reemplaza.
- Quien entra por primera vez con `{"pase"}` directo nace en la base con nick `GB<id>` y lo cambia en el chat con
  `/nombre`.

## 3 · El launcher abre el juego

1. Valida lo que llegó: `usuario` `^[0-9]{1,16}$`, `ticket` `^[A-Za-z0-9]{12}$`, `servidor` `^[A-Za-z0-9.\-]+:[0-9]{1,5}$`.
2. Escribe el registro `HKCU\Software\softnyx\Enenos` (el cliente parchado lee ahí, ver CLIENTE.md):
   `IP` = host del `servidor` (⚠ el exe lo resuelve con gethostbyname: un nombre debería andar; sin medir), `port`
   (DWORD) = su puerto, `ScreenMode` = `Windowed`, `ScreenDetail` = `1600x1200`, `Location`/`Path` = carpeta del
   cliente con `\` al final, y el resto de `REGISTRO_BASE` de `herramientas/jugar.py`.
   ⚠ RESPETAR LOS TIPOS: `InterfaceMode`, `Background`, `ShootingMode`… son REG_BINARY de un byte; como texto, el
   HUD sale mezclado (CLIENTE.md).
3. Arma el argumento: AES-128-ECB con la clave `FAEE85F24073D9161390197F6E562A67` de
   `usuario` (16, relleno con ceros) + `ticket` (16) + 16 ceros → HEX en MAYÚSCULA.
4. Abre `GunBound.exe` con ESE texto como línea de comandos entera (en Rust: `raw_arg`, y el programa sin la ruta
   en la línea: `CreateProcess` con `lpCommandLine` = el hex). ⚠ Con la ruta del exe adelante, el juego se cierra.

La referencia que anda: `herramientas/jugar.py` (canje → registro → exe) y `herramientas/mesa.py` (lo mismo con
Frida, para varias instancias).

## 4 · prod y prueba

| | prod | prueba |
|---|---|---|
| `aud` | `gunbound` | `gunbound-prueba` |
| broker / mundo / canje | 8372 / 8370 / 8371 | 9372 / 9370 / 9371 |
| base | `/opt/gunbound/estado-prod` | `/opt/gunbound/estado-prueba` |

Un pase de uno no sirve en el otro (lo prueba `probar_basicos` y se midió con los dos contenedores).
