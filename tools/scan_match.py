"""Resolves hashes added to the targets (by schema_scan.py or exe_tables.py) against the name lists at hand.

Lists of parser names are taken as they are. The loose sources (every identifier of a code base or data dump) are
large enough to hit a few dozen hashes by chance, so from those only names built from words that parser names use
are kept. With --save the kept names that the names folder lacks are added to other-sources.txt there.
usage: python scan_match.py [--save]"""
import os, re, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import joaat_cs

W = common.WORK
T = pickle.load(open(os.path.join(W, 'targets.pkl'), 'rb'))
TOK = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+|_+')


def kind(r):
    return 'field' if 'field' in r else 'struct' if 'struct' in r else 'enum value' if 'enumval' in r else 'enum'


listed = {}; vocab = collections.Counter()
for f in sorted(os.listdir(common.NAMES_DIR)):
    if f.endswith('.txt'):
        names = open(os.path.join(common.NAMES_DIR, f), encoding='utf-8', errors='replace').read().split()
        for n in names:
            for w in TOK.findall(n):
                if len(w) >= 3: vocab[w.lower()] += 1
            h = joaat_cs(n)
            if h in T: listed.setdefault(h, n)
print('names folder resolves', len(listed), 'of', len(T))


def plain(n):
    t = TOK.findall(n)
    if ''.join(t) != n: return False
    words = [w for w in t if w[0].isalpha()]
    long_words = [w for w in words if len(w) >= 3]
    if not long_words or any(len(w) < 2 for w in words) or any(vocab[w.lower()] < 3 for w in long_words): return False
    return len(long_words) >= 2 or len(long_words[0]) >= 5


extra = {}; dropped = 0
lp = os.path.join(W, 'list_sources.pkl')
for src, names in (pickle.load(open(lp, 'rb')).items() if os.path.exists(lp) else ()):
    strict = not src.startswith('parser-dumps/')
    got = 0
    for n in names:
        h = joaat_cs(n)
        if h in T and h not in listed and h not in extra:
            if strict and not plain(n): dropped += 1; continue
            extra[h] = n; got += 1
    print('%-36s %7d names -> %5d new (about %.1f chance hits before the word check)' % (src, len(names), got, len(names) * (len(T) - len(listed)) / 2 ** 32))
tot = collections.Counter(kind(r) for r in T.values()); have = collections.Counter(kind(T[h]) for h in list(listed) + list(extra))
print('resolved by lists %d of %d: %s | dropped by the word check %d' % (len(listed) + len(extra), len(T), {k: '%d/%d' % (have[k], tot[k]) for k in tot}, dropped))
if '--save' in sys.argv:
    p = os.path.join(common.NAMES_DIR, 'other-sources.txt')
    cur = set(open(p, encoding='utf-8').read().split()) if os.path.exists(p) else set()
    cur.update(extra.values())
    open(p, 'w', encoding='utf-8').write('\n'.join(sorted(cur)))
    print('other-sources.txt now', len(cur), 'names')
