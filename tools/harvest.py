"""Scans part of a game file for text whose case-sensitive joaat is a still-unresolved name hash.
usage: python harvest.py <file relative to the game folder> <start GiB> <end GiB> <z|raw>
z   = inflate every zlib stream and test every identifier-like token (3+ chars)
raw = test identifier-like tokens straight from the bytes; only long ones (8+ chars) with a case change or underscore,
      since short runs in binary data are noise"""
import os, re, sys, zlib, pickle, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.WORK
ROOT = common.game_dir()
name, g0, g1, mode = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
T = set(int(l, 16) for l in open(os.path.join(HERE, 'crack', 'in', 'all_targets.txt')))
known = pickle.load(open(os.path.join(HERE, 'crack', 'known.pkl'), 'rb')); known.update(pickle.load(open(os.path.join(HERE, 'crack', 'accepted.pkl'), 'rb')))
WANT = T - set(known)


def joaat_cs(b):
    h = 0
    for c in b:
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; h = (h + (h << 15)) & 0xffffffff
    return h


RZ = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,63}')
RR = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{7,63}')
SHAPE = re.compile(rb'[a-z][A-Z]|[A-Za-z]_[A-Za-z]')
path = os.path.join(ROOT, name)
size = os.path.getsize(path)
lo = int(g0 * 2 ** 30); hi = min(size, int(g1 * 2 ** 30))
f = open(path, 'rb'); seen = set(); hits = {}; tested = 0
BLK = 32 << 20; off = lo - (lo % 16); t0 = time.time()
while off < hi:
    f.seek(off); d = f.read(BLK + (4 << 20)); lim = min(len(d), BLK)
    if mode == 'z':
        for m in re.finditer(rb'\x78[\x9c\xda\x01\x5e]', d[:lim]):
            i = m.start()
            if (off + i) & 0xf: continue
            try: o = zlib.decompressobj().decompress(d[i:i + (4 << 20)], 8 << 20)
            except Exception: continue
            if len(o) < 32: continue
            for tok in set(RZ.findall(o)):
                if tok in seen: continue
                if len(seen) < 4_000_000: seen.add(tok)
                tested += 1
                h = joaat_cs(tok)
                if h in WANT: hits.setdefault(h, tok.decode())
    else:
        for tok in set(RR.findall(d[:lim + 64])):
            if tok in seen or not SHAPE.search(tok): continue
            if len(seen) < 4_000_000: seen.add(tok)
            tested += 1
            h = joaat_cs(tok)
            if h in WANT: hits.setdefault(h, tok.decode())
    off += BLK
tag = re.sub(r'[^A-Za-z0-9]', '_', name) + '_%g_%g_%s' % (g0, g1, mode)
os.makedirs(os.path.join(HERE, 'harvest2'), exist_ok=True)
pickle.dump({'file': name, 'range': (g0, g1), 'mode': mode, 'tested': tested, 'hits': hits}, open(os.path.join(HERE, 'harvest2', tag + '.pkl'), 'wb'))
print('DONE %s %g-%g GiB %s: %d tokens tested, %d hits, %.0fs' % (name, g0, g1, mode, tested, len(hits), time.time() - t0), flush=True)
