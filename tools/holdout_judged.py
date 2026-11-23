"""Holdout test of the crack-and-judge pipeline: known names are hidden, searched for and judged like unknown ones.

usage: python holdout_judged.py setup [how many names] [seed]   hide names, relearn word lists, run the cracker, write judge files
       python holdout_judged.py score [folder]                  after the judges wrote their .out files: right and wrong accepts
                                                                (folder under <work>/holdout_judged/crack, default judge)

Only names found in name lists or game text are hidden, so the truth is certain. Everything runs in <work>/holdout_judged,
a work folder of its own; the real results are not touched. Judge files hold the hidden names mixed with truly unknown
ones, so the share of lines that have a real candidate stays close to what the judges saw in the real rounds."""
import os, sys, pickle, random, shutil, subprocess, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

REAL = common.WORK
HOLD = os.path.join(REAL, 'holdout_judged')
HC = os.path.join(HOLD, 'crack')


def env():
    e = dict(os.environ)
    e['NAME_RECOVERY_WORK'] = HOLD
    e['NAME_RECOVERY_CRACK_EXE'] = common.CRACK_EXE
    e['NAME_RECOVERY_HIDE'] = os.path.join(HOLD, 'hidden.txt')
    return e


def run(tool, *args):
    subprocess.run([sys.executable, os.path.join(common.TOOLS, tool)] + list(args), check=True, env=env())


def setup(n, seed):
    if os.path.isdir(HOLD): shutil.rmtree(HOLD)
    os.makedirs(HC)
    for f in ('targets.pkl', 'kinds.pkl'): shutil.copy(os.path.join(REAL, f), os.path.join(HOLD, f))
    shutil.copy(os.path.join(common.CRACK, 'index.pkl'), os.path.join(HC, 'index.pkl'))
    T = pickle.load(open(os.path.join(REAL, 'targets.pkl'), 'rb'))
    listed = set()
    for v in pickle.load(open(os.path.join(REAL, 'list_sources.pkl'), 'rb')).values(): listed |= set(v)
    listed |= set(pickle.load(open(os.path.join(REAL, 'hit_cs.pkl'), 'rb')).values())
    sure = sorted(set(nm for nm in listed if common.joaat_cs(nm) in T))
    random.seed(seed)
    hidden = sorted(random.sample(sure, n))
    open(os.path.join(HOLD, 'hidden.txt'), 'w', encoding='utf-8').write('\n'.join(hidden))
    print('hidden', len(hidden), 'of', len(sure), 'names with a certain source', flush=True)
    run('prep.py')
    run('run_all.py', 'h1')
    # names the cracker accepts on its own count as known from here on, as in the real rounds
    truth = {common.joaat_cs(nm): nm for nm in hidden}
    acc = {}
    for nm in open(os.path.join(HC, 'cracked_h1.txt'), encoding='utf-8').read().split(): acc[common.joaat_cs(nm)] = nm
    pickle.dump(acc, open(os.path.join(HC, 'accepted.pkl'), 'wb'))
    outs = [os.path.join(HC, 'out', f) for f in sorted(os.listdir(os.path.join(HC, 'out'))) if f.startswith('h1_')]
    run('pool.py', 'all', '100000', *outs)
    # judge files: every hidden name with candidates, plus as many truly unknown ones, in the order pool.py gave them
    rows = [l for l in open(os.path.join(HC, 'judge', 'all_00.txt'), encoding='utf-8').read().split('\n') if l]
    os.remove(os.path.join(HC, 'judge', 'all_00.txt'))
    hid = [r for r in rows if int(r[:8], 16) in truth]
    rest = [r for r in rows if int(r[:8], 16) not in truth]
    random.seed(seed + 1)
    pick = set(random.sample(range(len(rest)), min(len(rest), len(hid))))
    keep = set(hid) | set(rest[i] for i in pick)
    mixed = [r for r in rows if r in keep]
    per = 400
    for i in range(0, len(mixed), per):
        open(os.path.join(HC, 'judge', 'hold_%02d.txt' % (i // per)), 'w', encoding='utf-8').write('\n'.join(mixed[i:i + per]) + '\n')
    present = sum(1 for r in hid if truth[int(r[:8], 16)] in [c.strip() for c in r.split('candidates: ')[1].split(' ; ')])
    auto_right = sum(1 for h, nm in acc.items() if h in truth and truth[h] == nm)
    auto_wrong = sum(1 for h, nm in acc.items() if h in truth and truth[h] != nm)
    print('cracker alone on hidden names: %d right, %d wrong' % (auto_right, auto_wrong))
    print('judge lines: %d hidden (%d with the true name among the candidates) + %d unknown, in %d files' % (len(hid), present, len(mixed) - len(hid), (len(mixed) + per - 1) // per))


def score():
    hidden = open(os.path.join(HOLD, 'hidden.txt'), encoding='utf-8').read().split()
    truth = {common.joaat_cs(nm): nm for nm in hidden}
    J = os.path.join(HC, sys.argv[2] if len(sys.argv) > 2 else 'judge')
    offered = {}
    for f in sorted(os.listdir(J)):
        if f.endswith('.txt'):
            for l in open(os.path.join(J, f), encoding='utf-8'):
                if 'candidates: ' in l: offered[int(l[:8], 16)] = [c.strip() for c in l.rstrip('\n').split('candidates: ')[1].split(' ; ')]
    c = collections.Counter(); wrong = []
    lines_hidden = [h for h in offered if h in truth]
    with_truth = set(h for h in lines_hidden if truth[h] in offered[h])
    for f in sorted(os.listdir(J)):
        if not f.endswith('.out'): continue
        for l in open(os.path.join(J, f), encoding='utf-8', errors='replace'):
            p = l.split()
            if len(p) != 2: continue
            try: h = int(p[0], 16)
            except ValueError: continue
            if h not in offered or p[1] not in offered[h] or common.joaat_cs(p[1]) != h: c['invalid'] += 1; continue
            if h not in truth: c['accepted unknown'] += 1; continue
            if p[1] == truth[h]: c['right'] += 1
            else:
                c['wrong'] += 1; wrong.append((p[1], truth[h]))
                c['wrong, truth was offered' if h in with_truth else 'wrong, truth not offered'] += 1
    acc = c['right'] + c['wrong']
    no_truth = len(lines_hidden) - len(with_truth)
    res = {
        'hidden': len(truth), 'hidden lines judged': len(lines_hidden), 'lines with the true name offered': len(with_truth),
        'accepted': acc, 'right': c['right'], 'wrong': c['wrong'],
        'wrong share of accepted': round(c['wrong'] / acc, 4) if acc else None,
        'recall where the true name was offered': round(c['right'] / len(with_truth), 4) if with_truth else None,
        'wrong accepts per 1000 lines without the true name': round(1000.0 * c['wrong, truth not offered'] / no_truth, 2) if no_truth else None,
        'unknown lines judged': len(offered) - len(lines_hidden), 'unknown accepted': c['accepted unknown'], 'invalid': c['invalid'],
    }
    for k, v in res.items(): print('%-52s %s' % (k, v))
    for w, t in wrong: print('  wrong: %-40s truth: %s' % (w, t))
    json.dump(res, open(os.path.join(HOLD, 'result_%s.json' % os.path.basename(J)), 'w'), indent=2)


if __name__ == '__main__':
    if sys.argv[1] == 'setup': setup(int(sys.argv[2]) if len(sys.argv) > 2 else 1500, int(sys.argv[3]) if len(sys.argv) > 3 else 7)
    elif sys.argv[1] == 'score': score()
