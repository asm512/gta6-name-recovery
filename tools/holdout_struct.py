"""HOLDOUT TEST of the per-struct search (known names hidden and searched for).
Per-struct search: every unresolved field of a struct is tried against combinations of that struct's own words,
optional extra words suggested for it, and a short list of globally common words.
usage: python holdout_struct.py <tag> [extra words file ...]   extra files hold lines "S<idx>: word word ..."."""
import os, sys, re, pickle, subprocess, collections, shutil
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
tag = sys.argv[1]
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
known.update(pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb')))
owners, members, samples, enum_of, enum_vals = pickle.load(open(os.path.join(HERE, 'index.pkl'), 'rb'))
index = pickle.load(open(os.path.join(HERE, 'sp_index.pkl'), 'rb'))
extra = collections.defaultdict(list)
for f in sys.argv[2:]:
    for line in open(f, encoding='utf-8', errors='replace'):
        m = re.match(r'\s*S(\d+)\s*[:|]\s*(.*)', line)
        if m:
            extra[int(m.group(1))] += [w for w in re.findall(r'[A-Za-z]{2,24}', m.group(2))]
only_extra = bool(sys.argv[2:])
WORD = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+')
gc = collections.Counter()
for n in known.values():
    for w in WORD.findall(n):
        if len(w) >= 2: gc[w.capitalize()] += 1
G = [w for w, _ in gc.most_common(300)]
PREFIXES = ['f', 'b', 'i', 'n', 'u', 'v', 's', 'e', 'p', 'a', 'str', 'vec', 'm_']
work = os.path.join(HERE, 'sjobs', tag)
shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
all_targets = open(os.path.join(HERE, 'in', 'all_targets.txt')).read()
open(os.path.join(work, 'all_targets.txt'), 'w').write(all_targets)
import random as _r
_r.seed(11)
truth = {}
jobs = []
cands = [(i, s) for i, s in index.items() if sum(1 for h in members[s] if h in known) >= 6]
_r.shuffle(cands)
for i, s in cands[:330]:
    fields = members[s]
    kn = [h for h in fields if h in known]
    if len(kn) < 5: continue
    hidden = set(_r.sample(kn, max(2, len(kn) * 2 // 5)))
    for h in hidden: truth[h] = known[h]
    known = {h: n for h, n in known.items() if h not in hidden}
    unk = list(hidden)
    names = [known[h] for h in fields if h in known] + ([known[s]] if s in known else [])
    lc = collections.Counter()
    for n in names:
        for w in WORD.findall(n):
            if len(w) >= 2: lc[w.capitalize()] += 1
    L = [w for w, _ in lc.most_common(60)]
    E = [w.capitalize() for w in extra.get(i, [])][:80]
    words = list(dict.fromkeys(L[:12] + E + L[12:] + G))
    fn = [n for n in (known[h] for h in fields if h in known)]
    hung = sum(1 for n in fn if len(n) > 1 and n[0].islower() and n[1].isupper()) + sum(1 for n in fn if n.startswith(('str', 'vec', 'm_')))
    camel = sum(1 for n in fn if n[0].islower()) - hung
    pascal = sum(1 for n in fn if n[0].isupper())
    tot = max(len(fn), 1)
    first = []
    if hung / tot >= 0.2: first += PREFIXES
    if pascal / tot >= 0.2 or not fn: first += words
    if camel / tot >= 0.2: first += [w.lower() for w in words]
    if not first: first = words
    c = 's%d' % i
    open(os.path.join(work, 'targets_%s.txt' % c), 'w').write('\n'.join('%08x' % h for h in unk))
    open(os.path.join(work, 'first_%s.txt' % c), 'w').write('\n'.join(first))
    open(os.path.join(work, 'mid_%s.txt' % c), 'w').write('\n'.join(words))
    open(os.path.join(work, 'last_%s.txt' % c), 'w').write('\n'.join(words + ['s', 'X', 'Y', 'Z']))
    jobs.append(c)


def run(c):
    with open(os.path.join(work, 'out_%s.txt' % c), 'w', encoding='utf-8') as fo:
        subprocess.run([common.CRACK_EXE, work, c, '2', '1e12', '4e6', '1.5e6'], stdout=fo, stderr=subprocess.DEVNULL)


with ThreadPoolExecutor(9) as ex:
    list(ex.map(run, jobs))
H = collections.defaultdict(dict); D = collections.defaultdict(list)
for c in jobs:
    for l in open(os.path.join(work, 'out_%s.txt' % c), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'H':
            ln, s, h = int(p[1]), int(p[2]), int(p[3], 16)
            if h not in H[ln] or (s, p[4]) < H[ln][h]: H[ln][h] = (s, p[4])
        elif p[0] == 'D': D[int(p[1])].append(int(p[2]))
acc = {}; noise_total = 0.0
for ln in sorted(H):
    hits = sorted(H[ln].items(), key=lambda kv: kv[1]); dec = sorted(D[ln])
    best = 0; prev_t = prev_d = 0; cut = 10.0
    while cut <= 1e13:
        t = sum(1 for _, v in hits if v[0] <= cut); dd = sum(1 for s in dec if s <= cut) / 4.0
        mt, md = t - prev_t, dd - prev_d
        if t > 0 and t >= 10 * dd and mt >= 4 * md: best = cut
        elif md >= 2 and mt < 4 * md: break
        prev_t, prev_d = t, dd; cut *= 10 ** (1 / 3)
    keep = [(h, v[1]) for h, v in hits if v[0] <= best]
    nz = sum(1 for s in dec if s <= best) / 4.0
    print('len %d: %d hits, %.1f chance; accepted %d up to score %.0e (chance %.1f)' % (ln, len(hits), len(dec) / 4, len(keep), best, nz), flush=True)
    for h, n in keep: acc.setdefault(h, n)
    noise_total += nz
right = sum(1 for h, n in acc.items() if truth.get(h) == n); wrong = len(acc) - right
print('HOLDOUT: %d hidden names searched; accepted %d: %d right, %d wrong (%.1f%% wrong); recall %.1f%%; wrong accepts per 1000 names searched: %.1f' % (
    len(truth), len(acc), right, wrong, 100.0 * wrong / max(len(acc), 1), 100.0 * right / max(len(truth), 1), 1000.0 * wrong / max(len(truth), 1)))
print('wrong examples:', [(truth[h], n) for h, n in acc.items() if truth.get(h) != n][:25])
for ln in sorted(H):
    for cut in (1e3, 1e4, 1e5, 1e6, 1e7):
        hs = [(h, v) for h, v in H[ln].items() if v[0] <= cut]
        r = sum(1 for h, v in hs if truth.get(h) == v[1])
        print('  len %d score<=%.0e: %d candidates, %d right, %d wrong' % (ln, cut, len(hs), r, len(hs) - r))
pickle.dump((acc, truth), open(os.path.join(HERE, 'holdout_%s.pkl' % tag), 'wb'))
raise SystemExit
# everything found, for judging what the automatic cut left out
with open(os.path.join(HERE, 'out', 'sjob_%s.txt' % tag), 'w', encoding='utf-8') as fo:
    for c in jobs:
        fo.write(open(os.path.join(work, 'out_%s.txt' % c), encoding='utf-8').read())
print('STRUCT SEARCH %s: %d structs -> %d names (chance ~%.1f)' % (tag, len(jobs), len(acc), noise_total))
import random
random.seed(2); v = sorted(acc.values()); print(random.sample(v, min(70, len(v))))
