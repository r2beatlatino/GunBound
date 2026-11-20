# GunBound — server para Eñeños

> Parte de **Eñeños** · coordinado por [`r2beatlatino/coordinador`](https://github.com/r2beatlatino/coordinador) (las cuentas, el panel y el catálogo de juegos).
> El arte y el cliente de GunBound son de Softnyx y **no** están en este repo.

Server de GunBound (cliente Legacy v179) en Python, para correr en Linux con Docker, con la entrada por el pase de
Cuenta Eñeños (como EDA y R2Beat). Dos servers por juego: prod (`main`) y prueba (`develop`).

- Empezar: [`CLAUDE.md`](CLAUDE.md)
- Desplegar: [`despliegue/LEEME.md`](despliegue/LEEME.md)
- El protocolo medido: [`documentacion/PROTOCOLO_LEGACY.md`](documentacion/PROTOCOLO_LEGACY.md)

```bash
pip install pycryptodome
python pruebas/correr_todas.py
python -m servidor            # con las variables GB_* (despliegue/ejemplo.env)
```
