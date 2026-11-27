# Informe de seguridad — auditoría nov-2026

**Rama:** `audit/noviembre-2026`  **Fecha:** 2026-11-27

## Resumen

Se auditaron todos los puntos de entrada de red y los mecanismos de autenticación. Se encontraron y corrigieron **2 issues de seguridad** (B-01 y B-pase). Los demás bugs tienen impacto de seguridad menor o nulo.

## Superficie de ataque

```
Internet → broker TCP (lista de mundos, sin auth)
         → mundo TCP (login con boleto, luego opcodes del juego)
         → web HTTP (canje de pase EdDSA por boleto)
```

El cliente nunca habla directamente con Cuenta Eñeños durante el juego; la clave pública de EdDSA se carga una vez al arrancar.

## Autenticación y autorización

### Pase EdDSA (Cuenta Eñeños)
- **Algoritmo verificado:** EdDSA / Ed25519 con clave pública en memoria.
- **Campos validados:** `alg`, `iss`, `aud`, `exp`, `iat`, `jti`, `sub`.
- **Anti-replay:** JTIs registrados hasta `exp + 30 s`. ✅ Fix B-pase corrigió la evicción prematura.
- **Separación prod/prueba:** `aud = "gunbound"` vs `"gunbound-prueba"`. Un pase de uno no sirve en el otro. ✅

### Login (0x1010)
- El boleto se valida en memoria (no en base de datos), de vida corta.
- La clave dinámica AES depende de usuario + boleto + ficha aleatoria por conexión.
- Una cuenta sólo puede estar adentro una vez (el server desconecta la sesión anterior). ✅

## Validaciones de servidor vs. cliente

| Acción | Validado en server |
|--------|-------------------|
| Terminar partida Jewel (0x4200) | ✅ B-01: sólo la llave, sólo durante JUGANDO |
| Elegir móvil (0x3200) | ✅ B-03: sólo valores 0-15, 17, 18 |
| Cambiar sala durante partida | ✅ B-06: sólo en ESPERA |
| Matar jugador (0x4100) | El server valida que la casilla exista y no esté ya muerta |
| Reaparecer (0x4104) | El server valida modo Score/Jewel y vidas restantes |
| Tunnel P2P (0x4500) | El server filtra por casilla; no llega a la propia casilla del remitente |

## Issues corregidos

### B-01 — Fin de Jewel sin autorización (Alta)
Cualquier jugador podía terminar una partida Jewel enviando 0x4200. Corregido: se valida que el remitente sea la llave, que la partida esté activa y que no haya ganador ya asignado.

**Impacto potencial antes del fix:** Un jugador perdiendo podía terminar la partida abruptamente o repetidamente, corrompiendo el estado del juego.

### B-pase — Evicción prematura de JTIs (Media)
En escenarios de alta carga (> 25 000 logins sin expiración), la evicción podía borrar JTIs vigentes, abriendo una ventana de replay de pases.

**Impacto potencial antes del fix:** Bajo (requiere > 25 000 logins sin que los JTIs expiren), pero la ventana de replay es inaceptable en un sistema de autenticación.

## Anti-cheat (observaciones)

La partida corre en cliente (arquitectura P2P): el server no simula física ni balas. El anti-cheat disponible es:

- **El server decide quién gana** en Solo, Score y Tag (conteo de muertes). ✅
- **El cliente host decide en Jewel** (0x4200), con validación de remitente añadida en B-01. ✅
- El server **no valida** posiciones, daño ni trayectorias (no tiene el motor de física). Esta es una limitación arquitectónica de GunBound, no un bug.

## Criptografía

| Uso | Algoritmo | Clave | Notas |
|-----|-----------|-------|-------|
| Login (usuario) | AES-128 ECB | Estática (`FFB3...`) | Sólo cifra el primer bloque; la clave es conocida, el objetivo es ofuscación |
| Login + juego | AES-128 ECB | Dinámica (SHA-0 de usuario+boleto+ficha) | La ficha es aleatoria por conexión; sin la ficha no se puede derivar la clave |
| Pase externo | EdDSA Ed25519 | Pública de Cuenta Eñeños | Verificación correcta; clave no hardcoded (llega por env/HTTP al arrancar) |

**SHA-0 vs SHA-1:** El servidor usa SHA-0 deliberadamente (sin rotación en `w[i]`), tal como el cliente Legacy. No es un error; es compatibilidad de protocolo.

**AES-ECB:** Modo ECB (sin IV, sin encadenamiento de bloques). Es la elección original del protocolo GunBound Legacy; no se puede cambiar sin romper la compatibilidad con el cliente.

## Recomendaciones (fuera del alcance de esta auditoría)

- Considerar rate-limiting en el endpoint `/canje` (HTTP) para limitar ataques de fuerza bruta a boletos.
- Considerar un tiempo de vida de boleto más corto (actualmente `boleto_horas` configurable).
- El modo ECB para AES no ofrece confidencialidad fuerte; pero cambiar el cifrado requiere modificar el cliente binario.
