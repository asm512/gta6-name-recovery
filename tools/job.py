"""Domain job: exhaustive word combinations from a hand-ranked vocabulary against the unresolved names of chosen structs.
usage: python job.py <job name> <vocab file> <psin file or - for all extracted files> [struct hash ...]
The vocabulary file lists words most likely first. Accepted names are appended to guess_hits.pkl."""
import os, sys, pickle, subprocess, collections, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
from psin_format import load
job, vocab_file, src = sys.argv[1], sys.argv[2], sys.argv[3]
only = set(int(x, 16) for x in sys.argv[4:])
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
gp = os.path.join(HERE, 'guess_hits.pkl')
guessed = pickle.load(open(gp, 'rb')) if os.path.exists(gp) else {}
known.update(guessed)
_ap = os.path.join(HERE, 'accepted.pkl')
if os.path.exists(_ap): known.update(pickle.load(open(_ap, 'rb')))
files = [src] if src != '-' else [os.path.join(common.PSIN_FILES, f) for f in os.listdir(os.path.join(common.PSIN_FILES)) if not f.endswith('.part.psin')]
targets = set()
for f in files:
    try: ch, payload, insts, structs = load(f)
    except Exception: continue
    for h, (size, fs) in structs.items():
        if only and h not in only: continue
        if h > 0xffff and h not in known: targets.add(h)
        targets.update(nh for nh, off, tr, ref in fs if nh != 0x100 and nh not in known)
words = []
for line in open(vocab_file, encoding='utf-8'):
    for w in line.replace(',', ' ').split():
        if w not in words: words.append(w)
cap = [w[0].upper() + w[1:] for w in words]
cap = list(dict.fromkeys(cap))
prefixes = ['f', 'b', 'n', 'i', 'vec', 'v', 's', 'str', 'u', 'e', 'p', 'm_', 'a', 'd']
low = [w[0].lower() + w[1:] for w in cap]
first = []
# interleave so the rank reflects likelihood: a few top words, then prefixes, then the rest
first += cap[:40] + prefixes + cap[40:] + [w for w in low if w not in cap]
d = os.path.join(HERE, 'jobs', job); os.makedirs(d, exist_ok=True)
open(os.path.join(d, 'targets_%s.txt' % job), 'w').write('\n'.join('%08x' % h for h in sorted(targets)))
open(os.path.join(d, 'all_targets.txt'), 'w').write(open(os.path.join(HERE, 'in', 'all_targets.txt')).read())
for nm, lst in (('first', first), ('mid', cap), ('last', cap + ['s', 'X', 'Y', 'Z', '1', '2', '3'])):
    open(os.path.join(d, '%s_%s.txt' % (nm, job)), 'w', encoding='utf-8').write('\n'.join(lst))
n = len(cap)
bounds = ['1e12', '1e12', '4e6', '0']
out = os.path.join(d, 'out.txt')
with open(out, 'w', encoding='utf-8') as fo:
    subprocess.run([common.CRACK_EXE, d, job, common.THREADS] + bounds, stdout=fo, check=True)
H = collections.defaultdict(dict); D = collections.defaultdict(list)
for l in open(out, encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if p[0] == 'H':
        ln = int(p[1]); s = int(p[2]); h = int(p[3], 16)
        if h not in H[ln] or (s, p[4]) < H[ln][h]: H[ln][h] = (s, p[4])
    elif p[0] == 'D': D[int(p[1])].append(int(p[2]))
acc = {}; noise_total = 0
for ln in sorted(H):
    hits = sorted(H[ln].items(), key=lambda kv: kv[1]); dec = sorted(D[ln])
    best = 0; prev_t = prev_d = 0; cut = 10.0
    while cut <= 1e13:
        t = sum(1 for _, v in hits if v[0] <= cut); dd = sum(1 for s in dec if s <= cut) / 4.0
        mt, md = t - prev_t, dd - prev_d
        if t > 0 and t >= 12 * dd and (mt >= 5 * md):
            best = cut
        elif md >= 1.5 and mt < 5 * md:
            break
        prev_t, prev_d = t, dd; cut *= 10 ** (1 / 3)
    keep = [(h, v[1]) for h, v in hits if v[0] <= best]
    nz = sum(1 for s in dec if s <= best) / 4.0
    print('len %d: %d hits total, %d decoys/4=%.1f; accepted %d up to score %.0e (noise %.1f)' % (ln, len(hits), len(dec), len(dec) / 4, len(keep), best, nz))
    print('    ', [n for _, n in keep][:60])
    for h, n in keep: acc.setdefault(h, n)
    noise_total += nz
print('JOB %s: %d targets, %d words -> %d names (noise ~%.1f)' % (job, len(targets), len(cap), len(acc), noise_total))
guessed.update(acc)
pickle.dump(guessed, open(gp, 'wb'))
