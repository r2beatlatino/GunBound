# Probar con el juego de verdad — la mesa

Varios clientes en VENTANA, manejados por API, **sin tocar el mouse ni el teclado de la PC** (el cursor de verdad
no se mueve: los clics van como mensajes a cada ventana y por DirectInput de mentira con Frida).

```bash
python herramientas/laboratorio.py                 # el server en esta PC (o los contenedores: despliegue/LEEME.md)
python herramientas/mesa.py                        # la mesa, en http://127.0.0.1:8399 (otra terminal)
python herramientas/mesa.py abrir 90000001         # un cliente (pase de PRUEBA → canje → registro → exe)
python herramientas/mesa.py abrir 90000003 gunbound-prueba http://IP:9371/canje     # contra el de prueba
python herramientas/mesa.py lista
python herramientas/mesa.py foto 1                 # estado/fotos/mesa_1.png (PrintWindow: aunque esté tapada)
python herramientas/mesa.py clic 1 300 110         # coordenadas de la foto
python herramientas/mesa.py doble 1 300 110
python herramientas/mesa.py decir 1 "hola" 1       # escribe en la caja de texto activa y aprieta Enter
python herramientas/mesa.py tecla 1 espacio 1.2    # mantener (disparar con fuerza)
python herramientas/mesa.py cerrar
```

⚠ Cerrar la mesa cierra los juegos que abrió (Frida). ⚠ Los juegos se abren en la pantalla de la PC.

## Coordenadas útiles (ventana 1600×1032)

| pantalla | qué | dónde |
|---|---|---|
| servidores | el mundo (clic, después doble clic) | 300, 110 |
| lobby | Create · All (actualizar salas) · la 1.ª sala (clic + doble) | 1340, 470 · 848, 450 · 300, 95 |
| crear sala | 1:1 · Solo · Jewel · confirmar (el título: `texto … 1`) | 585, 443 · 880, 450 · 1030, 500 · 1015, 655 |
| sala | Start / Ready | 1515, 985 |

## Lo que se aprendió armando la partida de a dos

- El invitado queda «Ready» con los clics de entrar; otro clic en Ready lo APAGA.
- Con el cliente parchado (6 y 7) el túnel se arma a los 2 s de entrar a la sala y el «Start» anda enseguida.
  (Con el original eran 20 s, y si nadie empezaba en los ~30 s siguientes el invitado se iba.)
- Dos clientes en la misma PC no pueden hablarse por UDP directo (los dos quieren el 8363): por eso el server de
  laboratorio corre con `GB_P2P=tunel`.

## Los guiones (estado/, gitignorado)

`estado/partida.sh` deja una partida 1:1 andando contra el server de laboratorio; con `GB_DOCKER=prod` y
`GB_CANJE=http://<IP del WSL>:8371/canje`, contra el contenedor. `estado/fotos.sh 1 2` junta las fotos.
