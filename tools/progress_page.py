"""Live progress page for the name recovery work. Serves one page and a small status endpoint on localhost."""
import os, json, pickle, time, random, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
HERE = common.CRACK
TOTAL = sum(1 for _ in open(os.path.join(HERE, 'in', 'all_targets.txt')))
PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Name recovery</title>
<style>
:root{--bg:#14101c;--panel:#1d1728;--ink:#ece8f4;--dim:#9b93ad;--bar:#2a2238;--a:#ffa81c;--b:#7cc4ff;--ok:#6fd08c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Segoe UI,system-ui,sans-serif;padding:20px 16px}
.wrap{max-width:760px;margin:0 auto}h1{font-size:19px;margin:0 0 4px}.sub{color:var(--dim);margin-bottom:18px}
.card{background:var(--panel);border-radius:10px;padding:16px 18px;margin-bottom:14px}
.big{font-size:40px;font-weight:650;letter-spacing:-.5px}.big small{font-size:16px;color:var(--dim);font-weight:400;margin-left:8px}
.bar{height:16px;background:var(--bar);border-radius:8px;overflow:hidden;margin:10px 0 6px;position:relative}
.fill{height:100%;background:var(--a);border-radius:8px;transition:width .8s ease}.fill.b{background:var(--b)}.fill.ok{background:var(--ok)}
.row{display:flex;justify-content:space-between;gap:12px;color:var(--dim);font-size:13px}
.label{font-weight:600;margin-bottom:2px}.stage{margin-top:12px}
.names{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.names span{background:var(--bar);border-radius:6px;padding:2px 8px;font:12.5px Consolas,monospace}
table{width:100%;border-collapse:collapse;font-size:13.5px}td{padding:4px 0;border-bottom:1px solid #2a2238}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);margin-right:6px;animation:p 1.6s infinite}@keyframes p{50%{opacity:.25}}
.idle .dot{background:var(--dim);animation:none}
</style></head><body><div class="wrap">
<h1>Hashed name recovery</h1><div class="sub" id="sub">loading</div>
<div class="card"><div class="big"><span id="pct">0</span>%<small id="count"></small></div>
<div class="bar"><div class="fill" id="overall" style="width:0%"></div></div>
<div class="row"><span>resolved names</span><span id="left"></span></div></div>
<div class="card" id="act"><div class="label"><span class="dot"></span><span id="stage">working</span></div><div id="stages"></div></div>
<div class="card"><div class="label">By kind</div><table id="kinds"></table></div>
<div class="card"><div class="label">Recently accepted</div><div class="names" id="names"></div></div>
</div><script>
function bar(label, done, total, cls){const p = total ? Math.min(100, 100*done/total) : 0;
 return `<div class="stage"><div class="row"><span>${label}</span><span>${done.toLocaleString()} / ${total.toLocaleString()}</span></div><div class="bar"><div class="fill ${cls}" style="width:${p}%"></div></div></div>`}
async function tick(){try{const s = await (await fetch('status')).json();
 document.getElementById('pct').textContent = (100*s.resolved/s.total).toFixed(1);
 document.getElementById('count').textContent = s.resolved.toLocaleString() + ' of ' + s.total.toLocaleString();
 document.getElementById('overall').style.width = (100*s.resolved/s.total) + '%';
 document.getElementById('left').textContent = (s.total - s.resolved).toLocaleString() + ' still hashed';
 document.getElementById('sub').textContent = 'updated ' + new Date().toLocaleTimeString() + ' · merged results only, work in progress is shown below';
 document.getElementById('stage').textContent = s.stage;
 document.getElementById('act').className = 'card' + (s.active ? '' : ' idle');
 document.getElementById('stages').innerHTML = s.bars.map(b => bar(b.label, b.done, b.total, b.cls)).join('');
 document.getElementById('kinds').innerHTML = s.kinds.map(k => `<tr><td>${k[0]}</td><td>${k[1].toLocaleString()} / ${k[2].toLocaleString()} (${(100*k[1]/k[2]).toFixed(0)}%)</td></tr>`).join('');
 document.getElementById('names').innerHTML = s.names.map(n => `<span>${n}</span>`).join('');
 }catch(e){document.getElementById('sub').textContent = 'waiting for status'}}
tick(); setInterval(tick, 3000);
</script></body></html>"""


def load(name, default):
    try:
        with open(os.path.join(HERE, name), 'rb') as f: return pickle.load(f)
    except Exception:
        return default


_roles = None


def roles():
    global _roles
    if _roles is None:
        t = load(os.path.join('..', 'targets.pkl'), {})
        _roles = {h: ('struct names' if 'struct' in r else 'field names' if 'field' in r else 'enum values' if 'enumval' in r else 'enum names') for h, r in t.items()}
    return _roles


def status():
    known = load('known.pkl', {}); acc = load('accepted.pkl', {})
    got = set(known) | set(acc)
    r = roles()
    tot = {}; have = {}
    for h, k in r.items():
        tot[k] = tot.get(k, 0) + 1
        if h in got: have[k] = have.get(k, 0) + 1
    bars = []; active = False
    sj = os.path.join(HERE, 'sjobs')
    if os.path.isdir(sj):
        for tag in sorted(os.listdir(sj)):
            d = os.path.join(sj, tag); names = os.listdir(d)
            total = sum(1 for n in names if n.startswith('targets_'))
            started = [n for n in names if n.startswith('out_')]
            fresh = any(time.time() - os.path.getmtime(os.path.join(d, n)) < 90 for n in started[-40:]) if started else False
            done = len(started) - (9 if fresh else 0)
            if total and (fresh or len(started) < total):
                bars.append({'label': 'Per-struct search (%s): structs searched' % tag, 'done': max(done, 0), 'total': total, 'cls': 'b'}); active = active or fresh
    od = os.path.join(HERE, 'out')
    if os.path.isdir(od):
        rounds = {}
        for n in os.listdir(od):
            m = re.match(r'(r\d+)_(.+)\.txt$', n)
            if m: rounds.setdefault(m.group(1), []).append(os.path.getmtime(os.path.join(od, n)))
        classes = sum(1 for n in os.listdir(os.path.join(HERE, 'in')) if n.startswith('targets_'))
        if rounds:
            tag = max(rounds, key=lambda t: max(rounds[t]))
            finished = os.path.exists(os.path.join(HERE, 'cracked_%s.txt' % tag)) and os.path.getmtime(os.path.join(HERE, 'cracked_%s.txt' % tag)) >= max(rounds[tag])
            if not finished and time.time() - max(rounds[tag]) < 1200:
                bars.append({'label': 'General cracker: name types searched', 'done': max(len(rounds[tag]) - 1, 0), 'total': classes, 'cls': 'b'}); active = True
    try:
        hs = json.load(open(os.path.join(HERE, 'harvest_status.json')))
        if hs['done'] < hs['total'] and time.time() - hs['t'] < 3600:
            bars.append({'label': 'Scanning game files for names: pieces done', 'done': hs['done'], 'total': hs['total'], 'cls': 'b'}); active = True
    except Exception:
        pass
    jd = os.path.join(HERE, 'judge')
    if os.path.isdir(jd):
        ins = [n for n in os.listdir(jd) if n.endswith('.txt')]; outs = [n for n in os.listdir(jd) if n.endswith('.out')]
        if ins and len(outs) < len(ins):
            bars.append({'label': 'Judging candidates: files judged', 'done': len(outs), 'total': len(ins), 'cls': 'ok'}); active = True
    stage = 'idle'
    try: stage = open(os.path.join(HERE, 'stage.txt'), encoding='utf-8').read().strip() or stage
    except Exception: pass
    vals = list(acc.values()); random.seed(int(time.time() // 9))
    order = ['field names', 'struct names', 'enum values', 'enum names']
    return {'total': TOTAL, 'resolved': len(got & set(r)), 'bars': bars, 'active': active, 'stage': stage,
            'kinds': [[k, have.get(k, 0), tot.get(k, 1)] for k in order if k in tot], 'names': random.sample(vals, min(28, len(vals)))}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path.startswith('/status'):
            body = json.dumps(status()).encode(); ctype = 'application/json'
        else:
            body = PAGE.encode(); ctype = 'text/html; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)


ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), H).serve_forever()
