"""Picks the files with the most unresolved names and writes a digest of each for a vocabulary writer.
usage: python topics.py <how many>"""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
from psin_format import load
D = os.path.join(common.PSIN_FILES)
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
known.update(pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb')))
KN = {0x01: 'bool', 0x14: 'int', 0x15: 'int', 0x11: 'int', 0x13: 'int', 0x21: 'float', 0x20: 'float', 0x31: 'vec', 0x33: 'vec', 0x34: 'vec', 0x30: 'vec2', 0x4a: 'hash', 0x4d: 'hash', 0x4b: 'hash', 0x44: 'string',
      0x05: 'struct', 0x07: 'pointer', 0x52: 'array', 0x5c: 'array', 0x60: 'enum', 0x62: 'enum', 0x65: 'flags'}
files = {}
for f in os.listdir(D):
    if f.endswith('.part.psin'): continue
    try: ch, payload, insts, structs = load(os.path.join(D, f))
    except Exception: continue
    if b'LSCH' not in ch: continue
    unk = set()
    for h, (size, fs) in structs.items():
        if h > 0xffff and h not in known: unk.add(h)
        unk.update(nh for nh, off, tr, ref in fs if nh != 0x100 and nh not in known)
    files[f] = (unk, structs)
covered = set(); picks = []
for _ in range(int(sys.argv[1])):
    best = max(files, key=lambda f: len(files[f][0] - covered))
    gain = len(files[best][0] - covered)
    if gain < 40: break
    picks.append((best, gain)); covered |= files[best][0]
out = os.path.join(HERE, 'topics'); os.makedirs(out, exist_ok=True)
for i, (f, gain) in enumerate(picks):
    unk, structs = files[f]
    lines = ['FILE %s: %d structs, %d unresolved names' % (f, len(structs), len(unk)), '']
    for h, (size, fs) in sorted(structs.items(), key=lambda kv: -sum(1 for x in kv[1][1] if x[0] not in known and x[0] != 0x100)):
        real = [x for x in fs if x[0] != 0x100]
        kn = [known[x[0]] for x in real if x[0] in known]
        un = collections.Counter(KN.get(x[2] & 0xff, 'other') for x in real if x[0] not in known)
        if not un and h in known: continue
        lines.append('struct %s: known fields [%s]; unknown fields: %s' % (known.get(h, '(unknown name)'), ', '.join(kn[:40]), ', '.join('%d %s' % (c, t) for t, c in un.most_common()) or 'none'))
        if len(lines) > 260: break
    open(os.path.join(out, 't%02d.txt' % i), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    open(os.path.join(out, 't%02d.src' % i), 'w').write(os.path.join(D, f))
    print('t%02d %-28s unresolved %4d (new %4d)  %d bytes' % (i, f, len(unk), gain, os.path.getsize(os.path.join(out, 't%02d.txt' % i))))
print('files', len(picks), 'cover', len(covered), 'unresolved names')
