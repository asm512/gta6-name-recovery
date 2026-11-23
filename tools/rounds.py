"""Runs search and judge cycles unattended until a cycle adds few names or the spending cap is reached.

One cycle: per-enum search, general cracker round, per-struct search; after each, the candidates go to pool.py,
are judged through the Claude API (judge_api.py) and merged. Needs ANTHROPIC_API_KEY in the environment.

usage: python rounds.py <first cycle number> [--min-gain 300] [--max-dollars 50] [--reuse-enum TAG]
  --reuse-enum TAG   start from the output of a per-enum search that is already running or done (waits for it)
Progress goes to <work>/rounds.log and to stage.txt, which progress_page.py shows."""
import os, sys, time, pickle, shutil, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
PY = sys.executable
LOG = os.path.join(common.WORK, 'rounds.log')


def say(text):
    line = '%s  %s' % (time.strftime('%H:%M:%S'), text)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f: f.write(line + '\n')


def stage(text):
    open(os.path.join(HERE, 'stage.txt'), 'w', encoding='utf-8').write(text)
    say(text)


def tool(name, *args):
    with open(LOG, 'a', encoding='utf-8') as f:
        subprocess.run([PY, os.path.join(common.TOOLS, name)] + [str(a) for a in args], check=True, stdout=f, stderr=subprocess.STDOUT)


def resolved():
    known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb'))
    acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
    return len(set(known) | set(acc))


def spent():
    p = os.path.join(HERE, 'judge', 'api_usage.tsv')
    if not os.path.exists(p): return 0.0
    return sum(float(l.split('\t')[5]) for l in open(p, encoding='utf-8') if l.count('\t') >= 5)


def archive():
    """judged files move out of the way; pool.py does not offer their candidates again"""
    done = os.path.join(HERE, 'judge_done'); os.makedirs(done, exist_ok=True)
    J = os.path.join(HERE, 'judge')
    for f in os.listdir(J):
        if f.endswith('.txt') or f.endswith('.out'): shutil.move(os.path.join(J, f), os.path.join(done, f))


def declined():
    """candidates a judge was shown and did not accept"""
    D = os.path.join(HERE, 'judge_done'); shown = set(); taken = set()
    for f in os.listdir(D) if os.path.isdir(D) else ():
        for l in open(os.path.join(D, f), encoding='utf-8', errors='replace'):
            if f.endswith('.txt') and 'candidates:' in l:
                shown.update((l[:8], c.strip()) for c in l.split('candidates:')[1].split(';'))
            elif f.endswith('.out') and '	' in l:
                taken.add(tuple(l.strip().split('	')[:2]))
    return shown - taken


def accept(pickle_name):
    """names a narrow search accepted on its own decoy count, except those a judge has already turned down"""
    hits = pickle.load(open(os.path.join(HERE, pickle_name), 'rb'))
    acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
    no = declined()
    new = {h: n for h, n in hits.items() if h not in acc and ('%08x' % h, n) not in no}
    acc.update(new)
    pickle.dump(acc, open(os.path.join(HERE, 'accepted.pkl'), 'wb'))
    return len(new)


def judge(prefix, what):
    files = [f for f in os.listdir(os.path.join(HERE, 'judge')) if f.startswith(prefix) and f.endswith('.txt')]
    if not files: return
    stage('Judging %s: %d files with Claude Opus 5.5' % (what, len(files)))
    tool('judge_api.py', os.path.join(HERE, 'judge'), prefix, '--workers', 6)
    tool('merge.py', '--save')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('first', type=int)
    ap.add_argument('--min-gain', type=int, default=300); ap.add_argument('--max-dollars', type=float, default=50.0)
    ap.add_argument('--reuse-enum', default='')
    a = ap.parse_args()
    c = a.first; reuse = a.reuse_enum
    while True:
        before = resolved()
        say('CYCLE %d starts with %d names, $%.2f spent on judging so far' % (c, before, spent()))
        # per-enum search
        etag = reuse or 'e%d' % c
        if reuse:
            stage('Per-enum search (%s): waiting for the run in progress' % etag)
            while not os.path.exists(os.path.join(HERE, 'ehits_%s.pkl' % etag)): time.sleep(20)
            reuse = ''
        else:
            stage('Per-enum search (%s): the prefix each enum shares, plus words' % etag)
            tool('erun.py', etag)
        n = accept('ehits_%s.pkl' % etag)
        say('per-enum search accepted %d names on its own' % n)
        archive()
        tool('pool.py', etag, 420, os.path.join(HERE, 'out', 'ejob_%s.txt' % etag))
        judge(etag + '_', 'per-enum candidates')
        # general round: relearn the word lists, crack every kind, pool what is left
        stage('General cracker round r%d: relearning word lists, then every kind of name' % c)
        tool('next_round.py', 'r%d' % c, 'g%d' % c)
        judge('g%d_' % c, 'general round candidates')
        # per-struct search
        stage('Per-struct search (w%d): each struct with the words of its known fields' % c)
        tool('sprep.py', 60)
        tool('srun.py', 'w%d' % c)
        n = accept('shits_w%d.pkl' % c)
        say('per-struct search accepted %d names on its own' % n)
        archive()
        tool('pool.py', 's%d' % c, 420, os.path.join(HERE, 'out', 'sjob_w%d.txt' % c))
        judge('s%d_' % c, 'per-struct candidates')
        archive()
        after = resolved(); cost = spent()
        say('CYCLE %d done: %d names (+%d), $%.2f spent on judging' % (c, after, after - before, cost))
        if after - before < a.min_gain:
            stage('Stopped: the last cycle added %d names, under the limit of %d' % (after - before, a.min_gain)); break
        if cost > a.max_dollars:
            stage('Stopped: $%.2f spent on judging, over the cap of $%.0f' % (cost, a.max_dollars)); break
        c += 1


if __name__ == '__main__':
    main()
