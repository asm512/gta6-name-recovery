"""Collects every hashed name from the extracted metadata files.
Writes <work>/targets.pkl {hash: roles} and <work>/kinds.pkl ({field hash: type bytes}, {enum hash: value name hashes}).
With --scan the schema found by schema_scan.py (levels.rpf, packs.rpf ...) is added too, with --exe the tables
read from the executable by exe_tables.py. Names that come only from the executable are listed in <work>/exe_only.pkl."""
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
if '--exe' in sys.argv:
    structs, exe_enums = pickle.load(open(os.path.join(common.WORK, 'exe_schema.pkl'), 'rb'))
    in_files = set(targets)
    # the executable numbers its member types differently: learn the file type of each from fields found in both
    seen = collections.defaultdict(collections.Counter)
    for h, (size, flags, ms) in structs.items():
        for nh, kind, sub, off, default, ref in ms:
            for k in kinds.get(nh, ()): seen[(kind, sub)][k] += 1
    as_file = {t: c.most_common(1)[0][0] for t, c in seen.items() if c.most_common(1)[0][1] >= 5}
    for h, (size, flags, ms) in structs.items():
        targets[h].add('struct')
        for nh, kind, sub, off, default, ref in ms:
            targets[nh].add('field')
            if nh not in in_files and (kind, sub) in as_file: kinds[nh].add(as_file[(kind, sub)])
    for eh, vals in exe_enums.items():
        targets[eh].add('enum')
        for v, vh in vals:
            if vh > 0xffff: targets[vh].add('enumval'); enums[eh].add(vh)
    pickle.dump(set(targets) - in_files, open(os.path.join(common.WORK, 'exe_only.pkl'), 'wb'))
    print('member types of the executable mapped to file types:', len(as_file), 'of', len(seen), '| names only in the executable', len(set(targets) - in_files))
# enum values without a name carry a small number where the hash would be: nothing to recover there
for h in [h for h in targets if h <= 0xffff]:
    del targets[h]
for vals in enums.values(): vals.difference_update([v for v in vals if v <= 0xffff])
pickle.dump(dict(targets), open(os.path.join(common.WORK, 'targets.pkl'), 'wb'))
pickle.dump((dict(kinds), dict(enums)), open(os.path.join(common.WORK, 'kinds.pkl'), 'wb'))
roles = collections.Counter(r for v in targets.values() for r in v)
print('hashed names', len(targets), dict(roles))
