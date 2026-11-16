// mesa_agente.js — va DENTRO de cada GunBound.exe (Frida). Le da al juego clics y teclas de mentira por DirectInput,
// sin tocar el mouse ni el teclado de la PC. Lo carga herramientas/mesa.py.
//
// El juego lee la POSICIÓN del mouse por los mensajes de la ventana (WM_MOUSEMOVE: eso lo manda mesa.py), pero los
// BOTONES y el teclado por DirectInput8 (dinput8.dll, cargada a mano). Acá se engancha el objeto que crea
// DirectInput8Create → su CreateDevice → los métodos del dispositivo (la tabla virtual):
//   7 Acquire · 9 GetDeviceState · 10 GetDeviceData · 13 SetCooperativeLevel
// y se fuerza «adquirido» aunque la ventana no tenga el foco.
'use strict';

const estado = { boton: 0, teclas: new Set(), cola: { raton: [], teclado: [] }, tipo: {}, log: [], dispositivos: {}, enganchado: false, secuencia: 1 };
estado.cuenta = {};
function contar(k) { estado.cuenta[k] = (estado.cuenta[k] || 0) + 1; }
function anotar(t) { estado.log.push(t); if (estado.log.length > 300) estado.log.shift(); }

const DIMOFS_BUTTON0 = 12;

function engancharDispositivo(disp, tipo) {
  estado.tipo[disp.toString()] = tipo;
  const vt = disp.readPointer();
  const clave = vt.toString();
  anotar('CreateDevice ' + tipo + ' ' + disp);
  if (estado.dispositivos[clave]) return;
  estado.dispositivos[clave] = true;
  const ps = Process.pointerSize;
  Interceptor.attach(vt.add(7 * ps).readPointer(), {           // Acquire: siempre bien
    onLeave(r) { r.replace(ptr(0)); }
  });
  Interceptor.attach(vt.add(13 * ps).readPointer(), {          // SetCooperativeLevel: anotar las banderas
    onEnter(a) { anotar('SetCooperativeLevel flags=0x' + a[2].toUInt32().toString(16)); }
  });
  Interceptor.attach(vt.add(9 * ps).readPointer(), {           // GetDeviceState(this, cb, datos)
    onEnter(a) { this.cb = a[1].toUInt32(); this.datos = a[2]; this.yo = estado.tipo[a[0].toString()]; },
    onLeave(r) {
      contar('state ' + this.yo + ' cb=' + this.cb + ' rc=0x' + (r.toUInt32() >>> 0).toString(16));
      if (this.cb === 16 || this.cb === 20) {                  // DIMOUSESTATE(2): x y z + botones
        if (r.toInt32() !== 0) { this.datos.writeByteArray(new Array(this.cb).fill(0)); }
        else { this.datos.writeU32(0); this.datos.add(4).writeU32(0); }   // el movimiento relativo no se usa: lo da la ventana
        this.datos.add(12).writeU8(estado.boton ? 0x80 : 0);
        r.replace(ptr(0));
      } else if (this.cb === 256) {                             // teclado
        if (r.toInt32() !== 0) this.datos.writeByteArray(new Array(256).fill(0));
        for (const k of estado.teclas) this.datos.add(k).writeU8(0x80);
        r.replace(ptr(0));
      }
    }
  });
  Interceptor.attach(vt.add(10 * ps).readPointer(), {          // GetDeviceData(this, cbObj, rgdod, pdwInOut, flags)
    onEnter(a) { this.yo = estado.tipo[a[0].toString()]; this.cbObj = a[1].toUInt32(); this.rg = a[2]; this.pn = a[3]; this.cap = a[3].isNull() ? 0 : a[3].readU32(); },
    onLeave(r) {
      contar('data ' + this.yo + ' cap=' + this.cap + ' rc=0x' + (r.toUInt32() >>> 0).toString(16));
      if (this.pn.isNull()) return;
      let n = r.toInt32() === 0 ? this.pn.readU32() : 0;
      if (r.toInt32() !== 0) r.replace(ptr(0));
      const cola = estado.cola[this.yo] || [];
      while (cola.length && n < this.cap && !this.rg.isNull()) {
        const ev = cola.shift();
        const p = this.rg.add(n * this.cbObj);
        p.writeU32(ev.ofs); p.add(4).writeU32(ev.dato); p.add(8).writeU32(Date.now() & 0xffffffff); p.add(12).writeU32(estado.secuencia++);
        if (this.cbObj >= 20) p.add(16).writeU32(0);
        n++;
      }
      this.pn.writeU32(n);
    }
  });
  anotar('dispositivo ' + tipo + ' enganchado vt=' + clave);
}

function engancharDI(mod) {
  if (estado.enganchado) return;
  estado.enganchado = true;
  Interceptor.attach(mod.getExportByName('DirectInput8Create'), {
    onEnter(a) { this.pp = a[3]; },
    onLeave(r) {
      if (r.toInt32() !== 0) return;
      const di = this.pp.readPointer();
      const vt = di.readPointer();
      Interceptor.attach(vt.add(3 * Process.pointerSize).readPointer(), {   // CreateDevice(this, guid, ppDev, outer)
        onEnter(a) { this.pd = a[2]; this.g = a[1].readU32(); },
        onLeave(r2) { if (r2.toInt32() === 0) engancharDispositivo(this.pd.readPointer(), this.g === 0x6F1D2B60 ? 'raton' : (this.g === 0x6F1D2B61 ? 'teclado' : 'otro')); }
      });
      anotar('DirectInput8Create enganchado');
    }
  });
}

// GetKeyState / GetAsyncKeyState: el botón izquierdo (VK_LBUTTON = 1) y las teclas que pida
const u32 = Process.getModuleByName('user32.dll');
for (const f of ['GetKeyState', 'GetAsyncKeyState']) {
  Interceptor.attach(u32.getExportByName(f), {
    onEnter(a) { this.vk = a[0].toUInt32() & 0xff; },
    onLeave(r) {
      contar(f + ' vk=' + this.vk);
      if (this.vk === 1 && estado.boton) r.replace(ptr(0xffff8001 >>> 0));
    }
  });
}
// El juego sólo atiende el mouse si cree que su ventana es la de ADELANTE: se le dice que sí (mesa.py le pasa su
// ventana con `ventana(hwnd)`). Y ⛔ nunca mueve el cursor de verdad: SetCursorPos no hace nada.
estado.hwnd = null;
for (const f of ['GetForegroundWindow', 'GetActiveWindow', 'GetFocus']) {
  Interceptor.attach(u32.getExportByName(f), { onLeave(r) { contar(f); if (estado.hwnd) r.replace(estado.hwnd); } });
}
Interceptor.replace(u32.getExportByName('SetCursorPos'), new NativeCallback(function (x, y) { contar('SetCursorPos'); return 1; }, 'int', ['int', 'int'], 'stdcall'));

const ya = Process.findModuleByName('dinput8.dll');
if (ya) engancharDI(ya);
else {
  const ll = Process.getModuleByName('kernel32.dll').getExportByName('LoadLibraryA');
  Interceptor.attach(ll, { onLeave() { const m = Process.findModuleByName('dinput8.dll'); if (m) engancharDI(m); } });
}

rpc.exports = {
  boton(abajo) {                                  // mantener / soltar el botón izquierdo
    estado.boton = abajo ? 1 : 0;
    estado.cola.raton.push({ ofs: DIMOFS_BUTTON0, dato: abajo ? 0x80 : 0 });
  },
  tecla(codigo, abajo) {                          // código DIK_*
    if (abajo) estado.teclas.add(codigo); else estado.teclas.delete(codigo);
    estado.cola.teclado.push({ ofs: codigo, dato: abajo ? 0x80 : 0 });
  },
  cuenta() { return estado.cuenta; },
  ventana(h) {
    estado.hwnd = ptr(h);
    if (!estado.wp) {
      const gwl = new NativeFunction(u32.getExportByName('GetWindowLongA'), 'pointer', ['pointer', 'int'], 'stdcall');
      estado.wp = gwl(estado.hwnd, -4);
      anotar('WndProc ' + estado.wp);
      Interceptor.attach(estado.wp, { onEnter(a) { const m = a[1].toUInt32(); if (m >= 0x200 && m <= 0x20e || m === 0x1c || m === 6 || m === 7 || m === 8) contar('msg 0x' + m.toString(16)); } });
    }
  },
  log() { const l = estado.log.slice(); estado.log.length = 0; return l; },
};
