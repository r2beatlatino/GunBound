"""Lectura estática de los XFS FOX7 de esta colección, sin DLL del juego."""
import struct,zlib
from pathlib import Path

def block_read(f, size):
    out=bytearray()
    while len(out)<size:
        remain=size-len(out)
        count=min(65536,remain)
        packed=int.from_bytes(f.read(3),'little')
        if packed&0x800000:
            actual=packed&0x3fffff
            if not 0<actual<=count: raise ValueError(('block size',actual,count,f.tell()))
            count=actual
            if not packed&0x400000: packed=int.from_bytes(f.read(3),'little')
        elif remain<65536:raise ValueError('missing partial block marker')
        length=packed&0x3fffff; flag=bool(packed&0x400000)
        f.read(2) # opaque/checksum bytes; zero in most Legacy blocks
        b=f.read(length)
        if len(b)!=length: raise ValueError('truncated block')
        if flag==0: b=zlib.decompress(b)
        if len(b)!=count: raise ValueError(('decoded size',len(b),count))
        out.extend(b)
    return bytes(out)

def block_write(data):
    out=bytearray()
    for p in range(0,len(data),65536):
        b=data[p:p+65536]
        c=zlib.compress(b)
        flag=0
        if len(c)>=len(b): c=b; flag=1
        if len(b)<65536 and not flag:out.extend((len(b)|0x800000).to_bytes(3,'little'))
        marker=(0x400000 if flag else 0)|(0x800000 if flag and len(b)<65536 else 0)
        out.extend((len(c)|marker).to_bytes(3,'little'));out.extend(b'\0\0');out.extend(c)
    return bytes(out)

class XFS:
    def __init__(self,path):
        self.path=Path(path)
        with self.path.open('rb') as f:
            self.index_offset=struct.unpack('<I',f.read(4))[0]; f.seek(self.index_offset)
            # FOX7 footer: uint8 compressed-header length, header; uint24 index length, index.
            n=f.read(1)[0]; self.header=zlib.decompress(f.read(n))
            if self.header[:4] not in (b'FOX7',b'XFS2'): raise ValueError('not FOX7/XFS2')
            count=struct.unpack_from('<I',self.header,8)[0]
            n=int.from_bytes(f.read(3),'little'); self.index=bytearray(zlib.decompress(f.read(n)))
            if len(self.index)!=count*128: raise ValueError('bad index size')
        self.entries={}
        for i in range(count):
            p=i*128; raw=self.index[p:p+112].split(b'\0',1)[0]; name=raw.decode('cp1252')
            self.entries[name.lower()]=(i,*struct.unpack_from('<IIII',self.index,p+112))
    def read(self,name):
        _,offset,flag,size,csize=self.entries[name.lower()]
        with self.path.open('rb') as f:
            f.seek(offset)
            if flag==0: return f.read(size)
            if flag!=1: raise ValueError(('entry flag',flag))
            out=block_read(f,size)
            if f.tell()!=offset+csize: raise ValueError(('entry csize',name,f.tell()-offset,csize))
            return out
