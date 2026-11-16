# -*- coding: utf-8 -*-
"""probar_basicos — el sobre de los mensajes, el cifrado y el pase, sin red."""
import json

from arnes import Banco, RAIZ  # noqa: F401
from servidor import cifrado, firma_ed25519 as ed, paquete, pase

b = Banco("probar_basicos")

# ── el sobre ─────────────────────────────────────────────────────────────────────────────────────────────
crudo = paquete.armar(0, 0x1001, b"\x01\x02\x03\x04")
b.igual(len(crudo), 10, "largo con cabecera")
b.igual(paquete.leer_cabecera(crudo), (10, paquete.secuencia(10), 0x1001), "cabecera")
# la secuencia depende de lo ya mandado: el mismo mensaje con otro acumulado lleva otra secuencia (control)
b.ver(paquete.armar(10, 0x1001, b"\x01\x02\x03\x04")[2:4] != crudo[2:4], "control: la secuencia cambia con lo enviado")
# el broker manda su primer mensaje con la secuencia fija 0xCBEB
b.igual(paquete.armar(0, 0x1312, b"\0\0", secuencia_fija=0xCBEB)[2:4], b"\xeb\xcb", "secuencia fija del broker")

c = paquete.Cortador()
dos = paquete.armar(0, 0x2000, b"ab") + paquete.armar(8, 0x2001, b"cde")
b.igual(len(c.meter(dos[:5])), 0, "medio mensaje no sale")
salieron = c.meter(dos[5:])
b.igual([x[4] | x[5] << 8 for x in salieron], [0x2000, 0x2001], "dos pegados salen los dos, en orden")
try:
    paquete.Cortador().meter(b"\x02\x00\x00\x00\x00\x00")
    b.ver(False, "control: un largo menor que la cabecera tiene que cortar")
except ValueError:
    b.ver(True, "")

# ── el cifrado ───────────────────────────────────────────────────────────────────────────────────────────
# el vector del emulador de jglim (MIT): un 0x3432 real del cliente, con su usuario, contraseña y ficha
vec = bytes.fromhex("32 42 48 43 9B 83 BD 5E 9E 87 9D 03 14 DD 01 7E 95 FF BE FA 7B 8A DD 4C C2 D5 12 E0 8C 60 33 E9 "
                    "DA C5 6B D5 11 DF 94 83 57 DD F6 2B 5A D4 85 41 A8 8F 44 4B D3 E4 25 A4 24 80 96 99 12 26 80 72 "
                    "65 06 01 7E 15 04 81 D6 F2 1C 94 66 71 E9 05 87 B0 D7 9B EE 30 C6 B5 97 B4 42 92 D0 4E 00 C0 D0")
clave = cifrado.clave_dinamica("saneusername", "sanepassword", bytes.fromhex("FFDC3080"))
datos, bien = cifrado.descifrar(vec[:96], clave, 0x3432)
b.ver(bien, "el 0x3432 real del emulador descifra con su control bien")
_, bien_mal = cifrado.descifrar(vec[:96], cifrado.clave_dinamica("saneusername", "OTRA", bytes.fromhex("FFDC3080")), 0x3432)
b.ver(not bien_mal, "control: con otra contraseña el control NO cierra")
_, bien_cmd = cifrado.descifrar(vec[:96], clave, 0x3433)
b.ver(not bien_cmd, "control: con otro comando el control NO cierra")
ida = cifrado.cifrar(b"hola mundo!!" * 2, clave, 0x2010)
b.igual(cifrado.descifrar(ida, clave, 0x2010), (b"hola mundo!!" * 2, True), "ida y vuelta")
# el argumento del exe: lo descifra la clave fija del cliente (lo mismo que hace GunBound.exe al arrancar)
arg = cifrado.argumento_cliente("90000001", "ABCdef123456")
plano = cifrado.descifrar_crudo(bytes.fromhex(arg), cifrado.CLAVE_ARGUMENTO)
b.igual(plano[:16].rstrip(b"\0"), b"90000001", "argumento: usuario")
b.igual(plano[16:32].rstrip(b"\0"), b"ABCdef123456", "argumento: contraseña")
b.igual(arg, arg.upper(), "argumento en hex MAYÚSCULA")

# ── el pase ──────────────────────────────────────────────────────────────────────────────────────────────
semilla = bytes(range(32))
pub = ed.publica(semilla)
v = pase.Verificador("gunbound", pub)
b.igual(v.comprobar(pase.firmar_pase(semilla, "gunbound", 10000570)), (10000570, None), "pase bueno")
p = pase.firmar_pase(semilla, "gunbound", 10000571)
v.comprobar(p)
b.igual(v.comprobar(p), (None, "pase ya usado"), "control: el mismo pase dos veces")
b.ver(v.comprobar(pase.firmar_pase(semilla, "gunbound-prueba", 1))[0] is None, "control: un pase del de PRUEBA no sirve en prod")
b.ver(pase.Verificador("gunbound-prueba", pub).comprobar(pase.firmar_pase(semilla, "gunbound", 1))[0] is None,
      "control: un pase de PROD no sirve en el de prueba")
b.igual(v.comprobar(pase.firmar_pase(semilla, "gunbound", 5, vida=-100))[1], "pase vencido", "control: vencido")
b.igual(v.comprobar(pase.firmar_pase(bytes(32), "gunbound", 5))[1], "firma inválida", "control: firmado por otra clave")
b.igual(v.comprobar(pase.firmar_pase(semilla, "gunbound", 5, iss="otro"))[1], "emisor desconocido", "control: otro emisor")
tocado = pase.firmar_pase(semilla, "gunbound", 7).split(".")
carga = json.loads(pase._de_b64u(tocado[1]))
carga["sub"] = "1"
tocado[1] = pase._b64u(json.dumps(carga).encode())
b.igual(v.comprobar(".".join(tocado))[1], "firma inválida", "control: cambiarle el Eñeños ID rompe la firma")
b.igual(pase.Verificador("gunbound", None).comprobar(p)[0], None, "control: sin clave nadie entra")
b.igual(pase.parsear_clave_publica(pub.hex()), pub, "clave en hex")
b.igual(pase.parsear_clave_publica(json.dumps({"keys": [{"x": pase._b64u(pub)}]})), pub, "clave en JWKS")
b.fin()
