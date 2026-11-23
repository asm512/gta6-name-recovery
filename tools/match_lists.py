"""Tests every identifier in the public name lists against the hashed names.

Expects clones of the list repositories in <work>/lists/<owner>_<repo> (see tools/README.md for which ones).
Writes <work>/list_sources.pkl {source: names} and <work>/hit_lists.pkl {hash: name}."""
import os, re, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import joaat_cs
HERE = common.WORK
L = os.path.join(HERE, 'lists')
T = pickle.load(open(os.path.join(HERE, 'targets.pkl'), 'rb'))
roles = collections.Counter(r for v in T.values() for r in v)
IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]{1,95}')
sources = collections.OrderedDict()


def add(src, names):
    sources.setdefault(src, set()).update(n for n in names if 2 <= len(n) <= 96)


def idents(root, exts=None, cap=60 << 20):
    names = set()
    for dp, dn, fn in os.walk(root):
        if '.git' in dp: continue
        for f in fn:
            if exts and not f.lower().endswith(exts): continue
            p = os.path.join(dp, f)
            if os.path.getsize(p) > cap: continue
            try: names.update(IDENT.findall(open(p, encoding='utf-8', errors='replace').read()))
            except Exception: pass
    return names


# parser dumps: every quoted identifier in the json text (:: namespaces become __)
root = os.path.join(L, 'alexguirre_rage-parser-dumps', 'dumps')
if os.path.isdir(root):
    for game in sorted(os.listdir(root)):
        gd = os.path.join(root, game)
        if not os.path.isdir(gd):
            if game.endswith('.txt'): add('parser-dumps/' + game, open(gd, encoding='utf-8', errors='replace').read().split())
            continue
        names = set()
        for f in sorted(os.listdir(gd)):
            if not f.endswith('.json'): continue
            txt = open(os.path.join(gd, f), encoding='utf-8', errors='replace').read()
            for m in re.finditer(r'"([A-Za-z_][A-Za-z0-9_:]{1,120})"', txt):
                s = m.group(1)
                names.add(s.replace('::', '__'))
                if '::' in s: names.update(s.split('::'))
        add('parser-dumps/' + game, names)
for repo, exts, cap in (('dexyfex_CodeWalker', ('.cs', '.txt', '.xml', '.ini'), 30 << 20), ('DurtyFree_gta-v-data-dumps', None, 60 << 20),
                        ('VIRUXE_rage-cli', None, 20 << 20), ('TrinitronClient_GTA6-Asset-Info', None, 20 << 20), ('ItsNotRexed_Leonida', None, 20 << 20)):
    if os.path.isdir(os.path.join(L, repo)): add(repo, idents(os.path.join(L, repo), exts, cap))

hp = os.path.join(HERE, 'hit_cs.pkl')
prev = pickle.load(open(hp, 'rb')) if os.path.exists(hp) else {}
allhit = {}
for src, names in sources.items():
    hit = {}
    for n in names:
        h = joaat_cs(n)
        if h in T: hit[h] = n
    new = sum(1 for h in hit if h not in prev and h not in allhit)
    # a list of N names is expected to hit N * targets / 2^32 hashes by chance
    print('%-40s %7d names -> %5d hits (%5d new), expected by chance %.1f' % (src, len(names), len(hit), new, len(names) * len(T) / 2 ** 32))
    for h, n in hit.items(): allhit.setdefault(h, n)
tot = dict(prev); tot.update(allhit)
rr = collections.Counter(r for h in tot for r in T[h])
print('lists alone', len(allhit), '| with game text', len(tot), 'of', len(T), {r: '%d/%d' % (rr[r], roles[r]) for r in roles})
pickle.dump(sources, open(os.path.join(HERE, 'list_sources.pkl'), 'wb'))
pickle.dump(tot, open(os.path.join(HERE, 'hit_lists.pkl'), 'wb'))
