"""Finds PSIN metadata files inside part of a game archive and collects their schema: struct, field and enum name hashes.

usage: python schema_scan.py <file relative to the game folder> <start GiB> <end GiB>
       python schema_scan.py --all <file> [<file> ...]     every piece of the files, several at a time
       python schema_scan.py --report                      totals, and how many hashes are new against targets.pkl

Files are found by inflating the first bytes of every zlib stream and checking for the PSIN header; files stored in
several streams are joined. Per piece a pickle goes to <work>/schema_scan/. A few files that hold structs or enums
not seen in targets.pkl are kept in <work>/psin_scan/ as context for later judging. Nothing is written to the repo."""
import os, re, sys, zlib, struct, pickle, time, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import psin_format

OUT = os.path.join(common.WORK, 'schema_scan')
KEEP = os.path.join(common.WORK, 'psin_scan')
TAGS = (b'PSIN', b'LSCH', b'LENM', b'LSNS', b'LGID', b'LRSC', b'CHKS', b'LMAP', b'PMAP', b'STRE', b'LSTR', b'PSCH', b'PSIG', b'STNS')
HEAD = re.compile(rb'\x78[\x9c\xda\x01\x5e]')
RAW = re.compile(rb'PSIN.{12}\xaa{8}', re.S)
TOKEN = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,63}')
SHAPE = re.compile(rb'[a-z][A-Z]|[A-Za-z]_[A-Za-z]')
STEP = 4.0


def iff_len(b):
    pos = 0
    while pos + 8 <= len(b):
        if bytes(b[pos:pos + 4]) not in TAGS: break
        sz = struct.unpack('>I', b[pos + 4:pos + 8])[0]
        if sz < 8: break
        pos += sz
    return pos


def complete(buf):
    return len(buf) >= 32 and iff_len(buf) == len(buf) and b'CHKS' in buf[-64:]


def inflate(f, pos):
    f.seek(pos); d = f.read((2 << 20) + 4096)
    dz = zlib.decompressobj()
    o = dz.decompress(d, 16 << 20)
    return o, len(d) - len(dz.unused_data)


def read_streams(f, pos):
    """the file whose first zlib stream starts at pos; later streams follow within a few bytes of each other"""
    o, used = inflate(f, pos)
    buf = bytearray(o)
    for _ in range(600):
        if complete(buf) or len(buf) > (96 << 20): break
        nxt = pos + used
        f.seek(nxt); look = f.read(80)
        found = False
        for m in HEAD.finditer(look):
            try: o, used2 = inflate(f, nxt + m.start())
            except Exception: continue
            if not o: continue
            buf += o; pos = nxt + m.start(); used = used2; found = True
            break
        if not found: break
    return bytes(buf)


def read_raw(f, pos):
    f.seek(pos); head = f.read(8)
    size = struct.unpack('>I', head[4:8])[0]
    if not (24 <= size <= (64 << 20)): return b''
    f.seek(pos); buf = bytearray(f.read(size))
    for _ in range(12):
        f.seek(pos + len(buf)); h = f.read(8)
        if len(h) < 8 or h[:4] not in TAGS: break
        sz = struct.unpack('>I', h[4:8])[0]
        if not (8 <= sz <= (64 << 20)): break
        f.seek(pos + len(buf)); buf += f.read(sz)
        if h[:4] == b'CHKS': break
    return bytes(buf)


def scan(name, g0, g1):
    path = os.path.join(common.game_dir(), name)
    size = os.path.getsize(path)
    lo = int(g0 * 2 ** 30); hi = min(size, int(g1 * 2 ** 30)); lo -= lo % 16
    tp = os.path.join(common.WORK, 'targets.pkl')
    old = set(pickle.load(open(tp, 'rb'))) if os.path.exists(tp) else set()
    tag = re.sub(r'[^A-Za-z0-9]', '_', name) + '_%g_%g' % (g0, g1)
    keep_dir = os.path.join(KEEP, tag)
    structs = {}; scount = collections.Counter(); enums = {}; tokens = set()
    n = collections.Counter(); kept = 0; seen_new = set()
    f = open(path, 'rb'); g = open(path, 'rb')
    BLK = 32 << 20; off = lo; t0 = time.time()

    def take(buf, where, how):
        nonlocal kept
        n['files_' + how] += 1; n['bytes'] += len(buf)
        if not complete(buf):
            n['partial'] += 1; return
        try: ch, payload, insts, st = psin_format.parse(buf)
        except Exception:
            n['unreadable'] += 1; return
        if b'LSCH' not in ch:
            n['no_schema'] += 1; return
        fresh = False
        for h, (sz, fs) in st.items():
            scount[h] += 1
            if h not in structs: structs[h] = (sz, tuple(fs))
            if h > 0xffff and h not in old and h not in seen_new: seen_new.add(h); fresh = True
            for nh, o, tr, ref in fs:
                if nh != 0x100 and nh not in old and nh not in seen_new: seen_new.add(nh); fresh = True
        for eh, vals in psin_format.enums(ch).items():
            if eh not in enums: enums[eh] = tuple(vals)
            if eh not in old and eh not in seen_new: seen_new.add(eh); fresh = True
        if len(tokens) < 3_000_000:
            for t in set(TOKEN.findall(payload)):
                if SHAPE.search(t): tokens.add(t)
        if fresh and kept < 600 and len(buf) <= (4 << 20):
            os.makedirs(keep_dir, exist_ok=True)
            open(os.path.join(keep_dir, '%012x.psin' % where), 'wb').write(buf); kept += 1

    while off < hi:
        f.seek(off); d = f.read(BLK + 64); lim = min(len(d), BLK)
        for m in HEAD.finditer(d, 0, lim):
            i = m.start()
            if (off + i) & 0xf: continue
            try: peek = zlib.decompressobj().decompress(d[i:i + 512], 24)
            except Exception: continue
            if peek[:4] != b'PSIN' or peek[16:24] != b'\xaa' * 8: continue
            try: take(read_streams(g, off + i), off + i, 'z')
            except Exception: n['failed'] += 1
        for m in RAW.finditer(d, 0, lim):
            if (off + m.start()) & 0xf: continue
            try: take(read_raw(g, off + m.start()), off + m.start(), 'raw')
            except Exception: n['failed'] += 1
        off += BLK
    os.makedirs(OUT, exist_ok=True)
    pickle.dump({'file': name, 'range': (g0, g1), 'counts': dict(n), 'structs': structs, 'struct_count': dict(scount), 'enums': enums, 'tokens': tokens},
                open(os.path.join(OUT, tag + '.pkl'), 'wb'))
    print('DONE %s %g-%g GiB: %s, %d structs, %d enums, %d tokens, %d kept, %.0fs' % (name, g0, g1, dict(n), len(structs), len(enums), len(tokens), kept, time.time() - t0), flush=True)


def run_all(names):
    from concurrent.futures import ThreadPoolExecutor
    jobs = []
    for name in names:
        size = os.path.getsize(os.path.join(common.game_dir(), name)) / 2 ** 30
        g = 0.0
        while g < size:
            jobs.append((name, g, min(size, g + STEP))); g += STEP
    print('pieces', len(jobs), flush=True)

    def one(j):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), j[0], '%g' % j[1], '%g' % j[2]], capture_output=True, text=True)
        print((r.stdout.strip().splitlines() or [r.stderr.strip()[-300:]])[-1], flush=True)
    with ThreadPoolExecutor(int(os.environ.get('SCAN_JOBS', '8'))) as ex:
        list(ex.map(one, jobs))
    print('ALL DONE', flush=True)


def merged():
    """schema of every scanned piece: (targets {hash: roles}, kinds {field hash: type bytes}, enums {enum: value hashes}, structs, counts per file)"""
    targets = collections.defaultdict(set); kinds = collections.defaultdict(set); enums = collections.defaultdict(set)
    structs = {}; per = collections.defaultdict(collections.Counter); tokens = set()
    for fn in sorted(os.listdir(OUT)):
        r = pickle.load(open(os.path.join(OUT, fn), 'rb'))
        per[r['file']].update(r['counts']); tokens |= r['tokens']
        for h, (sz, fs) in r['structs'].items():
            structs.setdefault(h, (sz, fs))
            if h > 0xffff: targets[h].add('struct')
            for nh, o, tr, ref in fs:
                if nh != 0x100: targets[nh].add('field'); kinds[nh].add(tr & 0xff)
        for eh, vals in r['enums'].items():
            targets[eh].add('enum')
            for v, vh in vals: targets[vh].add('enumval'); enums[eh].add(vh)
    return dict(targets), dict(kinds), dict(enums), structs, per, tokens


def report():
    targets, kinds, enums, structs, per, tokens = merged()
    old = pickle.load(open(os.path.join(common.WORK, 'targets.pkl'), 'rb'))
    for name, c in per.items(): print(name, dict(c))
    roles = collections.Counter(); fresh = collections.Counter()
    for h, rs in targets.items():
        r = 'field' if 'field' in rs else 'struct' if 'struct' in rs else 'enumval' if 'enumval' in rs else 'enum'
        roles[r] += 1
        if h not in old: fresh[r] += 1
    print('hashes', len(targets), dict(roles)); print('new against targets.pkl', sum(fresh.values()), dict(fresh))
    print('structs', len(structs), 'tokens', len(tokens))
    pickle.dump((targets, kinds, enums, structs), open(os.path.join(common.WORK, 'scan_schema.pkl'), 'wb'))
    pickle.dump(tokens, open(os.path.join(common.WORK, 'scan_tokens.pkl'), 'wb'))


if __name__ == '__main__':
    if sys.argv[1] == '--all': run_all(sys.argv[2:])
    elif sys.argv[1] == '--report': report()
    else: scan(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
