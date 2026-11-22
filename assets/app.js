(function () {
  'use strict';

  var PROGRESS_URL = 'data/progress.json';
  var NAMES_URL = 'data/names.tsv';
  var PAGE = 200;

  var KIND_LABEL = { 'field': 'Fields', 'struct': 'Structs', 'enum value': 'Enum values', 'enum': 'Enums' };
  var METHOD_ORDER = ['name list', 'game text', 'word combination', 'cracked', 'judged'];
  var METHOD_REL = {
    'name list': 'reliable', 'game text': 'reliable',
    'word combination': 'measured', 'cracked': 'measured',
    'judged': 'unmeasured'
  };
  var REL_TEXT = {
    reliable: 'Reliable',
    measured: 'Chance rate measured (a few percent)',
    unmeasured: 'Error rate not yet measured'
  };
  var REL_MARK = { reliable: '', measured: '*', unmeasured: '†' };

  // Method name with its reliability footnote mark (* measured, † not measured).
  function methodLabel(method) {
    var rel = METHOD_REL[method] || 'unmeasured';
    var s = el('span', 'meth rel-' + rel, method);
    if (REL_MARK[rel]) s.appendChild(el('sup', null, REL_MARK[rel]));
    s.title = REL_TEXT[rel];
    return s;
  }

  var fmt = new Intl.NumberFormat('en-US');
  var pct = function (n, d) { return d ? (100 * n / d) : 0; };
  var fmtPct = function (n, d) { return pct(n, d).toFixed(1) + '%'; };
  var $ = function (id) { return document.getElementById(id); };

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function bind(key, value) {
    var nodes = document.querySelectorAll('[data-bind="' + key + '"]');
    for (var i = 0; i < nodes.length; i++) nodes[i].textContent = value;
  }

  /* ---------------- joaat ---------------- */
  function joaat(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = (h + s.charCodeAt(i)) >>> 0;
      h = (h + (h << 10)) >>> 0;
      h = (h ^ (h >>> 6)) >>> 0;
    }
    h = (h + (h << 3)) >>> 0;
    h = (h ^ (h >>> 11)) >>> 0;
    h = (h + (h << 15)) >>> 0;
    return h;
  }
  function hex8(n) { return ('00000000' + n.toString(16)).slice(-8); }

  /* ---------------- theme toggle ---------------- */
  (function theme() {
    var btn = $('theme-toggle');
    var modes = ['auto', 'light', 'dark'];
    var labels = { auto: 'auto', light: 'light', dark: 'dark' };
    var cur = document.documentElement.dataset.theme || 'auto';
    function apply(m) {
      cur = m;
      if (m === 'auto') delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = m;
      btn.textContent = labels[m];
      btn.setAttribute('aria-label', 'Colour theme: ' + (m === 'auto' ? 'automatic' : m) + '. Click to change.');
      try { if (m === 'auto') localStorage.removeItem('theme'); else localStorage.setItem('theme', m); } catch (e) {}
    }
    apply(cur);
    btn.addEventListener('click', function () { apply(modes[(modes.indexOf(cur) + 1) % modes.length]); });
  })();

  /* ---------------- tooltip ---------------- */
  (function tooltip() {
    var tip = $('tip');
    function place(e) {
      var pad = 12, w = tip.offsetWidth, h = tip.offsetHeight;
      var x = e.clientX + pad, y = e.clientY + pad;
      if (x + w > window.innerWidth - 8) x = e.clientX - w - pad;
      if (y + h > window.innerHeight - 8) y = e.clientY - h - pad;
      tip.style.left = Math.max(8, x) + 'px';
      tip.style.top = Math.max(8, y) + 'px';
    }
    document.addEventListener('pointermove', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      if (!t || e.pointerType === 'touch') { tip.hidden = true; return; }
      tip.innerHTML = '';
      var lines = t.getAttribute('data-tip').split('\n');
      for (var i = 0; i < lines.length; i++) {
        var d = el('div', null, lines[i]);
        if (i === 0) d.style.fontWeight = '600';
        tip.appendChild(d);
      }
      tip.hidden = false;
      place(e);
    });
    document.addEventListener('pointerleave', function () { tip.hidden = true; });
  })();

  /* ---------------- charts ---------------- */
  function barRow(label, segs, valueNode, tipText, max) {
    var row = el('div', 'hbar');
    row.setAttribute('data-tip', tipText);
    var lab = el('div', 'hbar-label');
    if (typeof label === 'string') lab.textContent = label; else lab.appendChild(label);
    row.appendChild(lab);
    var body = el('div', 'hbar-body');
    var track = el('div', 'hbar-track');
    track.setAttribute('aria-hidden', 'true');
    segs.forEach(function (s) {
      var seg = el('div', 'seg ' + s.cls);
      seg.style.width = (100 * s.value / max) + '%';
      track.appendChild(seg);
    });
    body.appendChild(track);
    body.appendChild(valueNode);
    row.appendChild(body);
    return row;
  }

  function valueNode(main, sub) {
    var v = el('div', 'hbar-value');
    v.appendChild(el('strong', null, main));
    if (sub) v.appendChild(document.createTextNode(' ' + sub));
    return v;
  }

  function renderProgress(p) {
    bind('percent', fmtPct(p.resolved, p.total));
    bind('resolved', fmt.format(p.resolved));
    bind('total', fmt.format(p.total));
    bind('scope', p.scope);
    bind('updated', p.updated);
    $('headline-fill').style.width = pct(p.resolved, p.total) + '%';
    $('headline-meter').setAttribute('aria-label',
      fmtPct(p.resolved, p.total) + ' of names recovered; estimated ceiling 60 to 70%');

    var kind = $('chart-kind');
    kind.innerHTML = '';
    p.by_kind.forEach(function (k) {
      var label = KIND_LABEL[k.kind] || k.kind;
      kind.appendChild(barRow(label,
        [{ cls: 'kind', value: k.resolved }],
        valueNode(fmtPct(k.resolved, k.total), fmt.format(k.resolved) + ' / ' + fmt.format(k.total)),
        label + '\n' + fmt.format(k.resolved) + ' of ' + fmt.format(k.total) + ' recovered (' + fmtPct(k.resolved, k.total) + ')\n' +
          fmt.format(k.total - k.resolved) + ' still unknown',
        k.total));
    });

    var method = $('chart-method');
    method.innerHTML = '';
    var mmax = Math.max.apply(null, p.by_method.map(function (m) { return m.count; }));
    var msum = p.by_method.reduce(function (a, m) { return a + m.count; }, 0);
    var methods = p.by_method.slice().sort(function (a, b) {
      return idx(METHOD_ORDER, a.method) - idx(METHOD_ORDER, b.method);
    });
    methods.forEach(function (m) {
      var rel = METHOD_REL[m.method] || 'unmeasured';
      var track = barRow(methodLabel(m.method),
        [{ cls: 'rel-' + rel, value: m.count }],
        valueNode(fmt.format(m.count), '(' + fmtPct(m.count, msum) + ')'),
        m.method + '\n' + fmt.format(m.count) + ' names, ' + fmtPct(m.count, msum) + ' of recovered\n' + REL_TEXT[rel],
        mmax);
      track.querySelector('.hbar-track').classList.add('bare');
      method.appendChild(track);
    });

    var hist = $('chart-history');
    hist.innerHTML = '';
    var prev = 0;
    p.history.forEach(function (h, i) {
      var added = h.resolved - prev;
      var segs = i === 0 || added < 0
        ? [{ cls: 'hist-added', value: h.resolved }]
        : [{ cls: 'hist-before', value: prev }, { cls: 'hist-added', value: added }];
      if (segs.length === 2 && prev === 0) segs.shift();
      var sign = added >= 0 ? '+' : '−';
      hist.appendChild(barRow(h.step, segs,
        valueNode(fmt.format(h.resolved), i === 0 ? '' : '(' + sign + fmt.format(Math.abs(added)) + ')'),
        h.step + '\n' + fmt.format(h.resolved) + ' names (' + fmtPct(h.resolved, p.total) + ')' +
          (i === 0 ? '' : '\n' + sign + fmt.format(Math.abs(added)) + ' compared with the step before'),
        p.total));
      prev = h.resolved;
    });

    var judged = p.by_method.filter(function (m) { return m.method === 'judged'; })[0];
    bind('judged', judged ? fmt.format(judged.count) : '–');

    // Accuracy notes per method, if the data has them (otherwise the static paragraph stays).
    if (Array.isArray(p.accuracy) && p.accuracy.length) {
      var box = $('accuracy');
      box.innerHTML = '';
      var intro = el('p');
      intro.appendChild(el('strong', null, 'Accuracy by method.'));
      intro.appendChild(document.createTextNode(' What is known about how often each method is wrong. The table in section 3 shows the method of every name.'));
      box.appendChild(intro);
      var dl = el('dl', 'notes accuracy');
      p.accuracy.forEach(function (a) {
        var d = el('div');
        d.appendChild(el('dt', null, a.method));
        d.appendChild(el('dd', null, a.note));
        dl.appendChild(d);
      });
      box.appendChild(dl);
    }
  }

  function idx(arr, v) { var i = arr.indexOf(v); return i < 0 ? arr.length : i; }

  /* ---------------- names table ---------------- */
  var rows = [];        // {hash, name, kind, method, lname}
  var byHash = new Map();
  var view = [];
  var shown = 0;
  var sortKey = 'name', sortDir = 1;

  function parseTsv(text) {
    var lines = text.split(/\r?\n/);
    var head = lines[0].split('\t');
    var ci = { hash: head.indexOf('hash'), name: head.indexOf('name'), kind: head.indexOf('kind'), method: head.indexOf('method') };
    var out = [];
    for (var i = 1; i < lines.length; i++) {
      if (!lines[i]) continue;
      var c = lines[i].split('\t');
      var r = {
        hash: (c[ci.hash] || '').toLowerCase(),
        name: c[ci.name] || '',
        kind: c[ci.kind] || '',
        method: c[ci.method] || ''
      };
      r.lname = r.name.toLowerCase();
      out.push(r);
    }
    return out;
  }

  function fillSelect(select, values, labelFn) {
    values.forEach(function (v) {
      var o = el('option', null, labelFn ? labelFn(v) : v);
      o.value = v;
      select.appendChild(o);
    });
  }

  function cmp(a, b) {
    var x = a[sortKey], y = b[sortKey];
    if (sortKey === 'name') { x = a.lname; y = b.lname; }
    if (sortKey === 'method') { x = idx(METHOD_ORDER, a.method); y = idx(METHOD_ORDER, b.method); }
    if (x < y) return -sortDir;
    if (x > y) return sortDir;
    return a.lname < b.lname ? -1 : a.lname > b.lname ? 1 : 0;
  }

  function currentQuery() {
    var q = $('q').value.trim();
    var lq = q.toLowerCase();
    var hq = lq.replace(/^0x/, '');
    var isHex = /^[0-9a-f]{1,8}$/.test(hq);
    return { raw: q, lq: lq, hq: isHex ? hq : null };
  }

  function applyFilters() {
    var q = currentQuery();
    var kind = $('f-kind').value;
    var method = $('f-method').value;
    view = rows.filter(function (r) {
      if (kind && r.kind !== kind) return false;
      if (method && r.method !== method) return false;
      if (!q.lq) return true;
      if (r.lname.indexOf(q.lq) !== -1) return true;
      return q.hq !== null && r.hash.indexOf(q.hq) === 0;
    });
    view.sort(cmp);
    shown = 0;
    $('rows').innerHTML = '';
    renderMore();
  }

  function highlight(td, text, lq) {
    var i = lq ? text.toLowerCase().indexOf(lq) : -1;
    if (i < 0) { td.textContent = text; return; }
    td.appendChild(document.createTextNode(text.slice(0, i)));
    td.appendChild(el('mark', null, text.slice(i, i + lq.length)));
    td.appendChild(document.createTextNode(text.slice(i + lq.length)));
  }

  function renderMore() {
    var q = currentQuery();
    var frag = document.createDocumentFragment();
    var end = Math.min(view.length, shown + PAGE);
    for (var i = shown; i < end; i++) {
      var r = view[i];
      var tr = document.createElement('tr');
      var tn = el('td', 'n'); highlight(tn, r.name, q.lq); tr.appendChild(tn);
      var th = el('td', 'h');
      if (q.hq !== null && r.hash.indexOf(q.hq) === 0) {
        th.appendChild(document.createTextNode('0x'));
        th.appendChild(el('mark', null, r.hash.slice(0, q.hq.length)));
        th.appendChild(document.createTextNode(r.hash.slice(q.hq.length)));
      } else th.textContent = '0x' + r.hash;
      tr.appendChild(th);
      tr.appendChild(el('td', 'k', r.kind));
      var tm = el('td', 'm');
      tm.appendChild(methodLabel(r.method));
      tr.appendChild(tm);
      frag.appendChild(tr);
    }
    $('rows').appendChild(frag);
    shown = end;
    var total = rows.length;
    $('count').textContent = view.length === total
      ? 'Showing ' + fmt.format(shown) + ' of ' + fmt.format(total) + ' names'
      : fmt.format(view.length) + ' of ' + fmt.format(total) + ' names match' +
        (view.length ? ' · showing ' + fmt.format(shown) : '');
    var more = $('more');
    more.hidden = shown >= view.length;
    more.textContent = 'show ' + fmt.format(Math.min(PAGE, view.length - shown)) + ' more';
  }

  function updateSortButtons() {
    var btns = document.querySelectorAll('.names th button');
    for (var i = 0; i < btns.length; i++) {
      var k = btns[i].getAttribute('data-sort');
      if (k === sortKey) btns[i].setAttribute('aria-sort', sortDir > 0 ? 'ascending' : 'descending');
      else btns[i].removeAttribute('aria-sort');
    }
  }

  function initTable(text) {
    rows = parseTsv(text);
    rows.forEach(function (r) { byHash.set(r.hash, r); });
    var kinds = [], methods = [];
    rows.forEach(function (r) {
      if (kinds.indexOf(r.kind) < 0) kinds.push(r.kind);
      if (methods.indexOf(r.method) < 0) methods.push(r.method);
    });
    kinds.sort(function (a, b) { return idx(Object.keys(KIND_LABEL), a) - idx(Object.keys(KIND_LABEL), b); });
    methods.sort(function (a, b) { return idx(METHOD_ORDER, a) - idx(METHOD_ORDER, b); });
    fillSelect($('f-kind'), kinds, function (k) { return KIND_LABEL[k] || k; });
    fillSelect($('f-method'), methods);

    var t;
    $('q').addEventListener('input', function () { clearTimeout(t); t = setTimeout(applyFilters, 120); });
    $('f-kind').addEventListener('change', applyFilters);
    $('f-method').addEventListener('change', applyFilters);
    $('more').addEventListener('click', renderMore);
    var btns = document.querySelectorAll('.names th button');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () {
        var k = this.getAttribute('data-sort');
        if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
        updateSortButtons();
        applyFilters();
      });
    }
    updateSortButtons();
    applyFilters();
    convReady();
  }

  /* ---------------- animated converter ---------------- */
  var NAME_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  var HEX_CHARS = '0123456789abcdef';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var anims = new WeakMap();

  // Reveal `text` in `node` left to right, with the unrevealed part cycling through random characters.
  function scramble(node, text, charset, fixed, done) {
    var prev = anims.get(node);
    if (prev) clearTimeout(prev.raf);
    if (reduceMotion || !text) { node.textContent = text; if (done) done(); return; }
    var n = text.length;
    var dur = Math.min(1100, 420 + n * 26);
    var hold = 0.22;               // share of the time spent fully scrambled
    var start = performance.now(), last = -1e9, rnd = '';
    var locked = document.createElement('span');
    var rest = el('span', 'scr');
    node.textContent = '';
    node.appendChild(locked);
    node.appendChild(rest);
    var st = {};
    function frame(now) {
      var t = (now - start) / dur;
      var k = t <= hold ? 0 : Math.floor((t - hold) / (1 - hold) * n);
      k = Math.max(fixed || 0, Math.min(n, k));
      if (now - last > 30) {
        rnd = '';
        for (var i = k; i < n; i++) rnd += charset[(Math.random() * charset.length) | 0];
        last = now;
      } else {
        rnd = rnd.slice(rnd.length - (n - k));
      }
      locked.textContent = text.slice(0, k);
      rest.textContent = rnd;
      if (k < n) st.raf = setTimeout(tick, 40);
      else { node.textContent = text; anims.delete(node); if (done) done(); }
    }
    function tick() { frame(performance.now()); }
    st.raf = setTimeout(tick, 0);
    anims.set(node, st);
  }

  function parseConv(v) {
    v = v.trim();
    if (!v) return null;
    var m = /^(0x)?([0-9a-f]{1,8})$/i.exec(v);
    if (m && (m[1] || m[2].length === 8)) {
      return { type: 'hash', hex: ('00000000' + m[2].toLowerCase()).slice(-8), complete: m[2].length === 8 };
    }
    return { type: 'name', name: v };
  }

  var conv = {
    input: $('conv-input'), out: $('conv-out'), from: $('conv-from'), to: $('conv-to'),
    meta: $('conv-meta'),
    live: $('conv-live'), copy: $('conv-copy'), lastKey: null, copyText: ''
  };

  function setMeta(nodes, liveText) {
    conv.meta.classList.remove('show');
    conv.meta.innerHTML = '';
    nodes.forEach(function (n) { conv.meta.appendChild(typeof n === 'string' ? document.createTextNode(n) : n); });
    conv.live.textContent = liveText;
    void conv.meta.offsetWidth;    // restart the fade-in
    conv.meta.classList.add('show');
  }

  function finish(found) {
    conv.out.classList.remove('busy');
    conv.to.classList.remove('flash');
    if (found && !reduceMotion) { void conv.to.offsetWidth; conv.to.classList.add('flash'); }
    conv.copy.hidden = !conv.copyText;
  }

  function runConv(force) {
    if (!rows.length) return;
    var p = parseConv(conv.input.value);
    if (!p) return;
    if (p.type === 'hash' && !p.complete && !force) {
      conv.meta.classList.add('show');
      conv.meta.textContent = 'A hash has 8 hex digits. Press Enter to fill the rest with leading zeros.';
      return;
    }
    var key = p.type === 'hash' ? 'h:' + p.hex : 'n:' + p.name;
    if (key === conv.lastKey && !force) return;
    conv.lastKey = key;
    conv.out.classList.add('busy');
    conv.copy.hidden = true;
    conv.to.classList.remove('miss', 'flash');
    conv.meta.classList.remove('show');

    if (p.type === 'hash') {
      var r = byHash.get(p.hex);
      conv.from.textContent = '0x' + p.hex;
      if (r) {
        conv.copyText = r.name;
        scramble(conv.to, r.name, NAME_CHARS, 0, function () {
          finish(true);
          setMeta(['Kind: ' + r.kind + '. Method: ', methodLabel(r.method), '. ' + REL_TEXT[METHOD_REL[r.method] || 'unmeasured'] + '.'],
            '0x' + p.hex + ' is ' + r.name + ', a ' + r.kind + ' (method: ' + r.method + ').');
        });
      } else {
        conv.copyText = '';
        conv.to.classList.add('miss');
        scramble(conv.to, 'not recovered yet', NAME_CHARS, 0, function () {
          finish(false);
          setMeta(['This hash is not among the ' + fmt.format(rows.length) + ' recovered names. It may not be found yet, or it may not occur in the files covered here.'],
            '0x' + p.hex + ' is not among the recovered names.');
        });
      }
    } else {
      var h = hex8(joaat(p.name));
      var hit = byHash.get(h);
      conv.from.textContent = p.name;
      conv.copyText = '0x' + h;
      scramble(conv.to, '0x' + h, HEX_CHARS, 2, function () {
        finish(!!(hit && hit.name === p.name));
        var meta, live;
        if (hit && hit.name === p.name) {
          meta = ['Recovered. Kind: ' + hit.kind + '. Method: ', methodLabel(hit.method), '.'];
          live = p.name + ' hashes to 0x' + h + ' and is a recovered ' + hit.kind + '.';
        } else if (hit) {
          var c = el('code', null, hit.name);
          meta = ['Same hash as the recovered name ', c, '. Different text, same number.'];
          live = p.name + ' hashes to 0x' + h + ', the same hash as the recovered name ' + hit.name + '.';
        } else {
          meta = ['Not among the recovered names. Names are case-sensitive: ', el('code', null, 'fMass'), ' and ', el('code', null, 'fmass'), ' differ.'];
          live = p.name + ' hashes to 0x' + h + ', which is not among the recovered names.';
        }
        setMeta(meta, live);
      });
    }
  }

  var convTimer;
  conv.input.addEventListener('input', function () {
    clearTimeout(convTimer);
    convTimer = setTimeout(function () { runConv(false); }, 280);
  });
  conv.input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { clearTimeout(convTimer); runConv(true); }
  });
  $('conv-random').addEventListener('click', function () {
    if (!rows.length) return;
    conv.input.value = '0x' + rows[(Math.random() * rows.length) | 0].hash;
    runConv(true);
  });
  var chips = document.querySelectorAll('.lookup-try button');
  for (var ci = 0; ci < chips.length; ci++) {
    chips[ci].addEventListener('click', function () {
      conv.input.value = this.getAttribute('data-q');
      runConv(true);
    });
  }
  conv.copy.addEventListener('click', function () {
    var b = conv.copy;
    function done(ok) { b.textContent = ok ? 'copied' : 'copy failed'; setTimeout(function () { b.textContent = 'copy'; }, 1400); }
    try { navigator.clipboard.writeText(conv.copyText).then(function () { done(true); }, function () { done(false); }); }
    catch (e) { done(false); }
  });
  function convReady() { runConv(true); }

  /* ---------------- load ---------------- */
  function fail(err) {
    $('load-error').hidden = false;
    $('count').textContent = 'The names could not be loaded.';
    if (window.console) console.error(err);
  }

  fetch(PROGRESS_URL, { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(PROGRESS_URL + ': HTTP ' + r.status); return r.json(); })
    .then(renderProgress)
    .catch(fail);

  fetch(NAMES_URL, { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(NAMES_URL + ': HTTP ' + r.status); return r.text(); })
    .then(initTable)
    .catch(fail);
})();
