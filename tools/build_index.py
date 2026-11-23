"""One pass over the extracted metadata files (and those kept by schema_scan.py): which struct owns which field,
and one sample value per field. Writes <work>/crack/index.pkl."""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
from psin_format import load
D = os.path.join(common.PSIN_FILES)
owners = collections.defaultdict(set)      # field hash -> struct hashes
members = collections.defaultdict(dict)    # struct hash -> {field hash: (offset, kind, ref)}
samples = {}                               # (struct, field) -> text
enum_of = collections.defaultdict(set)     # enum value hash -> enum hashes
enum_vals = collections.defaultdict(set)


def sample(payload, o, kind):
    try:
        if kind == 0x21: return '%.5g' % struct.unpack_from('<f', payload, o)[0]
        if kind == 0x01: return 'true' if payload[o] else 'false'
        if kind == 0x14: return str(struct.unpack_from('<i', payload, o)[0])
        if kind == 0x15: return str(struct.unpack_from('<I', payload, o)[0])
        if kind == 0x11: return str(payload[o])
        if kind == 0x13: return str(struct.unpack_from('<H', payload, o)[0])
        if kind in (0x31, 0x33, 0x34): return ' '.join('%.3g' % x for x in struct.unpack_from('<4f', payload, o))
    except Exception:
        pass
    return ''


files = [os.path.join(D, f) for f in os.listdir(D)]
# files kept by schema_scan.py from the large archives
SCAN = os.path.join(common.WORK, 'psin_scan')
for dp, dn, fn in os.walk(SCAN):
    files += [os.path.join(dp, f) for f in fn]
for path in files:
    if not path.endswith('.psin') or path.endswith('.part.psin'): continue
    try: ch, payload, insts, structs = load(path)
    except Exception: continue
    if b'LSCH' not in ch: continue
    first = {}
    for t, s, o in insts:
        if t in structs and t not in first: first[t] = o
    for h, (size, fs) in structs.items():
        for nh, off, tr, ref in fs:
            if nh == 0x100: continue
            owners[nh].add(h); members[h][nh] = (off, tr & 0xff, ref)
            if (h, nh) not in samples and h in first:
                v = sample(payload, first[h] + off, tr & 0xff)
                if v: samples[(h, nh)] = v
    lenm = ch.get(b'LENM', b''); off = 0
    while off + 24 <= len(lenm) and lenm[off + 8:off + 16] == b'\xee' * 8:
        eh, cnt = struct.unpack_from('<I', lenm, off)[0], struct.unpack_from('<I', lenm, off + 16)[0]; off += 24
        for _ in range(cnt):
            if off + 16 > len(lenm): break
            vh = struct.unpack_from('<I', lenm, off + 8)[0]; enum_of[vh].add(eh); enum_vals[eh].add(vh); off += 16
# schema of scanned files that were not kept
sp = os.path.join(common.WORK, 'scan_schema.pkl')
if os.path.exists(sp):
    t2, k2, e2, s2 = pickle.load(open(sp, 'rb'))
    for h, (size, fs) in s2.items():
        for nh, off, tr, ref in fs:
            if nh == 0x100: continue
            owners[nh].add(h); members[h].setdefault(nh, (off, tr & 0xff, ref))
    for eh, vals in e2.items():
        for vh in vals: enum_of[vh].add(eh); enum_vals[eh].add(vh)
# structs, defaults and enums from the tables of the executable
xp = os.path.join(common.WORK, 'exe_schema.pkl')
if os.path.exists(xp):
    xs, xe = pickle.load(open(xp, 'rb'))
    for h, (size, flags, ms) in xs.items():
        for nh, kind, sub, off, default, ref in ms:
            owners[nh].add(h)
            if nh not in members[h]: members[h][nh] = (off, 0, ref)
            elif ref and not members[h][nh][2]: members[h][nh] = (members[h][nh][0], members[h][nh][1], ref)
            if default and (h, nh) not in samples: samples[(h, nh)] = 'default ' + default
    for eh, vals in xe.items():
        for v, vh in vals:
            if vh > 0xffff: enum_of[vh].add(eh); enum_vals[eh].add(vh)
pickle.dump((dict(owners), dict(members), samples, dict(enum_of), dict(enum_vals)), open(os.path.join(HERE, 'index.pkl'), 'wb'))
print('fields', len(owners), 'structs', len(members), 'samples', len(samples), 'enums', len(enum_vals))
