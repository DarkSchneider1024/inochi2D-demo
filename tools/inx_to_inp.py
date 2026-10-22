"""Re-pack an Inochi2D .inx/.inp so every texture is PNG (browsers cannot decode the RLE TGA
textures that Inochi Creator 0.7 writes). JSON is kept byte-for-byte; EXT_SECT is dropped.

    python tools/inx_to_inp.py ../example-models/Aka.inx models/official/aka.inp
"""
import io
import struct
import sys

from PIL import Image


def main(src, dst):
    b = open(src, 'rb').read()
    assert b[:8] == b'TRNSRTS\0', 'not an INP container'
    n = struct.unpack('>I', b[8:12])[0]
    js = b[12:12 + n]
    o = 12 + n
    assert b[o:o + 8] == b'TEX_SECT'
    count = struct.unpack('>I', b[o + 8:o + 12])[0]
    o += 12
    out = [b'TRNSRTS\0', struct.pack('>I', n), js, b'TEX_SECT', struct.pack('>I', count)]
    for _ in range(count):
        size, enc = struct.unpack('>I', b[o:o + 4])[0], b[o + 4]
        data = b[o + 5:o + 5 + size]
        o += 5 + size
        if enc != 0:                                   # 1 = TGA
            im = Image.open(io.BytesIO(data)).convert('RGBA')
            buf = io.BytesIO()
            im.save(buf, 'PNG', optimize=True)
            data = buf.getvalue()
        out += [struct.pack('>I', len(data)), b'\0', data]
    open(dst, 'wb').write(b''.join(out))
    print(f'{src} -> {dst}: {count} textures, {sum(map(len, out)) / 1e6:.1f} MB')


if __name__ == '__main__':
    main(*sys.argv[1:3])
