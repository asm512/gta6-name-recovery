"""Minimal reader for PSIN metadata files: sections, instance table and the struct schema."""
import struct


def chunks(b):
    """IFF style sections with big-endian sizes: {tag: body}"""
    out = {}
    pos = 0
    while pos + 8 <= len(b):
        tag = b[pos:pos + 4]
        sz = struct.unpack('>I', b[pos + 4:pos + 8])[0]
        if sz < 8 or pos + sz > len(b):
            break
        out[tag] = b[pos + 8:pos + sz]
        pos += sz
    return out


def r32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def parse(b):
    """returns (sections, payload, instances, structs)
    instances: list of (tag, size, payload offset); structs: {hash: (size, [(name hash, offset, type, ref)])}"""
    ch = chunks(b)
    body = ch[b'PSIN']
    i = 0
    raw = []
    while i + 8 <= len(body):
        if body[i:i + 8] == b'pppppppp':
            i += 8
            break
        raw.append((r32(body, i), r32(body, i + 4)))
        i += 16
    payload = body[i:]
    cur = 0
    insts = []
    for tag, size in raw:
        insts.append((tag, size, cur))
        cur += (size + 15) & ~15
    lsch = ch.get(b'LSCH', b'')
    off = 0
    hdrs = []
    while off + 32 <= len(lsch) and lsch[off + 16:off + 24] == b'\xaa' * 8:
        hdrs.append((r32(lsch, off), r32(lsch, off + 24), r32(lsch, off + 28) >> 16))
        off += 32
    structs = {}
    for h, size, fc in hdrs:
        fs = []
        for _ in range(fc):
            if off + 16 > len(lsch):
                break
            fs.append((r32(lsch, off), r32(lsch, off + 4), r32(lsch, off + 8), r32(lsch, off + 12)))
            off += 16
        structs[h] = (size, fs)
    return ch, payload, insts, structs


def enums(ch):
    """{enum hash: [(value, value name hash)]} from the LENM section"""
    lenm = ch.get(b'LENM', b'')
    off = 0
    out = {}
    while off + 24 <= len(lenm) and lenm[off + 8:off + 16] == b'\xee' * 8:
        h = r32(lenm, off)
        cnt = r32(lenm, off + 16)
        off += 24
        vals = []
        for _ in range(cnt):
            if off + 16 > len(lenm):
                break
            vals.append((struct.unpack_from('<q', lenm, off)[0], r32(lenm, off + 8)))
            off += 16
        out[h] = vals
    return out


def load(path):
    with open(path, 'rb') as f:
        return parse(f.read())
