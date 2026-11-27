# CHANGELOG

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
