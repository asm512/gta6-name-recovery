"""Per-struct packets: each struct with unresolved fields, its known field names and what the unknown ones hold.
usage: python sprep.py <structs per file>"""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
per = int(sys.argv[1])
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
known.update(pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb')))
owners, members, samples, enum_of, enum_vals = pickle.load(open(os.path.join(HERE, 'index.pkl'), 'rb'))
KN = {0x01: 'bool', 0x10: 'int', 0x11: 'int', 0x12: 'int', 0x13: 'int', 0x14: 'int', 0x15: 'int', 0x20: 'float', 0x21: 'float', 0x30: 'vec2', 0x31: 'vec', 0x33: 'vec', 0x34: 'vec',
      0x4a: 'hash', 0x4b: 'hash', 0x4d: 'hash', 0x44: 'string', 0x42: 'string', 0x05: 'struct', 0x07: 'pointer', 0x52: 'array', 0x5c: 'array', 0x50: 'array', 0x60: 'enum', 0x62: 'enum',
      0x65: 'flags', 0x63: 'flags', 0x71: 'map', 0x08: 'hash64', 0x4f: 'hash64'}
rows = []
for s, fields in members.items():
    unk = [(h, v) for h, v in fields.items() if h not in known]
    kn = [(known[h], v) for h, v in fields.items() if h in known]
    if not unk or len(kn) + (s in known) == 0: continue
    rows.append((len(unk), s, unk, kn))
rows.sort(key=lambda r: -r[0])
out = os.path.join(HERE, 'sp'); os.makedirs(out, exist_ok=True)
index = {}
lines = []
for i, (n, s, unk, kn) in enumerate(rows):
    index[i] = s
    kn_txt = ', '.join('%s:%s' % (name, KN.get(v[1], '?')) for name, v in sorted(kn, key=lambda x: x[1][0])[:45])
    un = collections.defaultdict(list)
    for h, v in unk:
        un[KN.get(v[1], 'other')].append(samples.get((s, h), ''))
    un_txt = '; '.join('%d %s%s' % (len(vs), t, (' (values ' + ', '.join(x for x in vs[:6] if x) + ')') if any(vs) else '') for t, vs in un.items())
    lines.append('S%d %s | known: %s | unknown: %s' % (i, known.get(s, '(name unknown)'), kn_txt or '(none)', un_txt))
n = 0
for i in range(0, len(lines), per):
    open(os.path.join(out, 'sp_%02d.txt' % n), 'w', encoding='utf-8').write('\n'.join(lines[i:i + per]) + '\n')
    n += 1
pickle.dump(index, open(os.path.join(HERE, 'sp_index.pkl'), 'wb'))
print(len(rows), 'structs,', sum(r[0] for r in rows), 'unresolved fields ->', n, 'files')
print(lines[3][:700])
