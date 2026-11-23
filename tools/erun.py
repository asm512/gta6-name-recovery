"""Per-enum search: the unresolved values of an enum are tried as the prefix its known values share, followed by
combinations of the words those values use and of words common in enum values overall.
usage: python erun.py <tag>
Hits and decoy scores of every enum go to <work>/crack/out/ejob_<tag>.txt for pool.py; what passes the decoy
cut on its own is kept in ehits_<tag>.pkl."""
import os, sys, re, pickle, subprocess, collections, shutil
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
tag = sys.argv[1]
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
known.update(pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb')))
owners, members, samples, enum_of, enum_vals = pickle.load(open(os.path.join(HERE, 'index.pkl'), 'rb'))
WORD = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+')
CAPS = re.compile(r'^[A-Z0-9_]+$')


def prefix(names):
    """longest start shared by nearly all names, cut back to a word boundary"""
    if len(names) < 2: return ''
    best = ''
    first = sorted(names)[0]
    for end in range(len(first), 1, -1):
        p = first[:end]
        if sum(1 for n in names if n.startswith(p)) >= max(2, 0.8 * len(names)):
            best = p; break
    if not best: return ''
    # stop at an underscore or before a capital, never inside a word
    for end in range(len(best), 0, -1):
        rest_ok = all(len(n) > end for n in names if n.startswith(best[:end]))
        if rest_ok and (best[end - 1] == '_' or all(n[end].isupper() or n[end].isdigit() for n in names if n.startswith(best[:end]))):
            return best[:end]
    return ''


# words of enum values overall, by style
glob_caps = collections.Counter(); glob_camel = collections.Counter()
for vh, es in enum_of.items():
    n = known.get(vh)
    if not n: continue
    for w in WORD.findall(n):
        if len(w) < 2: continue
        (glob_caps if CAPS.match(n) else glob_camel)[w.upper() if CAPS.match(n) else w.capitalize()] += 1
GC = [w for w, _ in glob_caps.most_common(1500)]; GM = [w for w, _ in glob_camel.most_common(1500)]
work = os.path.join(HERE, 'ejobs', tag)
shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
open(os.path.join(work, 'all_targets.txt'), 'w').write(open(os.path.join(HERE, 'in', 'all_targets.txt')).read())
jobs = []; styles = collections.Counter()
for e, vals in enum_vals.items():
    unk = [h for h in vals if h not in known and h > 0xffff]
    names = [known[h] for h in vals if h in known]
    if not unk or len(names) < 2: continue
    caps = sum(1 for n in names if CAPS.match(n)) * 2 >= len(names)
    pre = prefix(names)
    lc = collections.Counter()
    for n in names:
        for w in WORD.findall(n[len(pre):] if n.startswith(pre) else n):
            if len(w) >= 2 or w.isdigit(): lc[w.upper() if caps else w.capitalize()] += 1
    local = [w for w, _ in lc.most_common(400)]
    words = list(dict.fromkeys(local + (GC if caps else GM)))
    if caps:
        mid = [w + '_' for w in words]; last = words + [str(i) for i in range(10)]
    else:
        mid = words; last = words + [str(i) for i in range(10)]
    if pre: first = [pre]
    else: first = mid
    c = 'e%08x' % e
    open(os.path.join(work, 'targets_%s.txt' % c), 'w').write('\n'.join('%08x' % h for h in unk))
    open(os.path.join(work, 'first_%s.txt' % c), 'w', encoding='utf-8').write('\n'.join(first))
    open(os.path.join(work, 'mid_%s.txt' % c), 'w', encoding='utf-8').write('\n'.join(mid))
    open(os.path.join(work, 'last_%s.txt' % c), 'w', encoding='utf-8').write('\n'.join(last))
    jobs.append((c, bool(pre)))
    styles[('caps' if caps else 'camel', 'prefix' if pre else 'no prefix')] += 1
print('enums to search', len(jobs), dict(styles), flush=True)


def run(job):
    c, has_prefix = job
    # with a fixed prefix the first token costs nothing, so the same bounds reach one word further
    bounds = ['1e12', '4e6', '4e6'] if has_prefix else ['1e12', '4e6', '1.5e6']
    with open(os.path.join(work, 'out_%s.txt' % c), 'w', encoding='utf-8') as fo:
        subprocess.run([common.CRACK_EXE, work, c, '2'] + bounds, stdout=fo, stderr=subprocess.DEVNULL)


with ThreadPoolExecutor(max(2, int(common.THREADS) // 2)) as ex:
    list(ex.map(run, jobs))
H = collections.defaultdict(dict); D = collections.defaultdict(list)
with open(os.path.join(HERE, 'out', 'ejob_%s.txt' % tag), 'w', encoding='utf-8') as fo:
    for c, _ in jobs:
        text = open(os.path.join(work, 'out_%s.txt' % c), encoding='utf-8').read()
        fo.write(text)
        for l in text.split('\n'):
            p = l.split('\t')
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
        if t > 0 and t >= 20 * dd and mt >= 8 * md: best = cut
        elif md >= 2 and mt < 8 * md: break
        prev_t, prev_d = t, dd; cut *= 10 ** (1 / 3)
    keep = [(h, v[1]) for h, v in hits if v[0] <= best]
    nz = sum(1 for s in dec if s <= best) / 4.0
    print('len %d: %d hits, %.1f chance; accepted %d up to score %.0e (chance %.1f)' % (ln, len(hits), len(dec) / 4, len(keep), best, nz), flush=True)
    for h, n in keep: acc.setdefault(h, n)
    noise_total += nz
pickle.dump(acc, open(os.path.join(HERE, 'ehits_%s.pkl' % tag), 'wb'))
print('ENUM SEARCH %s: %d enums -> %d names (chance ~%.1f)' % (tag, len(jobs), len(acc), noise_total))
import random
random.seed(2); v = sorted(acc.values()); print(random.sample(v, min(90, len(v))))
