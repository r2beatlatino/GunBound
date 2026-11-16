# Lo que falta — en orden

> Al 16-nov-2026. Anda de punta a punta en esta PC: canje con pase → login → canal → chat → sala → partida de dos
> por el túnel → tienda (comprar, ponerse ropa) y todo guardado; en Docker Linux, prod y prueba.

1. **Cuenta Eñeños**: aplicar `integracion/cuenta_enenos_gunbound.patch` (los `aud` `gunbound` y `gunbound-prueba`).
   Sin eso el launcher de verdad no consigue pases para GunBound (hoy se prueba con pases firmados por la clave de
   prueba).
2. **El launcher**: una ficha para GunBound como la de EDA (`eda.rs`): canje → registro → exe. El contrato exacto
   está en `COMO_ENTRA_UN_JUGADOR.md`; la referencia que anda, `herramientas/jugar.py`.
3. **Repartir el cliente** por el servidor de parches (lista firmada), armado con `parchar_cliente.py`.
4. **El VPS de ensayo**: sumar GunBound como pieza del conjunto (compose del controlador + Caddy `/gunbound/*`).
5. **El premio**: al terminar la partida (0x4412) el server no acredita oro ni GP. Hay que medir qué manda el
   cliente en el resultado.
6. **Medir**: el paginado de salas (más de 9), el rechazo al entrar a una sala llena (hoy: aviso por chat),
   regalos, el UDP directo (la opción por omisión) entre casas distintas y detrás de un mismo router, y si el
   registro acepta un NOMBRE en `IP` (gethostbyname).
7. **Rangos y bandera** (ver `MAPA_DEL_CLIENTE.md`): calcular el rango del GP (19 = pollito al empezar), mandarlo
   en el 1.º y 3.º WORD de rango, el país en el 4.º (0 = «?»), y GP/oro en +61/+69 del 0x1012. De dónde sale el
   país (¿lo elige el jugador en el launcher?) lo decide Benja.
8. **Lo que el cliente pide y el server no atiende**: 0x4000 (la llave pide echar a un mudo → sacarlo + 0x3020/0x3400),
   0x3150 (`/kick` de la llave), echar con 0x1FFF y aviso de mantenimiento 0x1FFA para los GM, avisos con color.
9. **Parches al exe a pensar** (la red vieja): el vigilante de reloj 0x416C60 (cierra con «hack» si la PC se traba),
   el tope de reenvío P2P, los 30 s del vigilante de votos.
10. Ranking, gremios, amigos (Buddy, server aparte 0xA000..): no hay nada.
11. **Repo en GitHub** (`r2beatlatino/…`, main + develop) y el cron del de prueba: lo decide Benja.
