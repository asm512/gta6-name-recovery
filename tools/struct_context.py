"""Prints struct contexts (known and unknown field names with types and sample values) for a set of files or struct hashes.
usage: python struct_context.py <psin file> [struct hash ...]   (no hashes = every struct with unresolved fields)"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
from psin_format import load
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
for extra in ('guess_hits.pkl',):
    p = os.path.join(HERE, extra)
    if os.path.exists(p): known.update(pickle.load(open(p, 'rb')))
KN = {0x01: 'bool', 0x10: 's8', 0x11: 'u8', 0x12: 's16', 0x13: 'u16', 0x14: 's32', 0x15: 'u32', 0x20: 'half', 0x21: 'float', 0x30: 'vec2', 0x31: 'vec3', 0x33: 'vec4', 0x34: 'vec4',
      0x4a: 'hash', 0x4b: 'hash', 0x4d: 'hash', 0x44: 'string', 0x42: 'string', 0x05: 'struct', 0x07: 'ptr', 0x52: 'array', 0x5c: 'array', 0x50: 'fixedarray', 0x60: 'enum8', 0x62: 'enum32', 0x65: 'flags', 0x63: 'flags', 0x71: 'map'}


def sample(payload, o, kind):
    try:
        if kind == 0x21: return '%.6g' % struct.unpack_from('<f', payload, o)[0]
        if kind == 0x01: return str(bool(payload[o]))
        if kind in (0x14,): return str(struct.unpack_from('<i', payload, o)[0])
        if kind in (0x15,): return str(struct.unpack_from('<I', payload, o)[0])
        if kind in (0x11,): return str(payload[o])
        if kind in (0x13,): return str(struct.unpack_from('<H', payload, o)[0])
        if kind in (0x4a, 0x4b, 0x4d):
            v = struct.unpack_from('<I', payload, o)[0]; return '0x%08x' % v
        if kind in (0x31, 0x33, 0x34): return ' '.join('%.4g' % x for x in struct.unpack_from('<4f', payload, o))
        if kind in (0x60,): return str(payload[o])
        if kind in (0x62, 0x65): return str(struct.unpack_from('<I', payload, o)[0])
    except Exception:
        pass
    return ''


def main():
    ch, payload, insts, structs = load(sys.argv[1])
    want = [int(x, 16) for x in sys.argv[2:]]
    by_tag = collections.defaultdict(list)
    for t, s, o in insts: by_tag[t].append((s, o))
    for h, (size, fs) in structs.items():
        real = [f for f in fs if f[0] != 0x100]
        unk = [f for f in real if f[0] not in known]
        if (want and h not in want) or (not want and not unk): continue
        recs = []
        for s, o in by_tag.get(h, []):
            for e in range(0, s - size + 1, max(size, 1)):
                recs.append(o + e)
                if len(recs) >= 3: break
        print('STRUCT %s (0x%08x) size %d, %d fields, %d unknown' % (known.get(h, '?'), h, size, len(real), len(unk)))
        for nh, off, tr, ref in sorted(real, key=lambda f: f[1]):
            k = tr & 0xff
            vals = [sample(payload, r + off, k) for r in recs]
            ty = KN.get(k, 'k%02x' % k)
            if k in (0x05, 0x60, 0x62, 0x65) and ref in known: ty += ':' + known[ref]
            print('  +%-4d %-22s %-11s %s' % (off, known.get(nh, '0x%08x' % nh), ty, ' | '.join(v for v in vals if v)))
        print()


main()
