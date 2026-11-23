"""After a judging round: fold accepted names into the known set, relearn the word lists, run the cracker again and build new judge files.
usage: python next_round.py <round tag> <judge tag>"""
import os, sys, pickle, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
tag, jtag = sys.argv[1], sys.argv[2]
py = sys.executable


def joaat_cs(s):
    h = 0
    for c in s.encode('latin-1', 'replace'):
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; h = (h + (h << 15)) & 0xffffffff
    return h


acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
extra = os.path.join(HERE, 'accepted_names.txt')
open(extra, 'w', encoding='utf-8').write('\n'.join(sorted(acc.values())))
# keep earlier judge files out of the way so their candidates are not offered twice
old = os.path.join(HERE, 'judge_done'); os.makedirs(old, exist_ok=True)
for f in os.listdir(os.path.join(HERE, 'judge')):
    shutil.move(os.path.join(HERE, 'judge', f), os.path.join(old, f))
subprocess.run([py, os.path.join(common.TOOLS, 'prep.py'), extra], check=True)
subprocess.run([py, os.path.join(common.TOOLS, 'run_all.py'), tag], check=True)
# automatic picks of this round
T = set(int(l, 16) for l in open(os.path.join(HERE, 'in', 'all_targets.txt')))
n = 0
for name in open(os.path.join(HERE, 'cracked_%s.txt' % tag), encoding='utf-8').read().split():
    h = joaat_cs(name)
    if h in T and h not in acc: acc[h] = name; n += 1
pickle.dump(acc, open(os.path.join(HERE, 'accepted.pkl'), 'wb'))
print('automatic picks added', n, 'accepted now', len(acc))
outs = [os.path.join(HERE, 'out', f) for f in os.listdir(os.path.join(HERE, 'out')) if f.startswith(tag + '_')]
subprocess.run([py, os.path.join(common.TOOLS, 'pool.py'), jtag, '420'] + outs, check=True)
