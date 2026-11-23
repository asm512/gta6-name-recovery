"""Runs the cracker for every name class and keeps hits below the score where chance matches start to dominate."""
import os, subprocess, collections, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
IN = os.path.join(HERE, 'in'); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
tag = sys.argv[1] if len(sys.argv) > 1 else 'r1'
bounds = ['1e9', '1e8', '2e7', '2e6']  # lengths 2..5
classes = sorted(f[len('targets_'):-4] for f in os.listdir(IN) if f.startswith('targets_'))
accepted = {}; total_noise = 0.0
for c in classes:
    path = os.path.join(OUT, '%s_%s.txt' % (tag, c))
    with open(path, 'w', encoding='utf-8') as fo:
        subprocess.run([common.CRACK_EXE, IN, c, common.THREADS] + bounds, stdout=fo, stderr=subprocess.DEVNULL, check=True)
    H = collections.defaultdict(dict); D = collections.defaultdict(list)
    for l in open(path, encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'H':
            n = int(p[1]); s = int(p[2]); h = int(p[3], 16)
            if h not in H[n] or (s, p[4]) < H[n][h]: H[n][h] = (s, p[4])
        elif p[0] == 'D':
            D[int(p[1])].append(int(p[2]))
    got = 0; cn = 0.0
    for n in sorted(H):
        hits = sorted(H[n].items(), key=lambda kv: kv[1])
        dec = sorted(D[n])
        # walk score cuts in third-decade steps, keep the last cut where both the running and the marginal precision hold
        best = 0; prev_t = prev_d = 0
        cut = 10.0
        while cut <= 1e9:
            t = sum(1 for _, v in hits if v[0] <= cut); d = sum(1 for s in dec if s <= cut) / 4.0
            mt, md = t - prev_t, d - prev_d
            ok_total = t >= 12 * d and t > 0
            ok_marginal = (mt >= 5 * md) if (mt or md) else True
            if ok_total and ok_marginal:
                best = cut
            elif not ok_marginal and md >= 2:
                break
            prev_t, prev_d = t, d
            cut *= 10 ** (1 / 3)
        if best:
            keep = [(h, v[1]) for h, v in hits if v[0] <= best]
            noise = sum(1 for s in dec if s <= best) / 4.0
            for h, name in keep:
                if h not in accepted: accepted[h] = name; got += 1
            cn += noise
    total_noise += cn
    print('%-14s accepted %4d (noise ~%.1f)' % (c, got, cn), flush=True)
open(os.path.join(HERE, 'cracked_%s.txt' % tag), 'w', encoding='utf-8').write('\n'.join(sorted(accepted.values())))
print('TOTAL accepted', len(accepted), 'noise ~%.1f' % total_noise)
import random
random.seed(3); v = sorted(accepted.values()); print(random.sample(v, min(80, len(v))))
