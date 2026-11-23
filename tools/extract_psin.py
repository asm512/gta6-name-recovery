"""Extracts every PSIN metadata file from the given game archives into <work>/psin_files.
usage: python extract_psin.py common.rpf script.rpf data.rpf

Meant for the small archives: each one is read into memory. For the large ones use schema_scan.py,
which walks the file in pieces and keeps only the schema."""
import os, re, sys, zlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
ROOT = common.game_dir()
OUT = common.PSIN_FILES
os.makedirs(OUT, exist_ok=True)
TAGS = (b'PSIN', b'LSCH', b'LENM', b'LSNS', b'LGID', b'LRSC', b'CHKS', b'LMAP', b'PMAP', b'STRE', b'LSTR')


def iff_len(b):
    pos = 0
    while pos + 8 <= len(b):
        if b[pos:pos + 4] not in TAGS: break
        sz = struct.unpack('>I', b[pos + 4:pos + 8])[0]
        if sz < 8: break
        pos += sz
    return pos


n = 0
for name in sys.argv[1:]:
    d = open(os.path.join(ROOT, name), 'rb').read()
    stem = os.path.basename(name).split('.')[0]
    for m in re.finditer(rb'\x78[\x9c\xda\x01\x5e]', d):
        i = m.start()
        try:
            o = zlib.decompressobj().decompress(d[i:i + (1 << 20)], 1 << 20)
        except Exception:
            continue
        if o[:4] != b'PSIN' or len(o) < 16: continue
        # a file may be stored as several zlib streams: walk the following ones until the section chain is complete
        buf = bytearray(o); pos = i
        dz = zlib.decompressobj(); dz.decompress(d[i:i + (1 << 20)], 1 << 20)
        tries = 0
        while True:
            if b'CHKS' in buf[-64:] and iff_len(bytes(buf)) == len(buf): break
            used = len(d[pos:pos + (1 << 20)]) - len(dz.unused_data)
            nxt = pos + used
            k = d.find(b'\x78', nxt)
            found = False
            while 0 <= k < nxt + 64:
                if d[k + 1] in (0x9c, 0xda, 0x01, 0x5e):
                    try:
                        dz = zlib.decompressobj(); o2 = dz.decompress(d[k:k + (1 << 20)], 1 << 20)
                        buf += o2; pos = k; found = True; break
                    except Exception:
                        pass
                k = d.find(b'\x78', k + 1)
            tries += 1
            if not found or tries > 200: break
        ok = iff_len(bytes(buf)) == len(buf) and b'CHKS' in buf[-64:]
        open(os.path.join(OUT, '%s_%08x%s.psin' % (stem, i, '' if ok else '.part')), 'wb').write(bytes(buf))
        n += 1
print('extracted', n)
