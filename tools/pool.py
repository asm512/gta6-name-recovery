"""Builds judge files: unresolved names with their best brute-force candidates and the context a reader needs to tell real from chance.
usage: python pool.py <tag> <lines per file> <crack output file> ..."""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
tag, per = sys.argv[1], int(sys.argv[2])
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
for f in os.listdir(HERE):
    if f.startswith('cracked_') and f.endswith('.txt'):
        pass
acc_p = os.path.join(HERE, 'accepted.pkl')
accepted = pickle.load(open(acc_p, 'rb')) if os.path.exists(acc_p) else {}
known.update(accepted)
owners, members, samples, enum_of, enum_vals = pickle.load(open(os.path.join(HERE, 'index.pkl'), 'rb'))
kinds, enums = pickle.load(open(os.path.join(common.WORK, 'kinds.pkl'), 'rb'))
KN = {0x01: 'bool', 0x10: 'int', 0x11: 'int', 0x12: 'int', 0x13: 'int', 0x14: 'int', 0x15: 'int', 0x20: 'float', 0x21: 'float', 0x30: 'vec2', 0x31: 'vec3', 0x33: 'vec', 0x34: 'vec',
      0x4a: 'hash', 0x4b: 'hash', 0x4d: 'hash', 0x44: 'string', 0x42: 'string', 0x05: 'struct', 0x07: 'pointer', 0x52: 'array', 0x5c: 'array', 0x50: 'array', 0x60: 'enum', 0x62: 'enum',
      0x65: 'flags', 0x63: 'flags', 0x71: 'map', 0x08: 'hash64', 0x4f: 'hash64'}
cands = collections.defaultdict(dict)
# candidates a judge has already seen are not offered again
already_offered = collections.defaultdict(set)
_done = os.path.join(HERE, 'judge_done')
if os.path.isdir(_done):
    for _f in os.listdir(_done):
        if _f.endswith('.txt'):
            for _l in open(os.path.join(_done, _f), encoding='utf-8'):
                if 'candidates: ' in _l:
                    already_offered[int(_l[:8], 16)].update(c.strip() for c in _l.rstrip(chr(10)).split('candidates: ')[1].split(' ; '))
for path in sys.argv[3:]:
    H = collections.defaultdict(list); D = collections.defaultdict(list)
    for l in open(path, encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'H': H[int(p[1])].append((int(p[2]), int(p[3], 16), p[4]))
        elif p[0] == 'D': D[int(p[1])].append(int(p[2]))
    ntargets = len(set(h for v in H.values() for _, h, _ in v)) or 1
    for ln, hits in H.items():
        if ln > 4: continue
        dec = sorted(D[ln])
        # widest score cut where chance candidates stay under 0.35 per target
        limit = int(0.8 * ntargets * 4)
        cut = dec[limit] if len(dec) > limit else float('inf')
        for s, h, n in hits:
            if s <= cut and h not in known and n not in already_offered[h]:
                if n not in cands[h] or s < cands[h][n]: cands[h][n] = s


def context(h):
    ks = kinds.get(h, set())
    ty = '/'.join(sorted(set(KN.get(k, 'k%02x' % k) for k in ks))) or ('struct-name' if h in members else ('enum-value' if h in enum_of else '?'))
    best = None
    for o in owners.get(h, ()):
        sib = [known[x] for x in members[o] if x in known and x != h]
        score = (o in known, len(sib))
        if best is None or score > best[0]: best = (score, o, sib)
    parts = [ty]
    if best:
        _, o, sib = best
        parts.append('in ' + known.get(o, 'struct_%08x' % o))
        v = samples.get((o, h))
        if v: parts.append('value ' + v)
        if sib: parts.append('siblings ' + ', '.join(sorted(sib)[:9]))
    if h in members:
        fields = [known[x] for x in members[h] if x in known]
        if fields: parts.append('has fields ' + ', '.join(sorted(fields)[:10]))
    if h in enum_of:
        e = next(iter(enum_of[h])); sv = [known[x] for x in enum_vals[e] if x in known]
        if sv: parts.append('other values of the enum ' + ', '.join(sorted(sv)[:8]))
    return ' | '.join(parts)


rows = []
for h, c in cands.items():
    top = [n for n, s in sorted(c.items(), key=lambda kv: kv[1])[:4]]
    rows.append('%08x | %s | candidates: %s' % (h, context(h), ' ; '.join(top)))
rows.sort(key=lambda r: r.split(' | ')[2] if r.count(' | ') > 2 else r)
d = os.path.join(HERE, 'judge'); os.makedirs(d, exist_ok=True)
n = 0
for i in range(0, len(rows), per):
    open(os.path.join(d, '%s_%02d.txt' % (tag, n)), 'w', encoding='utf-8').write('\n'.join(rows[i:i + per]) + '\n')
    n += 1
print(len(rows), 'targets with candidates ->', n, 'files')
print('\n'.join(rows[:6]))
