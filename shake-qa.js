// 逐格大晃動檢核 (2026-10-23): the frame-check of index.html's 📸 即時截圖, as a module for official.html (精緻展示作品).
// The analysis is index.html's, unchanged: 殘塊 = a piece of the figure apart from the body (or hanging on by a 1 px
// sliver) that the resting pose has no counterpart for; 破洞 = an enclosed gap round the head / neck bigger than any in
// the resting pose; 半透明重影 = see-through blobs (a drawing fading in over nothing).
//   import { showQA } from './shake-qa.js';
//   showQA({ title, file, list: [{ c, t, label, sweep }], ref: { c } });   // c = a canvas copy of the frame
// window.qa = { done, frames, bad, warn, list: [{ t, issues: [what] }] } for scripted runs (qa_official.py).

const QA_W = 480;
const maskCv = document.createElement('canvas'), maskCx = maskCv.getContext('2d', { willReadFrequently: true });
function maskOf(c, box, W = QA_W) {
  const s = W / box.w, w = W, h = Math.max(1, Math.round(box.h * s));
  if (maskCv.width !== w || maskCv.height !== h) { maskCv.width = w; maskCv.height = h; } else maskCx.clearRect(0, 0, w, h);
  maskCx.drawImage(c, box.x, box.y, box.w, box.h, 0, 0, w, h);
  const d = maskCx.getImageData(0, 0, w, h).data, a = new Uint8Array(w * h), part = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) { const al = d[i * 4 + 3]; a[i] = al > 40 ? 1 : 0; part[i] = al > 30 && al < 200 ? 1 : 0; }
  return { a, part, d, w, h, s };
}
function components(mask, want) {               // 4-connected components of pixels equal to `want`
  const { a, w, h } = mask, lab = new Int32Array(w * h).fill(-1), out = [], st = [];
  for (let i = 0; i < w * h; i++) {
    if (a[i] !== want || lab[i] >= 0) continue;
    const id = out.length; let n = 0, x0 = w, y0 = h, x1 = 0, y1 = 0, border = false, sx = 0, sy = 0;
    st.push(i); lab[i] = id;
    while (st.length) {
      const j = st.pop(), x = j % w, y = (j / w) | 0; n++; sx += x; sy += y;
      if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y;
      if (x === 0 || y === 0 || x === w - 1 || y === h - 1) border = true;
      for (const k of [x > 0 ? j - 1 : -1, x < w - 1 ? j + 1 : -1, y > 0 ? j - w : -1, y < h - 1 ? j + w : -1])
        if (k >= 0 && a[k] === want && lab[k] < 0) { lab[k] = id; st.push(k); }
    }
    out.push({ n, x0, y0, x1, y1, border, cx: sx / n, cy: sy / n });
  }
  return out;
}
function erode(mask) {                            // shave 1 px: a piece hanging on by a thin sliver comes loose
  const { a, w, h } = mask, b = new Uint8Array(w * h);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    b[i] = a[i] && a[i - 1] && a[i + 1] && a[i - w] && a[i + w] ? 1 : 0;
  }
  return { ...mask, a: b };
}
export function analyse(c, box, ref, W = QA_W) {
  const m = maskOf(c, box, W);
  const fg = components(m, 1).sort((p, q) => q.n - p.n);
  const main = fg[0] ? fg[0].n : 1;
  const thin = components(erode(m), 1).sort((p, q) => q.n - p.n).slice(1).filter((p) => p.n >= 20);
  const islands = [...fg.slice(1).filter((p) => p.n >= 6),
    ...thin.filter((t) => !fg.slice(1).some((p) => Math.abs(p.cx - t.cx) < 6 && Math.abs(p.cy - t.cy) < 6)).map((t) => ({ ...t, thin: true }))];
  const holes = components(m, 0).filter((p) => !p.border && p.n >= 24 && p.cy < m.h * 0.34);   // head / neck only
  const ghosts = components(erode(erode({ ...m, a: m.part })), 1).filter((p) => p.n >= Math.max(16, 0.0015 * main));
  if (!ref) return { m, islands, holes, ghosts, main };
  const issues = [];
  for (const p of islands) {
    const known = ref.islands.some((q) => q.n >= p.n * 0.4 && q.n <= p.n * 2.5 && Math.hypot(q.cx - p.cx, q.cy - p.cy) < m.w * 0.18);
    if (!known) issues.push({ kind: 'bad', what: p.thin ? '殘塊（快斷開）' : '殘塊', p });
  }
  const refHole = Math.max(0, ...ref.holes.map((q) => q.n));
  for (const p of holes) if (p.n > Math.max(48, refHole * 1.6)) issues.push({ kind: 'warn', what: '破洞', p });
  for (const p of ghosts) {
    const known = (ref.ghosts || []).some((q) => q.n >= p.n * 0.4 && q.n <= p.n * 2.5 && Math.hypot(q.cx - p.cx, q.cy - p.cy) < m.w * 0.08);
    if (!known) issues.push({ kind: 'warn', what: '半透明重影', p });
  }
  return { m, islands, holes, ghosts, main, issues };
}
export function unionBox(list) {                  // crop all frames to the area the figure ever covers
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  for (const f of list) {
    const c = f.c, w = c.width, h = c.height, sc = Math.max(1, Math.round(w / 480));
    const t = document.createElement('canvas'); t.width = Math.ceil(w / sc); t.height = Math.ceil(h / sc);
    const x = t.getContext('2d', { willReadFrequently: true }); x.drawImage(c, 0, 0, t.width, t.height);
    const d = x.getImageData(0, 0, t.width, t.height).data;
    for (let y = 0; y < t.height; y++) for (let k = 0; k < t.width; k++) if (d[(y * t.width + k) * 4 + 3] > 20) {
      if (k < x0) x0 = k; if (k > x1) x1 = k; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    f.sc = sc;
  }
  const sc = list[0].sc, pad = 12;
  if (x1 < 0) return { x: 0, y: 0, w: list[0].c.width, h: list[0].c.height };
  const x = Math.max(0, x0 * sc - pad), y = Math.max(0, y0 * sc - pad);
  return { x, y, w: Math.min(list[0].c.width - x, (x1 - x0 + 1) * sc + 2 * pad), h: Math.min(list[0].c.height - y, (y1 - y0 + 1) * sc + 2 * pad) };
}
export function grab(canvas) {                    // a copy of the frame just drawn (the renderer keeps its buffer)
  const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height;
  c.getContext('2d').drawImage(canvas, 0, 0);
  return c;
}

// ---------------------------------------------------------------- the review overlay (built on first use)
const CSS = `
.sqa { position: fixed; inset: 0; z-index: 50; background: rgba(20,14,28,.72); display: none; padding: 24px; overflow: auto; }
.sqa.open { display: block; }
.sqa-box { max-width: 1280px; margin: 0 auto; background: var(--bg, #f7efe8); color: var(--ink, #2d2436); border-radius: 16px; padding: 18px 20px 22px; }
.sqa-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }
.sqa-head h3 { margin: 0 auto 0 0; font-size: 17px; }
.sqa button { font: inherit; font-size: 13px; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--line, rgba(60,40,80,.2));
  background: var(--card, #fff); color: inherit; cursor: pointer; }
.sqa button[aria-pressed="true"] { border-color: var(--accent, #8a6fd1); color: var(--accent, #8a6fd1); }
.sqa-sum { color: var(--muted, #6f6479); font-size: 13px; margin: 0 0 12px; }
.sqa-sum b.bad { color: #d9364a; } .sqa-sum b.ok { color: #2e9a5b; }
.sqa-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.sqa-cell { background: var(--card, #fff); border: 2px solid var(--line, rgba(60,40,80,.14)); border-radius: 10px; padding: 4px; cursor: zoom-in; }
.sqa-cell.bad { border-color: #d9364a; } .sqa-cell.warn { border-color: #e2a400; }
.sqa-cell canvas { position: static; inset: auto; width: 100%; height: auto; display: block; border-radius: 6px;
  background: repeating-conic-gradient(#e9e4ee 0 25%, #fff 0 50%) 0 0 / 16px 16px; }
.sqa-cell small { display: block; font-size: 11px; line-height: 1.35; color: var(--muted, #6f6479); padding: 3px 2px 0; font-variant-numeric: tabular-nums; }
.sqa-cell small b { color: #d9364a; font-weight: 600; } .sqa-cell small i { color: #b88400; font-style: normal; }
.sqa-big { position: fixed; inset: 0; z-index: 60; background: rgba(10,8,14,.9); display: none; align-items: center; justify-content: center; flex-direction: column; gap: 10px; }
.sqa-big.open { display: flex; }
.sqa-big canvas { position: static; inset: auto; max-width: 94vw; max-height: 82vh; width: auto; height: auto; object-fit: contain; background: repeating-conic-gradient(#e9e4ee 0 25%, #fff 0 50%) 0 0 / 20px 20px; border-radius: 8px; }
.sqa-big .bar { display: flex; gap: 8px; color: #fff; align-items: center; flex-wrap: wrap; justify-content: center; font-size: 13px; }
.sqa-big .bar b { color: #ff8a9a; } .sqa-big .bar i { color: #ffd166; font-style: normal; }
.sqa-big .bar button { color: #fff; background: transparent; border-color: rgba(255,255,255,.4); }
@media (max-width: 760px) { .sqa { padding: 10px; } .sqa-box { padding: 12px; } }`;

let ui = null, st = null;
function build() {
  const style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);
  const root = document.createElement('div');
  root.innerHTML = `
  <div class="sqa"><div class="sqa-box">
    <div class="sqa-head"><h3 data-k="title"></h3>
      <button data-k="all" aria-pressed="true">全部</button><button data-k="bad" aria-pressed="false">只看有疑點</button>
      <button data-k="sheet">⬇ 總表</button><button data-k="again">↻ 再跑一次</button><button data-k="close">✕ 關閉</button></div>
    <p class="sqa-sum" data-k="sum"></p>
    <div class="sqa-grid" data-k="grid"></div>
  </div></div>
  <div class="sqa-big"><canvas data-k="bigc"></canvas>
    <div class="bar"><button data-k="prev">‹ 上一張</button><span data-k="lab"></span><button data-k="next">下一張 ›</button>
      <button data-k="dl">⬇ 存這張</button><button data-k="bclose">✕</button></div></div>`;
  document.body.appendChild(root);
  const q = (k) => root.querySelector(`[data-k="${k}"]`);
  ui = { qa: root.querySelector('.sqa'), big: root.querySelector('.sqa-big'), q };
  q('all').onclick = () => { st.onlyBad = false; renderGrid(); };
  q('bad').onclick = () => { st.onlyBad = true; renderGrid(); };
  q('close').onclick = () => ui.qa.classList.remove('open');
  q('again').onclick = () => { ui.qa.classList.remove('open'); if (st.again) st.again(); };
  q('prev').onclick = () => openBig(st.idx - 1);
  q('next').onclick = () => openBig(st.idx + 1);
  q('bclose').onclick = () => ui.big.classList.remove('open');
  ui.big.addEventListener('click', (e) => { if (e.target === ui.big) ui.big.classList.remove('open'); });
  q('dl').onclick = () => { const f = st.view[st.idx]; download(full(f), `${st.file}_shake_${f.t.toFixed(1)}s.png`); };
  q('sheet').onclick = sheet;
  addEventListener('keydown', (e) => {
    if (ui.big.classList.contains('open')) {
      if (e.key === 'Escape') ui.big.classList.remove('open');
      if (e.key === 'ArrowLeft') openBig(st.idx - 1);
      if (e.key === 'ArrowRight') openBig(st.idx + 1);
      e.stopImmediatePropagation();
    } else if (ui.qa.classList.contains('open') && e.key === 'Escape') ui.qa.classList.remove('open');
  }, true);
}
function drawMarks(x, f, s) {                     // red / yellow boxes round the suspects (s = canvas px per mask px)
  for (const it of f.res.issues || []) {
    const p = it.p, r = Math.max(6, 4 * s);
    x.lineWidth = Math.max(2, s * 0.9); x.strokeStyle = it.kind === 'bad' ? '#ff2a44' : '#ffb300';
    x.strokeRect(p.x0 * s - r, p.y0 * s - r, (p.x1 - p.x0 + 1) * s + 2 * r, (p.y1 - p.y0 + 1) * s + 2 * r);
  }
}
function countWhat(issues) {
  const o = {};
  for (const i of issues) { const k = i.what.replace('（快斷開）', ''); o[k] = (o[k] || 0) + 1; }
  return o;
}
function label(f) {
  const bad = f.res.issues.filter((i) => i.kind === 'bad').length;
  const warns = Object.entries(countWhat(f.res.issues.filter((i) => i.kind !== 'bad'))).map(([k, n]) => `${k} ×${n}`).join('　');
  return `${f.t.toFixed(1)}s${f.sweep ? '［極限］' : ''}　${f.label || ''}` +
         (bad ? `<br><b>殘塊 ×${bad}</b>` : '') + (warns ? `${bad ? '　' : '<br>'}<i>${warns}</i>` : '');
}
function thumb(f, w) {
  const b = st.box, c = document.createElement('canvas'), s = w / b.w; c.width = w; c.height = Math.round(b.h * s);
  const x = c.getContext('2d'); x.drawImage(f.c, b.x, b.y, b.w, b.h, 0, 0, c.width, c.height);
  drawMarks(x, f, w / QA_W);
  return c;
}
function full(f) { return thumb(f, st.box.w); }
function renderGrid() {
  const g = ui.q('grid'); g.innerHTML = '';
  st.view = st.onlyBad ? st.list.filter((f) => f.res.issues.length) : st.list;
  st.view.forEach((f, i) => {
    const d = document.createElement('div');
    d.className = 'sqa-cell' + (f.res.issues.some((x) => x.kind === 'bad') ? ' bad' : f.res.issues.length ? ' warn' : '');
    d.appendChild(thumb(f, 300));
    const sm = document.createElement('small'); sm.innerHTML = label(f); d.appendChild(sm);
    d.onclick = () => openBig(i); g.appendChild(d);
  });
  if (!st.view.length) g.innerHTML = '<p class="sqa-sum">沒有疑點。</p>';
  ui.q('all').setAttribute('aria-pressed', !st.onlyBad);
  ui.q('bad').setAttribute('aria-pressed', st.onlyBad);
}
function openBig(i) {
  st.idx = (i + st.view.length) % st.view.length;
  const f = st.view[st.idx], c = ui.q('bigc'), b = st.box;
  c.width = b.w; c.height = b.h;
  const x = c.getContext('2d'); x.clearRect(0, 0, c.width, c.height);
  x.drawImage(f.c, b.x, b.y, b.w, b.h, 0, 0, b.w, b.h);
  drawMarks(x, f, b.w / QA_W);
  ui.q('lab').innerHTML = `${st.idx + 1} / ${st.view.length}　` + label(f).replace('<br>', '　');
  ui.big.classList.add('open');
}
function download(c, name) {
  c.toBlob((b) => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); }, 'image/png');
}
function sheet() {                                // every frame on one contact sheet, labelled, marks included
  const cols = 8, tw = 240, list = st.list, th = Math.round(st.box.h * tw / st.box.w), lh = 34, head = 56;
  const c = document.createElement('canvas'); c.width = cols * tw; c.height = head + Math.ceil(list.length / cols) * (th + lh);
  const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = '#2d2436'; x.font = 'bold 22px system-ui, "Microsoft JhengHei", sans-serif';
  x.fillText(`${st.title} · ${new Date().toLocaleString()}`, 12, 34);
  list.forEach((f, i) => {
    const gx = (i % cols) * tw, gy = head + Math.floor(i / cols) * (th + lh);
    const bad = f.res.issues.some((q) => q.kind === 'bad'), warn = f.res.issues.length && !bad;
    x.fillStyle = bad ? '#ffe3e7' : warn ? '#fff4d6' : '#f3f0f6'; x.fillRect(gx + 2, gy + 2, tw - 4, th + lh - 4);
    x.drawImage(thumb(f, tw), gx, gy);
    x.fillStyle = bad ? '#d9364a' : warn ? '#9a7000' : '#555'; x.font = '13px system-ui, "Microsoft JhengHei", sans-serif';
    x.fillText(`${f.t.toFixed(1)}s ${f.sweep ? '極限 ' : ''}${f.label || ''}`.slice(0, 34), gx + 6, gy + th + 14);
    if (f.res.issues.length) x.fillText(f.res.issues.map((q) => q.what).join('、'), gx + 6, gy + th + 29);
  });
  download(c, `${st.file}_shake_contact_sheet.png`);
}

// list: [{ c, t, label, sweep }], ref: { c } (the resting pose); again: re-run callback
export function showQA({ title, file, list, ref, again, note = '' }) {
  if (!ui) build();
  const box = unionBox([ref, ...list]);
  const r0 = analyse(ref.c, box, null);
  for (const f of list) f.res = analyse(f.c, box, r0);
  st = { title, file, list, box, again, onlyBad: false, idx: 0, view: list };
  const bad = list.filter((f) => f.res.issues.some((i) => i.kind === 'bad')).length;
  const warn = list.filter((f) => f.res.issues.length && !f.res.issues.some((i) => i.kind === 'bad')).length;
  ui.q('title').textContent = title;
  ui.q('sum').innerHTML = `共 ${list.length} 張。${note}` +
    (bad || warn ? `疑似<b class="bad">殘塊 ${bad} 張</b>、<b class="bad">破洞／重影 ${warn} 張</b>（紅框＝跟身體分離、或只剩細細一條連著的碎片；黃框＝頭頸附近比站姿多出來的封閉空洞，或半透明重影）。點縮圖放大確認，自動檢查只是幫忙找，最後請用眼睛看。`
                 : `<b class="ok">自動檢查沒有找到殘塊、破洞或重影</b>。還是建議點幾張放大看看接縫（脖子、髮際、手肘）。`) +
    '參考站姿：檢核開始前的靜止畫面。';
  renderGrid();
  ui.qa.classList.add('open');
  window.qa = { done: true, frames: list.length, bad, warn,
                list: list.filter((f) => f.res.issues.length).map((f) => ({ t: +f.t.toFixed(2), sweep: !!f.sweep, label: f.label || '',
                                                                           issues: f.res.issues.map((i) => i.what) })) };
  return window.qa;
}
