"""Runs harvest.py over every file of the game folder, several pieces at a time, and writes a status file the progress page reads."""
import os, sys, subprocess, time, math, json
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.WORK
ROOT = common.game_dir()
jobs = []


def add(name, mode, step, start=0.0):
    size = os.path.getsize(os.path.join(ROOT, name)) / 2 ** 30
    g = start
    while g < size:
        jobs.append((name, g, min(size, g + step), mode)); g += step


# every file of the game folder, once as compressed streams and once as plain bytes
for dp, dn, fn in os.walk(ROOT):
    for n in sorted(fn):
        rel = os.path.relpath(os.path.join(dp, n), ROOT)
        if os.path.getsize(os.path.join(ROOT, rel)) > 4096:
            add(rel, 'z', 6.0); add(rel, 'raw', 8.0)
done = [0]
status = os.path.join(HERE, 'crack', 'harvest_status.json')


def run(j):
    r = subprocess.run([sys.executable, os.path.join(common.TOOLS, 'harvest.py'), j[0], '%g' % j[1], '%g' % j[2], j[3]], capture_output=True, text=True)
    done[0] += 1
    json.dump({'done': done[0], 'total': len(jobs), 't': time.time()}, open(status, 'w'))
    line = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
    print(line, flush=True)


json.dump({'done': 0, 'total': len(jobs), 't': time.time()}, open(status, 'w'))
print('pieces', len(jobs), flush=True)
with ThreadPoolExecutor(8) as ex:
    list(ex.map(run, jobs))
print('ALL DONE')
