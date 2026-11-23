"""Reads the parser tables of the game executable: every struct the game can load, with the hash, type, offset and
default value of each member, and every enum with its values. The executable holds no names, only their hashes;
the tables give context (and structs that occur in no scanned file).

usage: python exe_tables.py [path to the executable]     default: game_scarlett_master.exe in the game folder
Writes <work>/exe_schema.pkl: (structs {hash: (size, flags, [member ...])}, enums {hash: [(value, name hash)]})
with member = (name hash, type, subtype, offset, default text, hash of the struct or enum it refers to or 0)."""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def sections(d):
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    count = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
    base = struct.unpack_from('<Q', d, pe + 24 + 24)[0]
    out = {}
    for i in range(count):
        s = d[pe + 24 + opt + i * 40: pe + 24 + opt + i * 40 + 40]
        vsize, va, rsize, roff = struct.unpack_from('<IIII', s, 8)
        out.setdefault(s[:8].rstrip(b'\0').decode('latin-1'), (base + va, roff, rsize))
    return out


def default_text(d, rec, kind, sub):
    """default value kept with a member, as text for a reader; empty when the type keeps none"""
    try:
        if kind in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07) and sub == 0:
            v = struct.unpack_from('<d', d, rec + 36)[0]
            if kind == 0: return 'true' if v else 'false'
            return '%.6g' % v
        if kind in (0x08, 0x09, 0x0a, 0x14, 0x15, 0x13):
            n = {0x08: 2, 0x13: 2, 0x09: 3, 0x14: 3}.get(kind, 4)
            return ' '.join('%.4g' % x for x in struct.unpack_from('<%df' % n, d, rec + 36))
    except struct.error:
        pass
    return ''


def read(path):
    d = open(path, 'rb').read()
    sec = sections(d)
    dva, doff, dsize = sec['.data']; rva, roff, rsize = sec['.rdata']

    def in_data(va): return doff + (va - dva) if dva <= va < dva + dsize else None
    def in_rdata(va): return roff + (va - rva) if rva <= va < rva + rsize else None

    # enum descriptors: pointer to the values, 16 empty bytes, hash, count, flags; values are (hash, 64-bit value)
    enums = {}; enum_at = {}
    for o in range(doff, doff + dsize - 32, 8):
        q = struct.unpack_from('<Q', d, o)[0]
        vo = in_rdata(q)
        if vo is None or d[o + 8:o + 24] != bytes(16): continue
        h, count = struct.unpack_from('<IH', d, o + 24)
        if h <= 0xffff or not (1 <= count <= 8000) or vo + count * 12 > roff + rsize: continue
        vals = [struct.unpack_from('<Iq', d, vo + k * 12) for k in range(count)]
        if any(abs(v) > 1 << 33 for _, v in vals) or sum(1 for vh, _ in vals if vh > 0xffff) * 10 < count * 9: continue
        enums[h] = [(v, vh) for vh, v in vals]; enum_at[dva + (o - doff)] = h
    # struct records: pointer to the member table, hash, size, flags, one offset per member
    structs = {}; struct_at = {}; raw = {}
    for o in range(doff, doff + dsize - 24, 8):
        mt = in_data(struct.unpack_from('<Q', d, o)[0])
        if mt is None or d[mt] != 0: continue
        n = struct.unpack_from('<H', d, mt + 1)[0]
        if not (1 <= n <= 4000) or mt + 3 + 2 * n > doff + dsize: continue
        offs = struct.unpack_from('<%dH' % n, d, mt + 3)
        if offs[0] != 3 + 2 * n or any(b <= a for a, b in zip(offs, offs[1:])): continue
        if any(d[mt + r + 32:mt + r + 34] != b'\xff\xff' for r in offs): continue
        h, size, flags = struct.unpack_from('<IIH', d, o + 8)
        moffs = struct.unpack_from('<%dI' % n, d, o + 18)
        if h <= 0xffff or any(m > max(size, 1) + 64 for m in moffs): continue
        struct_at[dva + (o - doff)] = h; struct_at[dva + (o - doff) + 8] = h
        raw[h] = (size, flags, mt, offs, moffs)
    for h, (size, flags, mt, offs, moffs) in raw.items():
        members = []
        for k, r in enumerate(offs):
            rec = mt + r
            end = mt + offs[k + 1] if k + 1 < len(offs) else rec + 96
            nh, kind, sub = struct.unpack_from('<IBB', d, rec + 24)
            ref = 0
            # a member that holds a struct, an enum or an array of them points at that descriptor somewhere in its record
            for p in range(rec + 34, end - 7):
                q = struct.unpack_from('<Q', d, p)[0]
                if q in struct_at: ref = struct_at[q]; break
                if q in enum_at: ref = enum_at[q]; break
            members.append((nh, kind, sub, moffs[k], default_text(d, rec, kind, sub), ref))
        structs[h] = (size, flags, members)
    return structs, enums


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(common.game_dir(), 'game_scarlett_master.exe')
    structs, enums = read(path)
    pickle.dump((structs, enums), open(os.path.join(common.WORK, 'exe_schema.pkl'), 'wb'))
    names = set(structs) | set(enums)
    for size, flags, members in structs.values(): names.update(m[0] for m in members)
    for vals in enums.values(): names.update(vh for _, vh in vals if vh > 0xffff)
    kinds = collections.Counter(m[1] for s in structs.values() for m in s[2])
    print('structs %d, members %d, enums %d, enum values %d, distinct name hashes %d' % (
        len(structs), sum(len(s[2]) for s in structs.values()), len(enums), sum(len(v) for v in enums.values()), len(names)))
    print('members with a default value %d, with a struct or enum reference %d' % (
        sum(1 for s in structs.values() for m in s[2] if m[4]), sum(1 for s in structs.values() for m in s[2] if m[5])))
    print('member types', dict(kinds.most_common(12)))
    tp = os.path.join(common.WORK, 'targets.pkl')
    if os.path.exists(tp):
        T = pickle.load(open(tp, 'rb'))
        print('of the %d hashed names in the scanned files, %d are in these tables; %d table names occur in no scanned file' % (len(T), len(names & set(T)), len(names - set(T))))
