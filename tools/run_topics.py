"""Waits for topic vocabularies and runs a domain job for each one."""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
T = os.path.join(HERE, 'topics')
want = sorted(f[:-4] for f in os.listdir(T) if f.endswith('.txt'))
only = sys.argv[1:]
if only: want = [w for w in want if w in only]
deadline = time.time() + 40 * 60
done = set()
while len(done) < len(want) and time.time() < deadline:
    progressed = False
    for t in want:
        if t in done: continue
        v = os.path.join(T, t + '.vocab')
        if not os.path.exists(v) or time.time() - os.path.getmtime(v) < 5: continue
        src = open(os.path.join(T, t + '.src')).read().strip()
        r = subprocess.run([sys.executable, os.path.join(common.TOOLS, 'job.py'), t, v, src], capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if l.startswith('JOB')]
        print(tail[-1] if tail else ('%s failed: %s' % (t, r.stderr[-300:])), flush=True)
        done.add(t); progressed = True
    if not progressed: time.sleep(15)
print('topics done', len(done), 'of', len(want))
