# Informe de pruebas — auditoría nov-2026

**Rama:** `audit/noviembre-2026`  **Fecha:** 2026-11-27

## Resultado del banco completo

```
✔ probar_audit:       VERDE · 23 bien, 0 mal   ← NUEVO (auditoría nov-2026)
✔ probar_azar:        VERDE · 18 bien, 0 mal
✔ probar_basicos:     VERDE · 25 bien, 0 mal
✔ probar_cliente:     SALTADA · no está C:\GunBound-Legacy\GunBound.exe
✔ probar_entrada:     VERDE · 34 bien, 0 mal
✔ probar_fin:         VERDE · 31 bien, 0 mal
✔ probar_lista:       VERDE · 11 bien, 0 mal
✔ probar_panel:       VERDE · 82 bien, 0 mal
✔ probar_personajes:  VERDE · 28 bien, 0 mal
✔ probar_premio:      VERDE · 16 bien, 0 mal   ← +6 (fix B-2v2)
✔ probar_rangos:      VERDE · 63 bien, 0 mal
✔ probar_sala:        VERDE · 39 bien, 0 mal
✔ probar_silencio:    VERDE · 3 bien, 0 mal
✔ probar_tienda:      VERDE · 19 bien, 0 mal
── 0 con rojas · ~45 s
```

**Línea base pre-auditoría:** 363 pruebas verdes (sin `probar_audit.py`).  
**Post-auditoría nov-2026:** 386 pruebas verdes (+23 nuevas de regresión).  
**Post-fix B-2v2:** 392 pruebas verdes (+6 nuevas para race condition 2v2/3v3).

## Nuevas pruebas de regresión (`pruebas/probar_audit.py`)

| ID prueba | Bug cubierto | Descripción |
|-----------|-------------|-------------|
| B-01-1 | B-01 | 0x4200 de un NO-llave no termina la partida |
| B-01-2 | B-01 | 0x4200 fuera de sala se ignora |
| B-01-3 | B-01 | 0x4200 de la llave sí termina la partida |
| B-01-4 | B-01 | Segundo 0x4200 tras el fin se ignora |
| B-02-1 | B-02 | 0x3232 durante partida no cambia estado a ESPERA |
| B-02-2 | B-02 | 0x3232 con ganador definido lleva a ESPERA |
| B-03-1 | B-03 | Móvil inválido (16) no se guarda, queda AL_AZAR |
| B-03-2 | B-03 | Móviles 15 y 17 (válidos) se guardan |
| B-04-1 | B-04 | armar_inicio completado sin crash con 2 jugadores |
| B-04-2 | B-04 | armar_inicio completado sin crash con 4 jugadores |
| B-05-1 | B-05 | /movil 14 aceptado (confirmación con '14') |
| B-05-2 | B-05 | /movil 14 guarda 14 en la sesión |
| B-05-3 | B-05 | /movil 15 aceptado (confirmación con '15') |
| B-05-4 | B-05 | /movil 15 guarda 15 en la sesión |
| B-05-5 | B-05 | /movil 16 manda mensaje de uso |
| B-05-6 | B-05 | /movil 16 rechazado (el móvil no cambió de 15) |
| B-06-1 | B-06 | Cambiar mapa durante partida se ignora |
| B-09-1 | B-09 | clave_dinamica con inputs largos trunca y devuelve 16 bytes |
| B-09-2 | B-09 | Truncación equivalente: 20 chars = 12 chars truncado |
| B-09-3 | B-09 | clave_dinamica con inputs normales no falla |
| B-10-1 | B-10 | Cuando no quedan IDs el server manda 0x5101 |
| B-08-1 | B-08 | _lugar_libre devuelve None con 255 lugares ocupados |
| B-08-2 | B-08 | Control: con 254 ocupados devuelve el 254 libre |
| B-2v2-1 | B-2v2 | 2v2: equipo B muerto → 0x4410 gana A |
| B-2v2-2 | B-2v2 | 2v2 race: 0x4413 llega a llave aunque los otros mandaron 0x3232 antes |
| B-2v2-3 | B-2v2 | 2v2 race: llave (ganadora) recibe +3 GP y +150 oro |
| B-2v2-4 | B-2v2 | 2v2 race: otro ganador (no-llave) también recibe +3 GP y +150 oro |
| B-2v2-5 | B-2v2 | 2v2 race: perdedor: 0 GP, +20 oro |
| B-2v2-6 | B-2v2 | 2v2 race: otro perdedor: 0 GP, +20 oro |

## Cobertura por módulo

| Módulo | Pruebas que lo cubren |
|--------|----------------------|
| `partida.py` | probar_audit (B-01, B-04), probar_fin, probar_premio (B-2v2) |
| `sala.py` | probar_audit (B-02, B-03, B-06, B-10), probar_sala, probar_fin, probar_lista |
| `comandos.py` | probar_audit (B-05) |
| `mundo.py` | probar_basicos, probar_silencio |
| `entrada.py` | probar_audit (B-08), probar_entrada |
| `cifrado.py` | probar_audit (B-09), probar_basicos |
| `pase.py` | probar_basicos |
| `base.py` | probar_personajes, probar_entrada |
| `tienda.py` | probar_tienda |
| `rangos.py` | probar_rangos |
| `panel.py` | probar_panel |
| `premio.py` | probar_premio |

## Límites del banco

- `probar_cliente` requiere el ejecutable del cliente (`C:\GunBound-Legacy\GunBound.exe`). Se salta automáticamente si no está.
- Las pruebas de protocolo usan el robot (`pruebas/robot.py`), que implementa el protocolo medido en el cliente real. No reemplazan la prueba manual con el juego.
- B-04 (colisión de posiciones) se verifica sólo con smoke test (el juego arranca sin crash). Verificar coordenadas exactas requiere decodificar el paquete 0x3432 completo.
- B-07 (límite de conexiones pre-login) no tiene prueba de integración por la complejidad de abrir 255+ conexiones TCP simultáneas en el banco.
