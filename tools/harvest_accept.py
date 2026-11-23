"""Sorts what harvest.py found into real names and chance matches.

A scan of the whole game tests hundreds of millions of tokens, so a few hundred hit an unresolved hash by chance.
Those are scraps of binary data; a real name is made of words that other names already use. A hit is kept when it
splits into such words; one unfamiliar word is allowed when several hits share it. Names listed in
<work>/crack/harvest_reviewed.txt are kept as well: that is where a reader puts the real ones the rule dropped.
Kept names are printed and, with --save, added to recovered.txt in the names folder; run prep.py afterwards.
usage: python harvest_accept.py [--save]"""
import os, re, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

W = common.WORK
T = pickle.load(open(os.path.join(W, 'targets.pkl'), 'rb'))
known = pickle.load(open(os.path.join(common.CRACK, 'known.pkl'), 'rb'))
ap = os.path.join(common.CRACK, 'accepted.pkl')
if os.path.exists(ap): known.update(pickle.load(open(ap, 'rb')))
TOK = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+|_+')


def split(n):
    t = TOK.findall(n)
    return t if ''.join(t) == n else None


# words of every name at hand, resolved or only listed
vocab = collections.Counter()
names = list(known.values())
for f in os.listdir(common.NAMES_DIR):
    if f.endswith('.txt'): names += open(os.path.join(common.NAMES_DIR, f), encoding='utf-8', errors='replace').read().split()
for n in names:
    for w in split(n) or ():
        if len(w) >= 2: vocab[w.lower()] += 1


def strange(n):
    """words of the name that no known name uses, None when it does not read as a name at all"""
    t = split(n)
    if not t: return None
    words = [w for w in t if w[0].isalpha()]
    # asset names (lower case with numbers) are too many to tell from chance, short scraps are no words
    if not any(len(w) >= 3 for w in words) or any(len(w) < 2 or (len(w) == 2 and vocab[w.lower()] < 50) for w in words): return None
    if n == n.lower() and any(c.isdigit() for c in n): return None
    return [w for w in words if len(w) >= 3 and vocab[w.lower()] < 3]


hits = {}; where = collections.defaultdict(set); tested = 0
D = os.path.join(W, 'harvest2')
for f in os.listdir(D):
    r = pickle.load(open(os.path.join(D, f), 'rb'))
    tested += r['tested']
    for h, n in r['hits'].items():
        if h in T and h not in known and common.joaat_cs(n) == h:
            hits[h] = n; where[n].add(r['file'])
# a word no known name uses is allowed when several hits share it, like a common prefix
shared = collections.Counter(w for n in hits.values() for w in set(strange(n) or ()))
# names a person accepted after reading the dropped list
rp = os.path.join(common.CRACK, 'harvest_reviewed.txt')
reviewed = set(open(rp, encoding='utf-8').read().split()) if os.path.exists(rp) else set()
keep = {h: n for h, n in hits.items() if n in reviewed}
for h, n in hits.items():
    odd = strange(n)
    if odd is None: continue
    long_words = [w for w in split(n) if w[0].isalpha() and len(w) >= 3]
    if not odd and (len(long_words) >= 2 or len(long_words[0]) >= 4): keep[h] = n
    elif len(odd) == 1 and shared[odd[0]] >= 2 and len(long_words) >= 2: keep[h] = n
print('%d tokens tested, %d unresolved hashes hit, about %.0f expected by chance; kept %d' % (tested, len(hits), tested * (len(T) - len(known)) / 2 ** 32, len(keep)))
for n in sorted(keep.values()): print('  %-44s %s' % (n, ', '.join(sorted(where[n]))[:70]))
print('dropped:', ' '.join(sorted(n for h, n in hits.items() if h not in keep)[:200]))
if '--save' in sys.argv:
    p = os.path.join(common.NAMES_DIR, 'recovered.txt')
    cur = set(open(p, encoding='utf-8').read().split()) if os.path.exists(p) else set()
    cur.update(keep.values())
    open(p, 'w', encoding='utf-8').write('\n'.join(sorted(cur)))
    print('recovered.txt now', len(cur), 'names')
