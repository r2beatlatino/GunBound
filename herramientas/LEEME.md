# Herramientas (Windows, de escritorio)

| herramienta | para qué |
|---|---|
| `parchar_cliente.py` | arma el cliente de Eñeños desde `C:\GunBound-Legacy` (5 parches medidos) · `--comprobar` |
| `laboratorio.py` | el server en esta PC con una clave de PRUEBA (`estado/clave_prueba.json`) |
| `jugar.py` | el launcher de mesa: pase (de prueba o de verdad) → canje → registro → GunBound.exe · `--veces N` |
| `mesa.py` + `mesa_agente.js` | varios clientes manejados por API sin tocar la PC (ver documentacion/PROBAR_CON_EL_JUEGO.md) |
| `exportar_para_launcher.py` | íconos de rango (PNG), países y rangos en JSON para la pantalla de personajes del launcher |
| `lista_del_cliente.py` | la lista de archivos del cliente (formato de la de EDA) para que el launcher lo baje; sin firmar |
| `mezclar_img.py` | un `.img` del Legacy con un cuadro del original (el fondo del lobby y la sala sin la marca Legacy) |
| `ventanas.py` | listar y fotografiar las ventanas del juego (PrintWindow) |

Necesitan: `pip install pycryptodome pillow frida pefile`.
