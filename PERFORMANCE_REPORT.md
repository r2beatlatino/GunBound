# Informe de rendimiento y estabilidad — auditoría nov-2026

**Rama:** `audit/noviembre-2026`  **Fecha:** 2026-11-27

## Arquitectura de concurrencia

El servidor es **asyncio single-threaded**: todo el código de juego corre en un único event loop. Esto elimina la necesidad de locks para el estado compartido (salas, sesiones, boletos). No hay race conditions por diseño.

La base de datos (SQLite WAL, `isolation_level=None`) también corre en ese mismo hilo, con transacciones explícitas. No hay acceso concurrente a la DB.

## Hallazgos de rendimiento / estabilidad

### B-07 — Límite de conexiones no contaba pre-login
**Impacto en estabilidad:** Bajo-Medio.  
Un atacante podía abrir muchas conexiones TCP sin hacer login, superando `max_conexiones` y dejando sin espacio a jugadores legítimos. Con el fix, `_total_conexiones` cubre también las conexiones pre-login.

### JTI store (pase.py) — Crecimiento ilimitado bajo ataque
**Impacto en estabilidad:** Medio (sólo bajo ataque de denegación de servicio).  
El diccionario `_usados` crece hasta MAX_RECORDADOS (50 000). El fix B-pase asegura que la evicción borra sólo entradas expiradas, pero si un atacante envía 50 000 pases válidos que aún no expiraron, el dict llega al tope y el sistema deja de aceptar nuevos JTIs (todos los logins se rechazan con "pase ya usado").

**Recomendación:** Considerar un tope por IP en el endpoint `/canje` para limitar este vector.

### Sala ID veda (sala.py)
El mecanismo de veda de IDs de sala (5 minutos) usa `salas_cerradas` con tiempos `time.monotonic()`. Si se crean y destruyen salas muy rápido, `salas_cerradas` puede crecer hasta 255 entradas. No hay leak: las entradas se limpian cuando el ID vuelve a estar disponible (en `_id_libre`). ✅

## Medidas del banco

| Prueba | Tiempo (referencia) |
|--------|-------------------|
| `correr_todas.py` completo (386 pruebas) | ~44 s |
| `probar_sala.py` (túnel P2P) | ~8 s |
| `probar_fin.py` (ciclos de partida completa) | ~12 s |
| `probar_panel.py` (82 aserciones) | ~6 s |

Los tiempos incluyen arrancar/detener un servidor real en cada bloque `with ServerDePrueba(...)`. No son benchmarks de carga.

## Aspectos no medidos en esta auditoría

- Throughput bajo carga alta (> 50 partidas simultáneas).
- Latencia del túnel P2P bajo tráfico UDP real.
- Consumo de memoria con muchas conexiones abiertas.
- Comportamiento del SQLite WAL bajo escrituras intensivas (premios de partida).

Estos aspectos se miden mejor con la **mesa de prueba** (`herramientas/mesa.py`) con clientes reales del juego.
