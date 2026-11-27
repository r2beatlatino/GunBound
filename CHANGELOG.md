# CHANGELOG

## [Segunda pasada] — 2026-11-27 — rama `audit/noviembre-2026`

### Corregido

- **B-15 (Crítica)** `servidor/mundo.py` — `_conexion`: desde Python 3.11 `asyncio.TimeoutError` es `TimeoutError`, así que el ETIMEDOUT del keepalive TCP caía en el plazo de silencio; con la sala en JUGANDO el `continue` volvía a un `read()` que fallaba al instante sin ceder el lazo y **congelaba el server entero** (el Docker usa 3.13). Ahora, si el lector tiene una excepción, se corta la conexión. El `except` externo pasa a `OSError` (incluye `ConnectionError` y `TimeoutError`).
- **B-11 (Media)** `servidor/partida.py` — `_acreditar`: regresión de B-2v2. Tras el 0x3232 la sala vuelve a ESPERA y la casilla libre la puede tomar alguien que no jugó, que cobraba esa fila. `empezar()` guarda `x.en_partida` (casilla → Eñeños ID) y sólo se paga si coincide.
- **B-16 (Media)** `servidor/sesion.py` — `enviar`: el buffer de salida de una conexión que no lee crecía sin límite (DoS de memoria con chat o túnel). Pasado `TOPE_SALIDA` (2 MB) se corta con `abort()`.
- **B-12 (Baja)** `servidor/sala.py` — `crear`: el cupo se recorta a 1..8, como en `cambiar_cupo` (con cupo 20 entraban 10 y `leer_resultado` rechazaba el premio).
- **B-13 (Baja)** `servidor/base.py` — `sumar`: oro, cash y GP con techo 0xFFFFFFFF (el cliente los lee como u32 y los mostraba dados vuelta).
- **B-14 (Baja)** `servidor/pase.py` — `comprobar`: cabecera o carga JSON que no es objeto → «pase mal formado» (antes `AttributeError` → 500).
- **B-17 (Baja)** `servidor/entrada.py` — `login`: usuario con dígitos no ASCII («²») ya no tira `ValueError` sin respuesta; recibe 0x1012.

### Añadido

- `pruebas/probar_audit.py`: +13 pruebas (B-12 a B-17). `pruebas/probar_premio.py`: +4 (B-11).

### Sin corregir (anotado)

- `servidor/broker.py` — `ip_a_anunciar`: si `GB_IP_PUBLICA` es un nombre, `gethostbyname` bloquea el lazo en cada 0x1100. Con una IP literal no pasa; resolver en cada pedido parece buscado (IP dinámica).
- `servidor/ajustes.py` — `GB_ORO_INICIAL` negativo o `GB_BOLETO_HORAS <= 0` se aceptan sin validar (lo controla el operador).
- Si la llave se va entre el fin y el 0x4412, nadie manda el premio. Hay que medirlo en la mesa.

## [2v2/3v3 fix] — 2026-11-27 — rama `audit/noviembre-2026`

### Corregido

- **B-2v2** `servidor/partida.py` — `resultado`: Race condition en modos 2v2 y 3v3 donde los jugadores no-llave enviaban 0x3232 (volver_del_resultado) antes de que la llave enviara 0x4412 (premio). Esto dejaba `sala.estado = ESPERA` prematuramente y el guard `estado == JUGANDO` rechazaba el 0x4412, dejando los premios sin acreditar. Fix: la condición ahora admite `estado == JUGANDO OR ganador is not None`, preservando el flujo normal y cubriendo el caso de race condition.

### Añadido

- `pruebas/probar_premio.py` — 6 nuevas pruebas para el bug B-2v2: fin de partida 2v2, race condition con 0x3232 antes del 0x4412, y verificación de premios para ambos ganadores y perdedores.

---

## [Auditoría nov-2026] — 2026-11-27 — rama `audit/noviembre-2026`

### Corregido

- **B-01** `servidor/partida.py` — `fin_jewel`: Validar que el remitente sea la llave, que la partida esté activa y que no haya ganador ya asignado antes de terminar una partida Jewel (0x4200).

- **B-02** `servidor/sala.py` — `volver_del_resultado`: Sólo resetear `sala.estado` a `ESPERA` cuando existe un ganador definido; ignorar 0x3232 durante partida activa.

- **B-03** `servidor/sala.py` — `elegir_movil`: Validar que los bytes de móvil estén en el conjunto válido (`_MOVILES_VALIDOS = set(range(16)) | {17, 18, AL_AZAR}`) antes de guardarlos.

- **B-04** `servidor/partida.py` — `armar_inicio`: Usar el índice del bucle (`i`) en lugar de `s.casilla` al calcular posiciones de salida, evitando colisiones cuando dos casillas difieren en `len(puntos)`.

- **B-05** `servidor/comandos.py` — `/movil`: Ampliar el rango aceptado de 0-13 a 0-15 (los móviles 14 y 15 existen en el cliente).

- **B-06** `servidor/sala.py` — `cambiar_mapa` y demás funciones de configuración: Añadir helper `_llave_en_espera()` que sólo devuelve la sala si `estado == ESPERA`, bloqueando cambios durante partidas activas.

- **B-07** `servidor/mundo.py` — `_conexion`: Añadir contador `_total_conexiones` para incluir conexiones pre-login en el límite `max_conexiones`.

- **B-08** `servidor/entrada.py` — `_lugar_libre`: Devolver `None` en lugar del fallback `254` cuando los 255 slots del canal están ocupados; `login` rechaza la entrada con `0x1012 NO_EXISTE`.

- **B-09** `servidor/cifrado.py` — `clave_dinamica`: Añadir slices `[:12]` y `[:4]` al construir el mensaje SHA-0, truncando silenciosamente los inputs que superen el tamaño del bloque.

- **B-10** `servidor/sala.py` — `crear`: Enviar `0x5101` con texto de error cuando `_id_libre` devuelve `None`, en lugar de retornar silenciosamente.

- **B-pase** `servidor/pase.py` — `_olvidar_vencidos`: La evicción dura del diccionario de JTIs sólo elimina entradas con `exp + TOLERANCIA_RELOJ < ahora`, evitando ventanas de replay.

### Añadido

- `pruebas/probar_audit.py` — 23 pruebas de regresión para los 11 bugs corregidos.
- `AUDIT_REPORT.md` — Informe de auditoría general.
- `BUG_TRACKER.md` — Descripción técnica de cada bug.
- `SECURITY_REPORT.md` — Análisis de seguridad.
- `PERFORMANCE_REPORT.md` — Análisis de rendimiento y estabilidad.
- `TEST_REPORT.md` — Informe de pruebas con tabla de cobertura.
- `CHANGELOG.md` — Este archivo.

### No modificado

- Protocolo de red (opcodes, formatos de paquete).
- Esquema de la base de datos.
- Mecánicas de juego (física, rangos, premios).
- Código del cliente.
- Configuración de producción.
