"""Resolves the hashes found by schema_scan.py against everything already at hand: the name lists, the names
recovered so far and the text inside the scanned metadata files. Prints counts per kind and writes
<work>/scan_hits.pkl {hash: (name, source)}."""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import joaat_cs

W = common.WORK
targets, kinds, enums, structs = pickle.load(open(os.path.join(W, 'scan_schema.pkl'), 'rb'))
old = pickle.load(open(os.path.join(W, 'targets_base.pkl' if os.path.exists(os.path.join(W, 'targets_base.pkl')) else 'targets.pkl'), 'rb'))
new = {h: r for h, r in targets.items() if h not in old}


def kind(r):
    return 'field' if 'field' in r else 'struct' if 'struct' in r else 'enum value' if 'enumval' in r else 'enum'


hits = {}


def test(names, source):
    n = 0
    for nm in names:
        h = joaat_cs(nm)
        if h in new and h not in hits: hits[h] = (nm, source); n += 1
    return n


for f in sorted(os.listdir(common.NAMES_DIR)):
    if f.endswith('.txt'):
        names = open(os.path.join(common.NAMES_DIR, f), encoding='utf-8', errors='replace').read().split()
        print('%-34s %7d names -> %d' % (f, len(names), test(names, 'name list' if f != 'built.txt' else 'built')))
lp = os.path.join(W, 'list_sources.pkl')
if os.path.exists(lp):
    for src, names in pickle.load(open(lp, 'rb')).items():
        print('%-34s %7d names -> %d' % (src, len(names), test(names, 'name list')))
tokens = pickle.load(open(os.path.join(W, 'scan_tokens.pkl'), 'rb'))
print('%-34s %7d names -> %d' % ('text in the scanned files', len(tokens), test([t.decode('latin-1') for t in tokens], 'game text')))
tot = collections.Counter(kind(r) for r in new.values()); got = collections.Counter(kind(new[h]) for h in hits)
print('new hashes %d, resolved %d (%.1f%%): %s' % (len(new), len(hits), 100.0 * len(hits) / max(1, len(new)), {k: '%d/%d' % (got[k], tot[k]) for k in tot}))
print('all hashes in the scanned archives %d, already among the earlier targets %d' % (len(targets), len(targets) - len(new)))
pickle.dump(hits, open(os.path.join(W, 'scan_hits.pkl'), 'wb'))
