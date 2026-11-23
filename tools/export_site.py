"""Writes data/names.tsv and data/progress.json in the gta6-name-recovery repo from the current accepted set."""
import os, pickle, json, collections, datetime
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK; UP = common.WORK
OUT = common.SITE_DATA
T = pickle.load(open(os.path.join(UP, 'targets.pkl'), 'rb'))
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb')); acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
names = dict(known); names.update(acc)
names = {h: n for h, n in names.items() if h in T}
src = pickle.load(open(os.path.join(UP, 'list_sources.pkl'), 'rb'))
listed = set()
for v in src.values(): listed |= set(v)
dump = set(pickle.load(open(os.path.join(UP, 'hit_cs.pkl'), 'rb')).values())
for f in os.listdir(os.path.join(UP, 'harvest2')) if os.path.isdir(os.path.join(UP, 'harvest2')) else []:
    dump |= set(pickle.load(open(os.path.join(UP, 'harvest2', f), 'rb'))['hits'].values())
rust_built_p = os.path.join(UP, 'rust_out', 'built.txt')
rust_built = set(open(rust_built_p, encoding='utf-8').read().split()) if os.path.exists(rust_built_p) else set()
judged = set()
for d in ('judge', 'judge_done'):
    for f in os.listdir(os.path.join(HERE, d)):
        if f.endswith('.out'):
            for l in open(os.path.join(HERE, d, f), encoding='utf-8', errors='replace'):
                p = l.split()
                if len(p) == 2: judged.add(p[1])


def kind(h):
    r = T[h]
    return 'field' if 'field' in r else 'struct' if 'struct' in r else 'enum value' if 'enumval' in r else 'enum'


def method(h, n):
    if n in listed: return 'name list'
    if n in dump: return 'game text'
    if n in judged: return 'judged'
    if n in rust_built and h not in acc: return 'word combination'
    return 'cracked' if h in acc else 'word combination'


rows = sorted(((n, h, kind(h), method(h, n)) for h, n in names.items()), key=lambda r: r[0].lower())
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'names.tsv'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('hash\tname\tkind\tmethod\n')
    for n, h, k, m in rows: f.write('%08x\t%s\t%s\t%s\n' % (h, n, k, m))
tot = collections.Counter(kind(h) for h in T); have = collections.Counter(r[2] for r in rows); meth = collections.Counter(r[3] for r in rows)
prog = {
    'updated': datetime.date.today().isoformat(),
    'scope': 'Hashed struct, field and enum names in the PSIN metadata of common.rpf, script.rpf, data.rpf, levels.rpf and packs.rpf (GTA VI, Xbox build 1.0.2.1)',
    'total': len(T), 'resolved': len(rows),
    'by_kind': [{'kind': k, 'resolved': have[k], 'total': tot[k]} for k in ('field', 'struct', 'enum value', 'enum')],
    'by_method': [{'method': m, 'count': meth[m]} for m in ('name list', 'game text', 'word combination', 'cracked', 'judged')],
    'history': [
        {'step': 'Lower-cased hashing (the wrong assumption)', 'resolved': 167, 'total': 21492},
        {'step': "Case-sensitive hashing, the game's own strings", 'resolved': 1191, 'total': 21492},
        {'step': 'Public name lists from earlier RAGE games', 'resolved': 7418, 'total': 21492},
        {'step': 'Word combinations with chance-match measurement', 'resolved': 9401, 'total': 21492},
        {'step': 'Crack and judge, round one', 'resolved': 10979, 'total': 21492},
        {'step': 'Crack and judge, round two', 'resolved': 11254, 'total': 21492},
        {'step': 'Topic vocabularies', 'resolved': 11408, 'total': 21492},
        {'step': 'Per-struct search and round three', 'resolved': 11625, 'total': 21492},
        {'step': 'levels.rpf and packs.rpf added (4,794 more names to find), name lists applied', 'resolved': 12747},
        {'step': 'Crack and judge on the wider set, second scan of the game text', 'resolved': len(rows)},
    ],
    'accuracy': [
        {'method': 'name list / game text', 'note': 'The exact text exists elsewhere; a chance collision is about 1 in 200,000 per name.'},
        {'method': 'word combination, cracked', 'note': 'Accepted only where random decoy hashes show few chance matches; measured chance rate of a few percent. In a holdout test the cracker alone accepted 520 of 1,500 hidden known names: 518 right, 2 wrong (0.4%).'},
        {'method': 'per-struct search', 'note': 'Holdout test on 1,260 hidden known names: 468 accepted, 458 right, 10 wrong (2.1%). On truly unknown names the same cut is estimated to be wrong about 8% of the time before judging; every such pick was then checked by a judge.'},
        {'method': 'judged', 'note': 'Picked by a language model from candidates that hash correctly. Holdout test: 1,500 known names were hidden and sent through the same cracker and judges, mixed with as many truly unknown ones. The judges accepted 196 hidden names: 195 right, 1 wrong (0.5%); where the true name was among the candidates they found it 80% of the time. The one wrong pick came from 580 lines that had no true candidate; scaled to the lines judged in the real rounds that is about 2% of the judged names, and one event leaves a wide range (well under 1% to about 11%). The hidden names come from older games and may be easier than the unknown ones.'},
    ],
}
json.dump(prog, open(os.path.join(OUT, 'progress.json'), 'w', encoding='utf-8'), indent=2)
print(len(rows), dict(have), dict(meth))
