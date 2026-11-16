#!/usr/bin/env python3
"""avatar_xfs — el avatar.xfs del cliente (la ropa y sus precios) y la tienda SÓLO ORO.

Lo escribió Codex el 16-nov (encargo y su informe: documentacion/investigacion/TIENDA_AVATAR_XFS.md). Benja: «el
cash queda como placeholder; todo se compra con oro». `parchar_cliente.py` llama a `solo_oro()` al armar el
cliente; el server cobra con `servidor/datos/precios_avatar.json`, que sale de la misma conversión.

GunBound Legacy v179: convierte las 861 piezas permanentes del JSON a oro.

Python 3.10+, biblioteca estandar. No abre ni modifica el cliente instalado.
Uso: python oro_solo.py          (genera y verifica)
     python oro_solo.py --verificar  (solo vuelve a leer y verificar)
Los archivos se resuelven respecto de este script, no del directorio de trabajo.
En esas 861 piezas fija permiso oro=1 y permiso cash=0. Los alquileres,
paquetes, demas campos y piezas ajenas al JSON se conservan.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import zlib

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / "avatar_original.xfs"
REFERENCE = BASE / "precios_avatar.json"
OUTPUT = BASE / "avatar_oro.xfs"
JSON_OUTPUT = BASE / "precios_avatar_oro.json"
CHECK_OUTPUT = BASE / "verificacion.json"
INDIVIDUAL = {"fb.dat", "fg.dat", "fh.dat", "mb.dat", "mf.dat", "mg.dat", "mh.dat"}
RECORD_SIZE = 644
GOLD, CASH = 0x58, 0x5C
GOLD_PERMISSION, CASH_PERMISSION = 0x60, 0x61


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def u32(data: bytes, offset: int = 0) -> int:
    require(0 <= offset <= len(data) - 4, f"uint32 fuera de rango: {offset}")
    return struct.unpack_from("<I", data, offset)[0]


def put32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value)


def inflate(data: bytes, size: int) -> bytes:
    dec = zlib.decompressobj()
    raw = dec.decompress(data, size + 1)
    require(dec.eof and not dec.unused_data and not dec.unconsumed_tail,
            "Stream zlib incompleto, excedido o con bytes sobrantes")
    require(len(raw) == size, f"Longitud zlib: {len(raw)}, esperada {size}")
    return raw


@dataclass
class Block:
    raw: bytes
    stored: bytes
    raw_offset: int


@dataclass
class Entry:
    name: str
    directory_record: bytes
    offset: int
    size: int
    stored_size: int
    raw: bytes
    blocks: list[Block]


@dataclass
class Snapshot:
    offset: int
    end: int
    header: bytes
    directory: bytes


@dataclass
class Archive:
    data: bytes
    entries: list[Entry]
    snapshots: list[Snapshot]
    active: int


def read_snapshot(data: bytes, offset: int) -> Snapshot:
    require(4 <= offset < len(data), "Puntero de indice fuera del archivo")
    n = data[offset]
    pos = offset + 1
    header = inflate(data[pos:pos + n], 64)
    require(header[:4] == b"FOX7", "Firma de indice distinta de FOX7")
    require(u32(header, 20) == 65536, "Tamano de bloque no soportado")
    require(u32(header, 16) == offset, "Autopuntero del indice incorrecto")
    pos += n
    require(pos + 3 <= len(data), "Indice truncado")
    n = int.from_bytes(data[pos:pos + 3], "little")
    pos += 3
    require(0 < u32(header, 8) < 10000, "Cantidad de entradas invalida")
    directory = inflate(data[pos:pos + n], u32(header, 8) * 128)
    return Snapshot(offset, pos + n, header, directory)


def read_blocks(data: bytes, offset: int, stored_size: int, size: int) -> tuple[bytes, list[Block]]:
    pos, end = offset, offset + stored_size
    require(4 <= pos <= end <= len(data), "Entrada fuera del archivo")
    blocks: list[Block] = []
    raw_offset = 0
    while pos < end:
        start = pos
        require(pos + 5 <= end, "Cabecera de bloque truncada")
        token = int.from_bytes(data[pos:pos + 3], "little")
        pos += 3
        require(token & ~0xCFFFFF == 0, "Bits de bloque no soportados")
        short, plain = bool(token & 0x800000), bool(token & 0x400000)
        raw_size = (token & 0xFFFFF) if short else 65536
        require(0 < raw_size <= 65536, "Longitud descomprimida invalida")
        if short and not plain:
            require(pos + 5 <= end, "Cabecera de compresion truncada")
            packed = int.from_bytes(data[pos:pos + 3], "little")
            require(packed < 0x100000, "Longitud comprimida invalida")
            pos += 3
        else:
            packed = raw_size if plain else token & 0xFFFFF
        checksum = int.from_bytes(data[pos:pos + 2], "little")
        require(checksum == 0, "Este lector requiere checksum opcional de bloque igual a cero")
        pos += 2
        require(pos + packed <= end, "Datos de bloque truncados")
        payload = data[pos:pos + packed]
        raw = payload if plain else inflate(payload, raw_size)
        pos += packed
        blocks.append(Block(raw, data[start:pos], raw_offset))
        raw_offset += len(raw)
    require(pos == end and raw_offset == size, "Longitud de entrada incorrecta")
    return b"".join(block.raw for block in blocks), blocks


def read_xfs(data: bytes) -> Archive:
    require(len(data) >= 4, "XFS truncado")
    active = u32(data)
    current = read_snapshot(data, active)
    entries: list[Entry] = []
    for pos in range(0, len(current.directory), 128):
        rec = current.directory[pos:pos + 128]
        name = rec[:112].split(b"\0", 1)[0].decode("ascii")
        require(u32(rec, 116) == 1, f"Modo de entrada no soportado: {name}")
        offset, size, stored_size = u32(rec, 112), u32(rec, 120), u32(rec, 124)
        raw, blocks = read_blocks(data, offset, stored_size, size)
        entries.append(Entry(name, rec, offset, size, stored_size, raw, blocks))
    require(len({e.name for e in entries}) == len(entries), "Nombres de entrada repetidos")
    cursor = 4
    for entry in sorted(entries, key=lambda e: e.offset):
        require(entry.offset == cursor, "Hueco o superposicion entre entradas")
        cursor += entry.stored_size
    snapshots: list[Snapshot] = []
    while cursor < len(data):
        snap = read_snapshot(data, cursor)
        require(snap.directory == current.directory, "Indices historicos con entradas distintas")
        snapshots.append(snap)
        cursor = snap.end
    require(cursor == len(data) and snapshots and snapshots[-1].offset == active,
            "Cola XFS o indice activo inesperados")
    return Archive(data, entries, snapshots, active)


def records(archive: Archive):
    for entry in archive.entries:
        if entry.name not in INDIVIDUAL:
            continue
        count = u32(entry.raw)
        require(entry.size == 4 + RECORD_SIZE * count, f"Registros invalidos en {entry.name}")
        for index in range(count):
            pos = 4 + RECORD_SIZE * index
            record = entry.raw[pos:pos + RECORD_SIZE]
            yield entry, pos, record[:4].hex(), record


def extract_prices(archive: Archive, ids: set[str] | None = None) -> dict[str, list[int]]:
    """Sin ids: permanentes habilitados (byte +0x54) con algun importe."""
    result: dict[str, list[int]] = {}
    seen: set[str] = set()
    for _, _, key, rec in records(archive):
        require(key not in seen, f"ID de pieza repetido: {key}")
        seen.add(key)
        price = [u32(rec, GOLD), u32(rec, CASH)]
        selected = key in ids if ids is not None else bool(rec[0x54] and any(price))
        if selected:
            result[key] = price
    if ids is not None:
        require(result.keys() == ids, "Faltan IDs solicitados")
    return dict(sorted(result.items()))


def target_prices(prices: dict[str, list[int]]) -> dict[str, list[int]]:
    return {key: [gold if gold else cash * 10, 0] for key, (gold, cash) in prices.items()}


def encode_block(raw: bytes) -> bytes:
    packed = zlib.compress(raw, 9)
    short = len(raw) < 65536
    if len(packed) >= len(raw) - (3 if short else 0):
        token = (0x800000 if short else 0) | 0x400000 | len(raw)
        return token.to_bytes(3, "little") + b"\0\0" + raw
    prefix = ((0x800000 | len(raw)).to_bytes(3, "little") if short else b"")
    return prefix + len(packed).to_bytes(3, "little") + b"\0\0" + packed


def convert(archive: Archive, prices: dict[str, list[int]]) -> bytes:
    wanted = target_prices(prices)
    modified = {e.name: bytearray(e.raw) for e in archive.entries}
    for entry, pos, key, _ in records(archive):
        if key in wanted:
            struct.pack_into("<II", modified[entry.name], pos + GOLD, *wanted[key])
            modified[entry.name][pos + GOLD_PERMISSION] = 1
            modified[entry.name][pos + CASH_PERMISSION] = 0
    result = bytearray(4)
    directory = bytearray(archive.snapshots[-1].directory)
    new_locations: dict[str, tuple[int, int]] = {}
    for entry in sorted(archive.entries, key=lambda e: e.offset):
        start = len(result)
        raw = modified[entry.name]
        for block in entry.blocks:
            fragment = bytes(raw[block.raw_offset:block.raw_offset + len(block.raw)])
            # Conserva literalmente los bloques que no contienen cambios.
            result.extend(block.stored if fragment == block.raw else encode_block(fragment))
        new_locations[entry.name] = (start, len(result) - start)
    for index, entry in enumerate(archive.entries):
        offset, size = new_locations[entry.name]
        put32(directory, index * 128 + 112, offset)
        put32(directory, index * 128 + 124, size)
    for snap in archive.snapshots:
        start = len(result)
        header = bytearray(snap.header)
        put32(header, 16, start)
        compressed_header = zlib.compress(bytes(header), 9)
        compressed_directory = zlib.compress(bytes(directory), 9)
        require(len(compressed_header) < 256, "Cabecera comprimida demasiado grande")
        result.extend(bytes([len(compressed_header)]) + compressed_header)
        result.extend(len(compressed_directory).to_bytes(3, "little") + compressed_directory)
        if snap.offset == archive.active:
            put32(result, 0, start)
    return bytes(result)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(before: Archive, after: Archive, reference: dict[str, list[int]]) -> dict:
    old = extract_prices(before)
    require(len(old) == 861 and old == reference, "El original no coincide con las 861 piezas del JSON")
    wanted = target_prices(old)
    require(extract_prices(after) == wanted, "Los precios de salida no son los pedidos")
    permissions = {}
    for _, _, key, rec in records(after):
        if key in wanted:
            pair = (rec[GOLD_PERMISSION], rec[CASH_PERMISSION])
            require(pair == (1, 0), f"Permisos de moneda incorrectos en {key}: {pair}")
            permissions[key] = pair
    require(len(permissions) == 861, "No se verificaron los permisos de las 861 piezas")
    require(len(before.entries) == len(after.entries), "Cambio en cantidad de archivos internos")
    require(len(before.snapshots) == len(after.snapshots), "Cambio en cantidad de indices")
    changed_bytes = 0
    price_bytes = 0
    permission_bytes = 0
    by_file: dict[str, int] = {}
    for first, second in zip(before.entries, after.entries):
        require(first.name == second.name and first.size == second.size, "Cambio de archivo/tamano logico")
        original_meta, output_meta = bytearray(first.directory_record), bytearray(second.directory_record)
        for offset in (112, 124):
            original_meta[offset:offset + 4] = output_meta[offset:offset + 4] = b"\0" * 4
        require(original_meta == output_meta, f"Metadatos alterados: {first.name}")
        expected = bytearray(first.raw)
        modified_count = 0
        if first.name in INDIVIDUAL:
            for pos in range(4, len(expected), RECORD_SIZE):
                key = expected[pos:pos + 4].hex()
                if key in wanted:
                    struct.pack_into("<II", expected, pos + GOLD, *wanted[key])
                    expected[pos + GOLD_PERMISSION] = 1
                    expected[pos + CASH_PERMISSION] = 0
                    price_bytes += sum(a != b for a, b in zip(
                        first.raw[pos + GOLD:pos + CASH + 4], expected[pos + GOLD:pos + CASH + 4]))
                    permission_bytes += sum(a != b for a, b in zip(
                        first.raw[pos + GOLD_PERMISSION:pos + CASH_PERMISSION + 1],
                        expected[pos + GOLD_PERMISSION:pos + CASH_PERMISSION + 1]))
                    modified_count += 1
        require(bytes(expected) == second.raw,
                f"Cambio fuera de precios y permisos autorizados: {first.name}")
        changed_bytes += sum(a != b for a, b in zip(first.raw, second.raw))
        by_file[first.name] = modified_count
        # Cada bloque sin diferencias debe seguir almacenado literalmente igual.
        require(len(first.blocks) == len(second.blocks), "Cambio en cantidad de bloques")
        for a, b in zip(first.blocks, second.blocks):
            require(a.raw_offset == b.raw_offset and len(a.raw) == len(b.raw), "Cambio de limites de bloque")
            if a.raw == b.raw:
                require(a.stored == b.stored, "Bloque sin cambios recomprimido")
    for a, b in zip(before.snapshots, after.snapshots):
        h1, h2 = bytearray(a.header), bytearray(b.header)
        h1[16:20] = h2[16:20] = b"\0" * 4
        require(h1 == h2, "Cambio de cabecera ajeno al autopuntero")
    return {
        "resultado": "OK", "piezas_verificadas": len(old),
        "oro_preservado": sum(gold > 0 for gold, _ in old.values()),
        "cash_cero": sum(cash == 0 for _, cash in extract_prices(after).values()),
        "conversiones_solo_cash": {k: {"antes": old[k], "despues": wanted[k]}
                                  for k in old if old[k][0] == 0},
        "archivos_internos": len(before.entries),
        "bytes_logicos_totales": sum(e.size for e in before.entries),
        "bytes_logicos_distintos": changed_bytes,
        "bytes_logicos_distintos_solo_precios": price_bytes,
        "bytes_logicos_distintos_solo_permisos": permission_bytes,
        "resto_del_contenido_logico_identico": True,
        "campos_fuera_de_precios_y_permisos_autorizados_identicos": True,
        "permisos_verificados": len(permissions),
        "permiso_oro_uno": sum(gold == 1 for gold, _ in permissions.values()),
        "permiso_cash_cero": sum(cash == 0 for _, cash in permissions.values()),
        "combinaciones_banderas_oro_cash": {"1,0": len(permissions)},
        "permisos_del_resto_identicos": True,
        "indices_verificados": len(after.snapshots),
        "piezas_por_archivo": by_file,
        "registros_individuales_totales": sum(1 for _ in records(before)),
        "registros_individuales_fuera_del_json_sin_cambios": sum(1 for _ in records(before)) - len(old),
        "sha256_original": sha(before.data), "sha256_salida": sha(after.data),
        "bytes_original": len(before.data), "bytes_salida": len(after.data),
        "alcance": "Precios y permisos oro=1/cash=0 en 861 piezas permanentes del JSON; todo lo demas identico",
    }


def solo_oro(original_bytes: bytes) -> tuple[bytes, dict[str, list[int]]]:
    """avatar.xfs original → (avatar.xfs sólo oro, {pieza: [oro, 0]}). Verifica antes de devolver: sólo cambian
    precio y permisos de moneda de las 861 permanentes; todo lo demás, idéntico."""
    original = read_xfs(original_bytes)
    referencia = extract_prices(original)
    require(len(referencia) == 861, f"esperaba 861 piezas permanentes, hay {len(referencia)}")
    convertido = convert(original, referencia)
    verify(original, read_xfs(convertido), referencia)
    return convertido, target_prices(referencia)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Verifica los archivos existentes sin escribir")
    args = parser.parse_args()
    original_bytes = ORIGINAL.read_bytes()
    reference_document = json.loads(REFERENCE.read_text(encoding="utf-8-sig"))
    reference = reference_document["prices"]
    original = read_xfs(original_bytes)
    require(extract_prices(original) == reference and len(reference) == 861,
            "Control inverso fallido: precios originales distintos del JSON")
    if not args.verificar:
        converted = convert(original, reference)
        verify(original, read_xfs(converted), reference)  # valida antes de escribir
        OUTPUT.write_bytes(converted)
        document = dict(reference_document)
        document["source"] = "GunBound Legacy v179 avatar_oro.xfs, permanent individual avatars, gold only"
        wanted = target_prices(reference)
        document["prices"] = {key: wanted[key] for key in reference}
        JSON_OUTPUT.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    # Esta comprobacion lee otra vez los bytes efectivamente escritos en disco.
    result = verify(original, read_xfs(OUTPUT.read_bytes()), reference)
    exported = json.loads(JSON_OUTPUT.read_text(encoding="utf-8"))
    require(set(exported) == set(reference_document), "Formato de JSON distinto del original")
    require(exported["prices"] == extract_prices(read_xfs(OUTPUT.read_bytes())), "JSON de salida inconsistente")
    result["sha256_precios_avatar_oro_json"] = sha(JSON_OUTPUT.read_bytes())
    result["sha256_precios_avatar_json"] = sha(REFERENCE.read_bytes())
    require(ORIGINAL.read_bytes() == original_bytes, "El original cambio durante la ejecucion")
    if not args.verificar:
        CHECK_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
