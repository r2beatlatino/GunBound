# El server, módulo por módulo

Todo corre en UN proceso y UN hilo (asyncio): `python -m servidor` levanta las tres piezas.

| módulo | qué hace | mensajes |
|---|---|---|
| `__main__.py` | arranca broker + mundo + web; `Server` es lo que usan las pruebas | — |
| `ajustes.py` | TODAS las variables `GB_*` (no hay IPs ni rutas escritas en otro lado) | — |
| `broker.py` | la lista de mundos | 0x1013 → 0x1312 · 0x1100 → 0x1102 |
| `web.py` | HTTP: personajes, canje del pase y salud | `POST /personajes` · `/personajes/crear` · `/personajes/pais` · `POST /canje` · `GET /salud` |
| `pase.py` | comprueba el pase de Cuenta Eñeños SOLO (firma Ed25519, aud, exp, jti) | — |
| `boletos.py` | el boleto de 12 letras (contraseña) y las fichas temporales del launcher | — |
| `firma_ed25519.py` | Ed25519 en Python puro (copia del de R2Beat) | — |
| `cifrado.py` | el AES estático y el dinámico, y el argumento del exe | — |
| `paquete.py` | el sobre (largo, secuencia, comando) y el cortador del chorro TCP | — |
| `mundo.py` | las conexiones del mundo y el reparto de cada comando; el eco UDP | — |
| `sesion.py` | UNA conexión: lo de la conexión (no lo de la sala ni lo de la cuenta) | — |
| `entrada.py` | ficha, login, buscar a alguien | 0x1000/1001 · 0x1010/1012 · 0x1032 · 0x1020/1021 |
| `canal.py` | el lobby: quién está y el chat | 0x2001 · 0x200E/200F · 0x2010/201F |
| `rangos.py` | el rango sale del GP (el cliente no tiene tabla), GM = 20, rango fijo; `insignias(j)` = los 4 WORD (rango ×3 + país): el ÚNICO lugar que los arma | — (lo usan 0x1012, 0x200E, 0x2111) |
| `sala.py` | salas: lista, crear, entrar, salir, opciones | 0x2100/2103 · 0x2104/2105 · 0x2110/21F5/2111 · 0x2120/2121 · 0x3001 · 0x3010/3020/3400 · 0x31xx · 0x32xx |
| `partida.py` | empezar, el túnel, fin del Jewel, resultado | 0x3430/3432 · 0x4500/4501 · 0x4200/4410 · 0x4100 · 0x4412/4413 |
| `tienda.py` | inventario, compra, ponerse ropa, saldos | 0x1090/1091 · 0x6000/6001 · 0x6004 · 0x6008/6009 · 0x600E/600F · 0x6020/6021 · 0x6100/6101 · 0x6104/6105 |
| `comandos.py` | los /comandos del chat (y los de GM) | 0x5100 → 0x5101 |
| `base.py` | SQLite: jugadores, inventario, movimientos | — |
| `registro.py` | el log (a la salida; Docker lo guarda) | — |

Los formatos de cada mensaje, con la dirección del lector en el exe: `documentacion/PROTOCOLO_LEGACY.md`.
