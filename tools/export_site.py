"""Writes the published results: data/names.tsv (every recovered name) and data/progress.json (the figures the page shows)."""
import os, sys, pickle, json, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK; UP = common.WORK
OUT = common.SITE_DATA
T = pickle.load(open(os.path.join(UP, 'targets.pkl'), 'rb'))
known = pickle.load(open(os.path.join(HERE, 'known.pkl'), 'rb')); acc = pickle.load(open(os.path.join(HERE, 'accepted.pkl'), 'rb'))
names = dict(known); names.update(acc)
names = {h: n for h, n in names.items() if h in T}
xp = os.path.join(UP, 'exe_only.pkl')
exe_only = pickle.load(open(xp, 'rb')) if os.path.exists(xp) else set()

# names that exist as text somewhere: public lists, and the game's own files
listed = set()
lp = os.path.join(UP, 'list_sources.pkl')
if os.path.exists(lp):
    for v in pickle.load(open(lp, 'rb')).values(): listed |= set(v)
for f in ('rage-parser-dictionary.txt', 'other-sources.txt'):
    p = os.path.join(common.NAMES_DIR, f)
    if os.path.exists(p): listed |= set(open(p, encoding='utf-8', errors='replace').read().split())
dump = set()
hp = os.path.join(UP, 'hit_cs.pkl')
if os.path.exists(hp): dump |= set(pickle.load(open(hp, 'rb')).values())
hd = os.path.join(UP, 'harvest2')
for f in os.listdir(hd) if os.path.isdir(hd) else []:
    dump |= set(pickle.load(open(os.path.join(hd, f), 'rb'))['hits'].values())
judged = set()
for d in ('judge', 'judge_done'):
    dd = os.path.join(HERE, d)
    for f in os.listdir(dd) if os.path.isdir(dd) else []:
        if f.endswith('.out'):
            for l in open(os.path.join(dd, f), encoding='utf-8', errors='replace'):
                p = l.split()
                if len(p) == 2: judged.add(p[1])


def kind(h):
    r = T[h]
    return 'field' if 'field' in r else 'struct' if 'struct' in r else 'enum value' if 'enumval' in r else 'enum'


def method(h, n):
    if n in listed: return 'name list'
    if n in dump: return 'game text'
    if n in judged and h in acc: return 'judged'
    return 'cracked'


rows = sorted(((n, h, kind(h), method(h, n)) for h, n in names.items()), key=lambda r: r[0].lower())
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'names.tsv'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('hash\tname\tkind\tmethod\n')
    for n, h, k, m in rows: f.write('%08x\t%s\t%s\t%s\n' % (h, n, k, m))
tot = collections.Counter(kind(h) for h in T); have = collections.Counter(r[2] for r in rows); meth = collections.Counter(r[3] for r in rows)
in_files = set(T) - exe_only
prog = {
    'updated': datetime.date.today().isoformat(),
    'scope': 'every struct, field and enum name known to the game\'s metadata parser (GTA VI, Xbox build 1.0.2.1)',
    'total': len(T), 'resolved': len(rows),
    'by_kind': [{'kind': k, 'resolved': have[k], 'total': tot[k]} for k in ('field', 'enum value', 'struct', 'enum')],
    'by_method': [{'method': m, 'count': meth[m]} for m in ('name list', 'game text', 'cracked', 'judged')],
    'by_origin': [
        {'origin': 'Names used in the scanned data files', 'resolved': sum(1 for n, h, k, m in rows if h in in_files), 'total': len(in_files)},
        {'origin': 'Names found only in the executable\'s tables', 'resolved': sum(1 for n, h, k, m in rows if h in exe_only), 'total': len(exe_only)},
    ],
    'accuracy': [
        {'method': 'name list, game text', 'note': 'The exact text exists elsewhere, and about one such name in 4,000 is expected to be a chance collision. The largest loose sources are filtered to names built from words that parser names use.'},
        {'method': 'cracked', 'note': 'Accepted automatically where random decoy hashes show few chance matches. The decoy counts put chance matches at about 3 to 4% of these names. In a holdout test the cracker accepted 520 hidden known names: 518 right, 2 wrong.'},
        {'method': 'judged', 'note': 'Picked by a language model from candidates that hash correctly. In holdout tests on 825 hidden known names, mixed with as many unknown ones, Claude Opus 5.5 accepted 167 (all right) and Claude Fable 5.2 accepted 197 (196 right, 1 wrong). Scaled to the lines judged for real, that suggests 1 to 2% of judged names are wrong, with a wide margin. The hidden names come from earlier games and may be easier than the unknown ones.'},
    ],
}
json.dump(prog, open(os.path.join(OUT, 'progress.json'), 'w', encoding='utf-8'), indent=2)
print(len(rows), 'of', len(T), dict(have), dict(meth), [(o['resolved'], o['total']) for o in prog['by_origin']])
