/* Özel dikim görselleştirici.
   Ölçüler gerçek orana göre çizilir (1 cm = sabit piksel), renkler mağazanın kartelasından gelir.
   Yeni bir ürün şekli eklemek için: SHAPES içine bir çizim fonksiyonu, AREA içine kumaş hesabı ekleyin. */
(() => {
  const cfg = JSON.parse(document.getElementById('viz-config').textContent);
  const svg = document.getElementById('viz');
  const NS = 'http://www.w3.org/2000/svg';
  const VW = 600, VH = 460, PAD = 56;
  const $ = (id) => document.getElementById(id);

  const state = { item: cfg.items[0], dims: {}, parts: {} };

  // ---------- SVG yardımcıları ----------
  function el(name, attrs = {}, parent) {
    const node = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
  }

  function buildDefs() {
    const defs = el('defs', {}, svg);
    // Hacim hissi için üstten ışık, alttan gölge
    const shade = el('linearGradient', { id: 'shade', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el('stop', { offset: 0, 'stop-color': '#fff', 'stop-opacity': .22 }, shade);
    el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': .14 }, shade);
    const fold = el('linearGradient', { id: 'foldg', x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
    el('stop', { offset: 0, 'stop-color': '#000', 'stop-opacity': .2 }, fold);
    el('stop', { offset: .5, 'stop-color': '#fff', 'stop-opacity': .16 }, fold);
    el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': .2 }, fold);
    const drop = el('filter', { id: 'drop', x: '-10%', y: '-10%', width: '120%', height: '130%' }, defs);
    el('feDropShadow', { dx: 0, dy: 5, stdDeviation: 6, 'flood-color': '#1c1917', 'flood-opacity': .22 }, drop);

    for (const c of cfg.colors) {
      if (c.image) {
        const p = el('pattern', { id: 'c' + c.id, width: 90, height: 90, patternUnits: 'userSpaceOnUse' }, defs);
        el('image', { href: c.image, width: 90, height: 90, preserveAspectRatio: 'xMidYMid slice' }, p);
      } else if (c.pattern === 'cizgili') {
        const p = el('pattern', { id: 'c' + c.id, width: 18, height: 18, patternUnits: 'userSpaceOnUse' }, defs);
        el('rect', { width: 18, height: 18, fill: c.hex }, p);
        el('rect', { width: 7, height: 18, fill: c.hex2 }, p);
      } else if (c.pattern === 'kareli') {
        const p = el('pattern', { id: 'c' + c.id, width: 24, height: 24, patternUnits: 'userSpaceOnUse' }, defs);
        el('rect', { width: 24, height: 24, fill: c.hex }, p);
        el('rect', { width: 12, height: 24, fill: c.hex2, opacity: .55 }, p);
        el('rect', { width: 24, height: 12, fill: c.hex2, opacity: .55 }, p);
      } else if (c.pattern === 'puantiye') {
        const p = el('pattern', { id: 'c' + c.id, width: 20, height: 20, patternUnits: 'userSpaceOnUse' }, defs);
        el('rect', { width: 20, height: 20, fill: c.hex }, p);
        el('circle', { cx: 5, cy: 5, r: 2.6, fill: c.hex2 }, p);
        el('circle', { cx: 15, cy: 15, r: 2.6, fill: c.hex2 }, p);
      }
    }
  }

  const colorById = (id) => cfg.colors.find((c) => c.id === id) || cfg.colors[0];
  function fillOf(partKey) {
    const c = colorById(state.parts[partKey]);
    return c.image || c.pattern !== 'duz' ? `url(#c${c.id})` : c.hex;
  }

  // Dolgulu + gölgelendirilmiş yuvarlak köşeli kutu
  function box(g, x, y, w, h, fill, r = 6, shaded = true) {
    el('rect', { x, y, width: w, height: h, rx: r, fill, stroke: 'rgba(0,0,0,.18)', 'stroke-width': 1 }, g);
    if (shaded) el('rect', { x, y, width: w, height: h, rx: r, fill: 'url(#shade)', 'pointer-events': 'none' }, g);
  }

  function label(g, x, y, text, anchor = 'middle', rotate = 0) {
    const t = el('text', {
      x, y, 'text-anchor': anchor, 'font-size': 14, 'font-weight': 700, fill: '#44403c',
      'font-family': 'system-ui, sans-serif', 'paint-order': 'stroke', stroke: '#fff', 'stroke-width': 4,
    }, g);
    if (rotate) t.setAttribute('transform', `rotate(${rotate} ${x} ${y})`);
    t.textContent = text;
  }

  function dimH(g, x1, x2, y, text) {
    el('path', { d: `M${x1} ${y}H${x2}M${x1} ${y - 6}v12M${x2} ${y - 6}v12`, stroke: '#78716c', 'stroke-width': 1.5, fill: 'none' }, g);
    label(g, (x1 + x2) / 2, y + 20, text);
  }
  function dimV(g, x, y1, y2, text) {
    el('path', { d: `M${x} ${y1}V${y2}M${x - 6} ${y1}h12M${x - 6} ${y2}h12`, stroke: '#78716c', 'stroke-width': 1.5, fill: 'none' }, g);
    label(g, x + 20, (y1 + y2) / 2, text, 'middle', 90);
  }
  function note(g, text) { label(g, VW / 2, 24, text); }

  // Gerçek ölçüyü (cm) çizim alanına sığdıran ölçek ve sol-üst köşe
  function fit(realW, realH) {
    const s = Math.min((VW - PAD * 2) / realW, (VH - PAD * 2 - 10) / realH);
    return { s, x: (VW - realW * s) / 2, y: (VH - realH * s) / 2 + 4 };
  }

  // ---------- Şekiller ----------
  const SHAPES = {
    // Yatak: üstten görünüm
    bed(g, d, kind) {
      const head = 8; // başlık kalınlığı (cm)
      const { s, x, y } = fit(d.w + 24, d.l + head + 10);
      const bx = x + 12 * s, by = y + head * s, bw = d.w * s, bl = d.l * s;
      const body = el('g', { filter: 'url(#drop)' }, g);
      box(body, bx - 4 * s, y, bw + 8 * s, head * s + 6, '#8a6a4b', 5); // başlık
      box(body, bx, by, bw, bl, kind === 'yatak_ortusu' ? '#f5f5f4' : fillOf('sheet'), 10);

      // yastıklar (50x70 cm; dar yatakta tek, genişte çift)
      const n = d.w >= 130 ? 2 : 1;
      const pw = Math.min(70, d.w / n - 8) * s, ph = Math.min(50, d.l * .3) * s;
      const gap = (bw - n * pw) / (n + 1);
      const pillows = () => {
        for (let i = 0; i < n; i++) box(body, bx + gap + i * (pw + gap), by + 7 * s, pw, ph, fillOf('pillow'), 12 * s);
      };

      if (kind === 'nevresim') {
        pillows();
        const top = by + ph + 16 * s, over = 6 * s;
        box(body, bx - over, top, bw + over * 2, by + bl - top + over, fillOf('duvet'), 12);
        // kıvrılmış üst kenar: nevresimin iç yüzü
        el('rect', { x: bx - over, y: top, width: bw + over * 2, height: 14 * s, rx: 8, fill: '#fff', opacity: .38 }, body);
        el('path', { d: `M${bx - over} ${top + 14 * s}H${bx + bw + over}`, stroke: 'rgba(0,0,0,.2)', 'stroke-width': 1 }, body);
      } else if (kind === 'yatak_ortusu') {
        const over = 10 * s;
        box(body, bx - over, by + 2 * s, bw + over * 2, bl + over - 2 * s, fillOf('cover'), 14);
        // kapitone dikiş çizgileri
        const q = el('g', { stroke: 'rgba(0,0,0,.12)', 'stroke-width': 1, fill: 'none' }, body);
        for (let i = 1; i < 4; i++) el('path', { d: `M${bx + (bw * i) / 4} ${by + ph + 22 * s}V${by + bl}` }, q);
        pillows();
      } else {
        // lastikli çarşaf: köşe büzgüleri
        const c = el('g', { stroke: 'rgba(0,0,0,.22)', 'stroke-width': 1.2, fill: 'none' }, body);
        const k = 9 * s;
        [[bx, by, 1, 1], [bx + bw, by, -1, 1], [bx, by + bl, 1, -1], [bx + bw, by + bl, -1, -1]].forEach(([cx, cy, sx, sy]) => {
          el('path', { d: `M${cx + sx * k} ${cy + sy * 2}Q${cx + sx * k * .5} ${cy + sy * k * .5} ${cx + sx * 2} ${cy + sy * k}` }, c);
        });
        pillows();
      }
      dimH(g, bx, bx + bw, by + bl + 22, `${d.w} cm`);
      dimV(g, bx + bw + 24, by, by + bl, `${d.l} cm`);
      note(g, `Yatak yüksekliği ${d.h} cm`);
    },

    // Koltuk: önden görünüm
    sofa(g, d) {
      const foot = 8;
      const { s, x, y } = fit(d.w, d.h + foot);
      const W = d.w * s, H = d.h * s, arm = Math.min(22, d.w * .16) * s, seatY = y + H - 42 * s;
      const body = el('g', { filter: 'url(#drop)' }, g);
      // ayaklar
      [x + arm * .6, x + W - arm * .6 - 8 * s].forEach((fx) => el('rect', { x: fx, y: y + H - 2, width: 8 * s, height: foot * s, rx: 2, fill: '#44403c' }, body));
      box(body, x + arm * .5, y, W - arm, H - 14 * s, fillOf('body'), 16 * s); // sırt
      // sırt ve oturma minderleri
      const inner = W - arm * 2, n = Math.max(1, Math.round(d.w / 75)), cw = inner / n;
      for (let i = 0; i < n; i++) {
        box(body, x + arm + i * cw + 2, y + 9 * s, cw - 4, seatY - y - 7 * s, fillOf('cushion'), 10 * s);
        box(body, x + arm + i * cw + 1, seatY, cw - 2, 19 * s, fillOf('cushion'), 7 * s);
      }
      box(body, x + arm * .8, seatY + 18 * s, W - arm * 1.6, 24 * s, fillOf('body'), 5 * s); // etek
      const armH = Math.min(62, d.h - 14) * s;
      box(body, x, y + H - armH, arm, armH, fillOf('body'), 9 * s); // kollar
      box(body, x + W - arm, y + H - armH, arm, armH, fillOf('body'), 9 * s);
      el('path', { d: `M${x - 30} ${y + H + foot * s}H${x + W + 30}`, stroke: '#d6d3d1', 'stroke-width': 2 }, g);
      dimH(g, x, x + W, y + H + foot * s + 16, `${d.w} cm`);
      dimV(g, x + W + 22, y, y + H, `${d.h} cm`);
      note(g, `Oturma derinliği ${d.d} cm`);
    },

    // Perde: önden görünüm, pile kıvrımlarıyla
    curtain(g, d) {
      const { s, x, y } = fit(d.w + 20, d.h + 8);
      const cx = x + 10 * s, cy = y + 8 * s, W = d.w * s, H = d.h * s;
      // korniş
      el('rect', { x: x, y: y + 2 * s, width: (d.w + 20) * s, height: Math.max(4, 3 * s), rx: 2, fill: '#57534e' }, g);
      [x, x + (d.w + 20) * s].forEach((fx) => el('circle', { cx: fx, cy: y + 3.5 * s, r: Math.max(4, 3.5 * s), fill: '#57534e' }, g));
      const folds = Math.max(4, Math.round(d.w / 14)), fw = W / folds, wave = Math.min(8, fw * .35);
      let path = `M${cx} ${cy}H${cx + W}V${cy + H}`;
      for (let i = folds; i > 0; i--) path += `Q${cx + (i - .5) * fw} ${cy + H + (i % 2 ? wave : -wave)} ${cx + (i - 1) * fw} ${cy + H}`;
      path += 'Z';
      const body = el('g', { filter: 'url(#drop)' }, g);
      el('path', { d: path, fill: fillOf('curtain'), stroke: 'rgba(0,0,0,.18)' }, body);
      const clip = el('clipPath', { id: 'curtain-clip' }, g);
      el('path', { d: path }, clip);
      const fg = el('g', { 'clip-path': 'url(#curtain-clip)' }, body);
      for (let i = 0; i < folds; i++) el('rect', { x: cx + i * fw, y: cy, width: fw, height: H + wave, fill: 'url(#foldg)' }, fg);
      el('path', { d: `M${x - 20} ${cy + H + wave + 6}H${x + (d.w + 20) * s + 20}`, stroke: '#d6d3d1', 'stroke-width': 2 }, g);
      dimH(g, cx, cx + W, cy + H + wave + 24, `${d.w} cm`);
      dimV(g, cx + W + 10 * s + 20, cy, cy + H, `${d.h} cm`);
    },

    // Masa örtüsü: üstten görünüm
    table(g, d) {
      const tw = d.w + d.s * 2, tl = d.l + d.s * 2;
      // uzun kenar yatay dursun
      const { s, x, y } = fit(tl, tw);
      const W = tl * s, H = tw * s, o = d.s * s;
      const body = el('g', { filter: 'url(#drop)' }, g);
      box(body, x, y, W, H, fillOf('cloth'), Math.max(4, o * .6));
      if (d.s > 0) {
        el('rect', { x: x + o, y: y + o, width: d.l * s, height: d.w * s, rx: 4, fill: 'rgba(255,255,255,.14)', stroke: 'rgba(0,0,0,.35)', 'stroke-width': 1.3, 'stroke-dasharray': '6 5' }, body);
      }
      label(g, x + W / 2, y + H / 2 + 5, `Masa ${d.w} × ${d.l} cm`);
      dimH(g, x, x + W, y + H + 22, `${tl} cm`);
      dimV(g, x + W + 24, y, y + H, `${tw} cm`);
      note(g, d.s > 0 ? `Her kenardan ${d.s} cm sarkma` : 'Sarkma payı yok');
    },

    // Minder: üstten görünüm, biyeli
    cushion(g, d) {
      const { s, x, y } = fit(d.w, d.l);
      const W = d.w * s, H = d.l * s, r = Math.min(W, H) * .12;
      const body = el('g', { filter: 'url(#drop)' }, g);
      box(body, x, y, W, H, fillOf('main'), r);
      el('rect', { x: x + 2.5, y: y + 2.5, width: W - 5, height: H - 5, rx: r, fill: 'none', stroke: fillOf('piping'), 'stroke-width': 5 }, body);
      // kapitone düğmeleri
      const cols = Math.max(1, Math.round(d.w / 40)), rows = Math.max(1, Math.round(d.l / 40));
      for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
        el('circle', { cx: x + (W * (i + .5)) / cols, cy: y + (H * (j + .5)) / rows, r: 3.5, fill: fillOf('piping'), stroke: 'rgba(0,0,0,.25)' }, body);
      }
      dimH(g, x, x + W, y + H + 22, `${d.w} cm`);
      dimV(g, x + W + 24, y, y + H, `${d.l} cm`);
      note(g, `Kalınlık ${d.h} cm`);
    },
  };

  // ---------- Tahmini kumaş (m²) ----------
  const AREA = {
    nevresim: (d) => 2 * (d.w + 50) * (d.l + 20) + (d.w + 2 * d.h + 30) * (d.l + 2 * d.h + 30) + (d.w >= 130 ? 2 : 1) * 2 * 55 * 75,
    carsaf: (d) => (d.w + 2 * d.h + 30) * (d.l + 2 * d.h + 30) + (d.w >= 130 ? 2 : 1) * 2 * 55 * 75,
    yatak_ortusu: (d) => (d.w + 2 * (d.h + 25)) * (d.l + d.h + 25),
    koltuk: (d) => (d.w + 2 * d.d + 40) * (2 * d.h + d.d + 40),
    perde: (d) => d.w * 2.5 * (d.h + 25),
    masa: (d) => (d.w + 2 * d.s + 4) * (d.l + 2 * d.s + 4),
    minder: (d) => 2 * (d.w + 3) * (d.l + 3) + 2 * (d.w + d.l) * (d.h + 3),
  };
  const tl = (n) => new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 }).format(n) + ' ₺';

  // ---------- Çizim ----------
  let defsBuilt = false;
  function draw() {
    if (!defsBuilt) { buildDefs(); defsBuilt = true; }
    [...svg.children].forEach((c) => { if (c.tagName !== 'defs') c.remove(); });
    const g = el('g', {}, svg);
    SHAPES[state.item.shape](g, state.dims, state.item.kind);

    const m2 = AREA[state.item.kind](state.dims) / 10000;
    $('est-area').textContent = m2.toFixed(1).replace('.', ',') + ' m²';
    const priced = state.item.m2 !== null;
    $('est-price-row').hidden = !priced;
    if (priced) $('est-price').textContent = '≈ ' + tl(Math.round((state.item.base + m2 * state.item.m2) / 10) * 10);
    syncForm();
  }

  function summary() {
    const it = state.item;
    const dims = it.dims.map((d) => `${d.label}: ${state.dims[d.key]} cm`).join('\n');
    const parts = it.parts.map((p) => `${p.label}: ${colorById(state.parts[p.key]).name}`).join('\n');
    return `Merhaba, özel dikim için teklif almak istiyorum.\n\n${it.name}\n${dims}\n${parts}`;
  }

  function syncForm() {
    const form = $('request-form');
    form.elements.item.value = state.item.id;
    form.elements.dims.value = JSON.stringify(state.dims);
    form.elements.parts.value = JSON.stringify(state.parts);
    const wa = $('wa-send');
    if (wa) wa.href = `https://wa.me/${cfg.wa}?text=${encodeURIComponent(summary())}`;
  }

  // ---------- Kontroller ----------
  const clamp = (v, d) => Math.max(d.min, Math.min(d.max, Math.round(Number(v) || d.def)));

  function setDim(key, value, source) {
    const d = state.item.dims.find((x) => x.key === key);
    state.dims[key] = clamp(value, d);
    const range = $('r-' + key), num = $('n-' + key);
    if (range !== source) range.value = state.dims[key];
    if (num !== source) num.value = state.dims[key];
    draw();
  }

  function chip(text, on, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip' + (on ? ' on' : '');
    b.textContent = text;
    b.addEventListener('click', onClick);
    return b;
  }

  function selectItem(item) {
    state.item = item;
    state.dims = Object.fromEntries(item.dims.map((d) => [d.key, d.def]));
    // Parçalara farklı başlangıç renkleri ver ki ilk görüntü canlı dursun
    const prev = state.parts;
    state.parts = Object.fromEntries(item.parts.map((p, i) => [p.key, prev[p.key] ?? cfg.colors[i % cfg.colors.length].id]));

    $('items').replaceChildren(...cfg.items.map((it) => chip(it.name, it === item, () => selectItem(it))));
    $('items').parentElement.hidden = cfg.items.length < 2 && !item.desc;
    $('item-desc').textContent = item.desc;

    $('presets').replaceChildren(...item.presets.map((p) => chip(p.label, false, () => {
      for (const [k, v] of Object.entries(p.values)) setDim(k, v);
    })));

    const dims = $('dims');
    dims.replaceChildren();
    for (const d of item.dims) {
      const row = document.createElement('div');
      row.className = 'dim';
      row.innerHTML = `<label for="n-${d.key}">${d.label}</label>
        <input type="range" id="r-${d.key}" min="${d.min}" max="${d.max}" value="${d.def}" aria-label="${d.label}">
        <span class="num"><input type="number" id="n-${d.key}" min="${d.min}" max="${d.max}" value="${d.def}" inputmode="numeric"></span>`;
      dims.appendChild(row);
      const range = row.querySelector('input[type=range]'), num = row.querySelector('input[type=number]');
      range.addEventListener('input', () => setDim(d.key, range.value, range));
      num.addEventListener('input', () => { if (num.value !== '') setDim(d.key, num.value, num); });
      num.addEventListener('blur', () => setDim(d.key, num.value));
    }

    const parts = $('parts');
    parts.replaceChildren();
    for (const p of item.parts) {
      const wrap = document.createElement('div');
      wrap.className = 'part';
      const lbl = document.createElement('div');
      lbl.className = 'lbl';
      const name = document.createElement('span');
      lbl.append(p.label, name);
      const row = document.createElement('div');
      row.className = 'swatches';
      const refresh = () => {
        name.textContent = colorById(state.parts[p.key]).name;
        [...row.children].forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.id) === state.parts[p.key])));
      };
      for (const c of cfg.colors) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'sw';
        b.dataset.id = c.id;
        b.title = c.name;
        b.setAttribute('aria-label', `${p.label}: ${c.name}`);
        b.style.background = swatchCss(c);
        b.addEventListener('click', () => { state.parts[p.key] = c.id; refresh(); draw(); });
        row.appendChild(b);
      }
      wrap.append(lbl, row);
      parts.appendChild(wrap);
      refresh();
    }
    draw();
  }

  function swatchCss(c) {
    if (c.image) return `center / cover url("${c.image}")`;
    if (c.pattern === 'cizgili') return `repeating-linear-gradient(90deg, ${c.hex2} 0 5px, ${c.hex} 5px 12px)`;
    if (c.pattern === 'kareli') return `repeating-conic-gradient(${c.hex2} 0 25%, ${c.hex} 0 50%) 0 0 / 14px 14px`;
    if (c.pattern === 'puantiye') return `radial-gradient(${c.hex2} 2.5px, transparent 3px) 0 0 / 11px 11px ${c.hex}`;
    return c.hex;
  }

  selectItem(state.item);
})();
