"""Prepares inputs for the cracker: unresolved targets per name class and position-ranked token lists learned from known names."""
import os, re, pickle, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
UP = common.WORK
T = pickle.load(open(os.path.join(UP, 'targets.pkl'), 'rb'))
kinds, enums = pickle.load(open(os.path.join(UP, 'kinds.pkl'), 'rb'))
NAMES = common.NAMES_DIR
extra = sys.argv[1:]  # extra name files to treat as known


def joaat_cs(s):
    h = 0
    for c in s.encode('latin-1', 'replace'):
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; h = (h + (h << 15)) & 0xffffffff
    return h


known = {}
all_names = []
# holdout tests: names listed in this file are treated as unknown
_hp = os.environ.get('NAME_RECOVERY_HIDE')
hide = set(open(_hp, encoding='utf-8').read().split()) if _hp else set()
for f in ['recovered.txt', 'other-sources.txt', 'rage-parser-dictionary.txt', 'built.txt', 'cracked.txt', 'guessed.txt'] + extra:
    p = f if os.path.isabs(f) else os.path.join(NAMES, f)
    if not os.path.exists(p): continue
    for line in open(p, encoding='utf-8', errors='replace'):
        n = line.strip()
        if not n or n in hide: continue
        all_names.append(n)
        h = joaat_cs(n)
        if h in T: known.setdefault(h, n)
print('known', len(known), 'of', len(T))

CLASS = [('bool', {0x01}), ('float', {0x20, 0x21}), ('int', {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17}), ('vec', {0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36}),
         ('text', {0x42, 0x44, 0x4a, 0x4b, 0x4d, 0x08, 0x4f, 0x0c, 0x40}), ('enum', {0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x68}),
         ('array', {0x50, 0x52, 0x53, 0x5c, 0x71, 0x73, 0x75, 0x76, 0x77}), ('struct', {0x05}), ('ptr', {0x07})]


def field_class(h):
    ks = kinds.get(h, set())
    cs = [name for name, s in CLASS if ks & s]
    return cs[0] if len(cs) == 1 else 'mixed'


def name_class(h):
    r = T[h]
    if 'field' in r: return 'f_' + field_class(h)
    if 'struct' in r: return 'structname'
    if 'enumval' in r: return 'enumval'
    return 'enumname'


TOK = re.compile(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+|_+')


def tokens(n):
    t = TOK.findall(n)
    return t if ''.join(t) == n else None


cls_targets = collections.defaultdict(list)
first = collections.defaultdict(collections.Counter); mid = collections.defaultdict(collections.Counter); last = collections.defaultdict(collections.Counter)
lens = collections.defaultdict(collections.Counter)
for h in T:
    c = name_class(h)
    if h in known:
        t = tokens(known[h])
        if not t: continue
        lens[c][len(t)] += 1
        if len(t) == 1:
            first[c][t[0]] += 1; last[c][t[0]] += 1
        else:
            first[c][t[0]] += 1; last[c][t[-1]] += 1
            for m in t[1:-1]: mid[c][m] += 1
            # words anywhere inform the middle list a little
            for m in t: mid[c][m] += 0.25
    else:
        cls_targets[c].append(h)
# background vocabulary from every listed name: fills the tails of each list
bg = collections.Counter()
for n in all_names:
    t = tokens(n)
    if t:
        for w in t:
            if len(w) >= 2 or w == '_': bg[w] += 1
bg_cap = collections.Counter()
for w, c in bg.items():
    if w[0].isalpha(): bg_cap[w.capitalize()] += c
out = os.path.join(HERE, 'in'); os.makedirs(out, exist_ok=True)
for c in sorted(cls_targets):
    open(os.path.join(out, 'targets_%s.txt' % c), 'w').write('\n'.join('%08x' % h for h in sorted(cls_targets[c])))
    for nm, cnt in (('first', first[c]), ('mid', mid[c]), ('last', last[c])):
        ranked = [w for w, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
        seen = set(ranked)
        # tail: background words, capitalised for mid/last, as written for first
        tail_src = bg if nm == 'first' else bg_cap
        ranked += [w for w, _ in tail_src.most_common(12000) if w not in seen]
        open(os.path.join(out, '%s_%s.txt' % (nm, c)), 'w', encoding='utf-8').write('\n'.join(ranked))
    print('%-14s unresolved %5d  known %5d  lens %s  first %d mid %d last %d' % (c, len(cls_targets[c]), sum(lens[c].values()), dict(sorted(lens[c].items())[:8]), len(first[c]), len(mid[c]), len(last[c])))
open(os.path.join(out, 'all_targets.txt'), 'w').write('\n'.join('%08x' % h for h in sorted(T)))
pickle.dump(known, open(os.path.join(HERE, 'known.pkl'), 'wb'))
