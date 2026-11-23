"""Collects judged names, checks each one really hashes to its target and was among the candidates offered, and updates the accepted set.
usage: python merge.py [--save]   (--save also writes the list into the PercyStar names folder)"""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK


def joaat_cs(s):
    h = 0
    for c in s.encode('latin-1', 'replace'):
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; h = (h + (h << 15)) & 0xffffffff
    return h


T = set(int(l, 16) for l in open(os.path.join(HERE, 'in', 'all_targets.txt')))
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
DIRS = [d for d in (os.path.join(HERE, 'judge'), os.path.join(HERE, 'judge_done')) if os.path.isdir(d)]
offered = collections.defaultdict(set)
for J in DIRS:
  for f in os.listdir(J):
    if f.endswith('.txt'):
        for l in open(os.path.join(J, f), encoding='utf-8'):
            if 'candidates: ' in l:
                h = int(l[:8], 16)
                offered[h].update(c.strip() for c in l.rstrip('\n').split('candidates: ')[1].split(' ; '))
stats = collections.Counter(); judged = {}
_rp = os.path.join(HERE, 'rejected.txt')
rejected = set(open(_rp, encoding='utf-8').read().split()) if os.path.exists(_rp) else set()
for _h in [h for h, n in acc.items() if n in rejected]: del acc[_h]
for J, f in sorted((d, f) for d in DIRS for f in os.listdir(d)):
    if not f.endswith('.out'): continue
    n = 0
    for l in open(os.path.join(J, f), encoding='utf-8', errors='replace'):
        p = l.strip().split('\t')
        if len(p) != 2: p = l.strip().split()
        if len(p) != 2: stats['malformed'] += 1; continue
        try: h = int(p[0], 16)
        except ValueError: stats['malformed'] += 1; continue
        name = p[1].strip()
        if joaat_cs(name) != h: stats['hash mismatch'] += 1; continue
        if h not in T: stats['not a target'] += 1; continue
        if name not in offered[h]: stats['not offered'] += 1; continue
        if name in rejected: stats['rejected by review'] += 1; continue
        if h in known: stats['already known'] += 1; continue
        if h not in judged: n += 1
        judged[h] = name
    print('%-12s %4d accepted' % (f, n))
print('judged', len(judged), dict(stats))
new = {h: n for h, n in judged.items() if h not in acc}
acc.update(new)
pickle.dump(acc, open(os.path.join(HERE, 'accepted.pkl'), 'wb'))
pickle.dump(judged, open(os.path.join(HERE, 'judged.pkl'), 'wb'))
print('accepted set now', len(acc), '(+%d)' % len(new), '| total resolved', len(set(known) | set(acc)), 'of', len(T))
if '--save' in sys.argv:
    out = common.NAMES_DIR
    p = os.path.join(out, 'built.txt')
    cur = set(open(p, encoding='utf-8').read().split()) if os.path.exists(p) else set()
    cur.update(acc.values())
    open(p, 'w', encoding='utf-8').write('\n'.join(sorted(cur)))
    print('built.txt now', len(cur), 'names')
