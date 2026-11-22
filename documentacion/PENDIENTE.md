# Lo que falta — en orden

> Al 16-nov-2026. Anda de punta a punta en esta PC: canje con pase → login → canal → chat → sala → partida de dos
> por el túnel → tienda (comprar, ponerse ropa) y todo guardado; en Docker Linux, prod y prueba.

1. **Cuenta Eñeños**: aplicar `integracion/cuenta_enenos_gunbound.patch` (los `aud` `gunbound` y `gunbound-prueba`).
   Sin eso el launcher de verdad no consigue pases para GunBound (hoy se prueba con pases firmados por la clave de
   prueba).
2. **El launcher**: la ficha de GunBound (carta, instalar, pantalla de personajes, jugar). ✅ 16-nov la guía para la
   sesión del launcher está lista: `PARA_EL_LAUNCHER.md` (con `/paises`, íconos de rango y la lista del cliente).
3. **Repartir el cliente** por el servidor de parches (lista firmada), armado con `parchar_cliente.py`.
4. **El VPS de ensayo**: sumar GunBound como pieza del conjunto (compose del controlador + Caddy `/gunbound/*`).
5. ✅ **El premio** (16-nov): el cliente calcula y la llave manda 0x4412; el server acredita una vez con los topes
   del Serv3 (`partida.py`, `investigacion/PAGOS_GP_Y_ORO.md`). Falta medirlo con una partida jugada hasta el final.
6. **Medir**: el paginado de salas (más de 9), el rechazo al entrar a una sala llena (hoy: aviso por chat),
   regalos, el UDP directo (la opción por omisión) entre casas distintas y detrás de un mismo router, y si el
   registro acepta un NOMBRE en `IP` (gethostbyname).
7. ✅ **Rangos y bandera** (16-nov, medido con el juego): falta que la partida SUME GP (el 0x4412, punto 5), elegir
   entre GP fijo o por puesto para los rangos altos, y crear personajes desde el launcher (`CREAR_PERSONAJE.md`).
8. **Lo que el cliente pide y el server no atiende**: 0x4000 (la llave pide echar a un mudo → sacarlo + 0x3020/0x3400),
   0x3150 (`/kick` de la llave), echar con 0x1FFF y aviso de mantenimiento 0x1FFA para los GM, avisos con color.
9. **Parches al exe a pensar** (la red vieja): el vigilante de reloj 0x416C60 (cierra con «hack» si la PC se traba),
   el tope de reenvío P2P, los 30 s del vigilante de votos.
10. Ranking, gremios, amigos (Buddy, server aparte 0xA000..): no hay nada.
11. ✅ 19-nov: el arte original de Softnyx salió del repo (y de su historial) a `D:\Gunbound\arte_original`
    (`GB_ARTE_ORIGINAL`), para publicar el repo.
12. **Repo en GitHub** (`r2beatlatino/…`, main + develop) y el cron del de prueba: lo decide Eñeños.
