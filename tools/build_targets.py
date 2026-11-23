"""Collects every hashed name from the extracted metadata files.
Writes <work>/targets.pkl {hash: roles} and <work>/kinds.pkl ({field hash: type bytes}, {enum hash: value name hashes}).
With --scan the schema found by schema_scan.py (levels.rpf, packs.rpf ...) is added too."""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import psin_format

targets = collections.defaultdict(set); kinds = collections.defaultdict(set); enums = collections.defaultdict(set)
D = common.PSIN_FILES
for f in os.listdir(D):
    if f.endswith('.part.psin'): continue
    try: ch, payload, insts, structs = psin_format.load(os.path.join(D, f))
    except Exception: continue
    if b'LSCH' not in ch: continue
    for h, (size, fs) in structs.items():
        if h > 0xffff: targets[h].add('struct')
        for nh, off, tr, ref in fs:
            if nh != 0x100: targets[nh].add('field'); kinds[nh].add(tr & 0xff)
    for eh, vals in psin_format.enums(ch).items():
        targets[eh].add('enum')
        for v, vh in vals: targets[vh].add('enumval'); enums[eh].add(vh)
if '--scan' in sys.argv:
    t2, k2, e2, _ = pickle.load(open(os.path.join(common.WORK, 'scan_schema.pkl'), 'rb'))
    for h, r in t2.items(): targets[h] |= r
    for h, r in k2.items(): kinds[h] |= r
    for h, r in e2.items(): enums[h] |= r
pickle.dump(dict(targets), open(os.path.join(common.WORK, 'targets.pkl'), 'wb'))
pickle.dump((dict(kinds), dict(enums)), open(os.path.join(common.WORK, 'kinds.pkl'), 'wb'))
roles = collections.Counter(r for v in targets.values() for r in v)
print('hashed names', len(targets), dict(roles))
