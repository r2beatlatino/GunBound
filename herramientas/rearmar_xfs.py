"""rearmar_xfs — (de Codex, 16-nov) rearma el graphics.xfs con imágenes cambiadas, conservando todo lo demás.
`parchar_cliente.py` lo usa con `../arte_original/` (fuera del repo) (el arte de GunBound WC GIS 557).
Informe: documentacion/investigacion/ARTE_Y_ARRANQUE.md.

Rearma un FOX7 de Legacy, conservando los bloques no reemplazados.

Uso: python -B rearmar_xfs.py ORIGINAL CARPETA_REEMPLAZOS [--salida graphics_nuevo.xfs]
Los reemplazos son archivos binarios IMG/EPA/etc. con el nombre/ruta del índice;
un PNG no se convierte automáticamente a IMG. Sólo permite escribir junto a este
script o en sus subcarpetas. No modifica el original ni ejecuta código del juego.
"""
import argparse,os,shutil,struct,zlib,json,hashlib
from pathlib import Path
from xfs import XFS,block_write
ROOT=Path(__file__).resolve().parent

def rebuild(original,replacements,output=None):
    original=Path(original).resolve(); replacements=Path(replacements).resolve()
    output=Path(output or ROOT/'graphics_nuevo.xfs').resolve()
    if output==original:
        raise ValueError('La salida tiene que ser distinta del original.')
    if not replacements.is_dir(): raise ValueError('No existe la carpeta de reemplazos.')
    src=XFS(original)
    if src.header[:4]!=b'FOX7':raise ValueError('La escritura está validada sólo para FOX7 de Legacy.')
    chosen={}
    for p in replacements.rglob('*'):
        if p.is_symlink():raise ValueError(f'No se aceptan enlaces: {p}')
        if p.is_file():
            key=p.relative_to(replacements).as_posix().replace('/','\\').lower()
            if key not in src.entries: raise ValueError(f'El reemplazo no existe en el índice: {key}')
            if key in chosen:raise ValueError(f'Nombre duplicado: {key}')
            chosen[key]=p
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix(output.suffix+'.part')
    if temp==original:raise ValueError('Salida temporal inválida')
    manifest=[]
    try:
        with original.open('rb') as fi,temp.open('wb') as fo:
            # Conserva todos los offsets, bloques y restos antiguos: no compacta.
            remaining=src.index_offset
            while remaining:
                b=fi.read(min(8*1024*1024,remaining))
                if not b: raise ValueError('Original truncado')
                fo.write(b);remaining-=len(b)
            for name,path in sorted(chosen.items()):
                data=path.read_bytes();packed=block_write(data);off=fo.tell()
                if off+len(packed)>=2**32:raise ValueError('XFS excede offsets de 32 bits')
                fo.write(packed); i,oldoff,oldflag,oldsize,oldcsize=src.entries[name]
                struct.pack_into('<IIII',src.index,i*128+112,off,1,len(data),len(packed))
                manifest.append(dict(name=name,bytes=len(data),compressed_bytes=len(packed),offset=off,sha256=hashlib.sha256(data).hexdigest()))
            index_offset=fo.tell();header=bytearray(src.header)
            struct.pack_into('<I',header,16,index_offset)
            zh=zlib.compress(header);zi=zlib.compress(src.index)
            if len(zh)>255 or len(zi)>=2**24:raise ValueError('Índice fuera de rango')
            fo.write(bytes([len(zh)]));fo.write(zh);fo.write(len(zi).to_bytes(3,'little'));fo.write(zi)
            fo.seek(0);fo.write(struct.pack('<I',index_offset))
        check=XFS(temp)
        for row in manifest:
            if check.read(row['name'])!=chosen[row['name']].read_bytes():raise ValueError('Falló lectura de reemplazo')
        os.replace(temp,output)
    finally:
        if temp.exists():temp.unlink()
    return dict(original=str(original),output=str(output),entries=len(src.entries),replacements=manifest,bytes=output.stat().st_size)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original');ap.add_argument('reemplazos');ap.add_argument('--salida',default=str(ROOT/'graphics_nuevo.xfs'))
    args=ap.parse_args(); result=rebuild(args.original,args.reemplazos,args.salida)
    print(json.dumps(result,ensure_ascii=False,indent=2))
