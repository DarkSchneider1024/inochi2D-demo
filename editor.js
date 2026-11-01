// editor.js -- 圖層編輯 (2026-11-01, user: 把底圖放在圖層下面、手動修改圖層、切割底圖成新圖層、存回 Inochi2D).
// Everything here works on the REST pose: a Part's texture spans its mesh box 1:1 (uv 0..1), so editing a layer means
// editing that texture. A new layer clones the mesh and every binding of the layer it was made from, so it moves with it.
import { parseINP, buildINP, decodePNG, encodePNG } from './inp-io.js';
import { loadINP, Puppet, Renderer } from './inochi-full.js';

const $ = (id) => document.getElementById(id);
const cv = $('cv'), cx = cv.getContext('2d');
const NO_TEX = 4294967295, UNDO_MAX = 40, ZOOM_MAX = 64, GRID_AT = 8;
const flat = document.createElement('canvas'), fx = flat.getContext('2d');   // the layers, flattened: 圖層濃度 fades them as one
let M = null;                  // {id, json, textures, tail, layers (back -> front)}
let cur = null, tool = 'hand', sel = null, base = null, dirty = false, draft = null;
let view = { x: 0, y: 0, s: 1 }, need = false, cursor = null, soloOn = false, fitted = false, softSize = 24;
const undo = [], redo = [];
const ptrs = new Map();

const toast = (t) => { const e = $('toast'); e.textContent = t; e.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { e.hidden = true; }, 3500); };
const paint = () => { if (!need) { need = true; requestAnimationFrame(render); } };
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// ---- model -> layers ----------------------------------------------------------------------------------------------
function restValue(p, xs, values) {
  const mn = Array.isArray(p.min) ? p.min[0] : p.min, mx = Array.isArray(p.max) ? p.max[0] : p.max;
  const d = Array.isArray(p.defaults) ? p.defaults[0] : p.defaults, t = mx - mn ? (d - mn) / (mx - mn) : 0;
  const vs = values.map((v) => (Array.isArray(v) ? v[0] : v));
  if (t <= xs[0]) return vs[0];
  for (let i = 0; i < xs.length - 1; i++)
    if (xs[i] <= t && t <= xs[i + 1]) return vs[i] + (vs[i + 1] - vs[i]) * ((t - xs[i]) / Math.max(1e-9, xs[i + 1] - xs[i]));
  return vs[vs.length - 1];
}

function collect(json) {
  const op = new Map();
  for (const p of json.param) for (const b of p.bindings)
    if (b.param_name === 'opacity' && !p.is_vec2) {
      const v = restValue(p, p.axis_points[0], b.values.map((r) => r[0]));
      op.set(b.node, Math.min(op.get(b.node) ?? 1, v));
    }
  const out = [];
  const walk = (n, wx, wy, z, path, parent) => {
    const t = n.transform?.trans ?? [0, 0, 0];
    wx += t[0]; wy += t[1]; z += n.zsort ?? 0;
    if (n.type === 'Part') out.push(layerOf(n, parent, wx, wy, z, path, (n.opacity ?? 1) * (op.get(n.uuid) ?? 1) < 0.05));
    for (const c of n.children ?? []) walk(c, wx, wy, z, n.type === 'Node' && n.name !== 'Root' ? [...path, n.name] : path, n);
  };
  walk(json.nodes, 0, 0, 0, [], null);
  return out.sort((a, b) => b.z - a.z);
}

function layerOf(node, parent, wx, wy, z, group, hidden) {
  const L = { node, parent, wx, wy, z, group: Array.isArray(group) ? group.join('/') : group, hidden, on: !hidden, src: null, w: 0, h: 0, rgba: null, img: null, ctx: null, edited: false };
  setBox(L);
  return L;
}
function setBox(L) {
  const v = L.node.mesh.verts;
  let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
  for (let i = 0; i < v.length; i += 2) { a = Math.min(a, v[i]); c = Math.max(c, v[i]); b = Math.min(b, v[i + 1]); d = Math.max(d, v[i + 1]); }
  L.x0 = L.wx + a; L.y0 = L.wy + b; L.x1 = L.wx + c; L.y1 = L.wy + d;
}
const texOf = (L) => M.textures[L.node.textures[0]];
const toTex = (L, wx, wy) => [(wx - L.x0) * L.w / (L.x1 - L.x0), (wy - L.y0) * L.h / (L.y1 - L.y0)];

async function openModel(bytes, id) {
  $('hint').hidden = false; $('hint').textContent = '讀取模型中…';
  const { json, textures, tail } = parseINP(bytes);
  const layers = collect(json);
  await Promise.all(layers.map(async (L) => {
    L.src = await createImageBitmap(new Blob([textures[L.node.textures[0]].bytes], { type: 'image/png' }));
    L.w = L.src.width; L.h = L.src.height;
  }));
  M = { id, json, textures, tail, layers };
  cur = null; sel = null; undo.length = redo.length = 0; dirty = false;
  $('hint').hidden = true;
  for (const b of ['fit', 'zoomIn', 'zoomOut', 'preview', 'saveInp', 'saveInx']) $(b).disabled = false;
  fitView(); renderList(); select(layers.find((l) => !l.hidden) ?? layers[0]); syncButtons();
}

async function loadById(id) {
  try {
    const r = await fetch(`models/${id}.inp`, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`讀不到 models/${id}.inp`);
    await openModel(new Uint8Array(await r.arrayBuffer()), id);
    history.replaceState(null, '', `?model=${id}`);
  } catch (e) { $('hint').hidden = false; $('hint').textContent = e.message; }
}

// a layer's pixels: decoded only when first edited; the bitmap serves until then
async function ensure(L) {
  if (L.rgba) return;
  let d = await decodePNG(texOf(L).bytes);
  if (!d) {
    const c = new OffscreenCanvas(L.w, L.h), g = c.getContext('2d');
    g.drawImage(L.src, 0, 0);
    d = { w: L.w, h: L.h, rgba: g.getImageData(0, 0, L.w, L.h).data };
  }
  adopt(L, d.w, d.h, d.rgba);
}
function adopt(L, w, h, rgba) {
  L.w = w; L.h = h; L.rgba = rgba; L.img = new ImageData(rgba, w, h);
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  L.ctx = c.getContext('2d'); L.ctx.putImageData(L.img, 0, 0); L.src = c;
}
function touched(L, x = 0, y = 0, w = L.w, h = L.h) { L.ctx.putImageData(L.img, 0, 0, x, y, w, h); L.edited = true; dirty = true; paint(); }

// ---- undo ---------------------------------------------------------------------------------------------------------
function record(entry) { undo.push(entry); if (undo.length > UNDO_MAX) undo.shift(); redo.length = 0; syncButtons(); }
function fullState(L) { return { w: L.w, h: L.h, rgba: L.rgba.slice(), verts: L.node.mesh.verts.slice() }; }
function restore(L, s) {
  adopt(L, s.w, s.h, s.rgba.slice()); L.node.mesh.verts = s.verts.slice(); setBox(L); L.edited = true; drawThumb(L); paint();
}
function pixelEntry(L, before) { const after = fullState(L); return { undo: () => restore(L, before), redo: () => restore(L, after) }; }
function step(from, to) {
  const e = from.pop(); if (!e) return;
  (from === undo ? e.undo : e.redo)(); to.push(e); dirty = true; renderList(); syncSel(); syncButtons(); paint();
}

// ---- drawing ------------------------------------------------------------------------------------------------------
function render() {
  need = false;
  const dpr = devicePixelRatio || 1, r = cv.getBoundingClientRect(), W = Math.round(r.width * dpr), H = Math.round(r.height * dpr);
  if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
  if (flat.width !== W || flat.height !== H) { flat.width = W; flat.height = H; }
  cx.setTransform(1, 0, 0, 1, 0, 0); cx.clearRect(0, 0, W, H);
  if (!M) return;
  const T = [view.s * dpr, 0, 0, view.s * dpr, view.x * dpr, view.y * dpr];
  const smooth = view.s < 2;
  cx.imageSmoothingEnabled = smooth;
  cx.setTransform(...T);
  if (base) { cx.globalAlpha = +$('baseA').value / 100; cx.drawImage(base.c, base.x, base.y, base.c.width * base.s, base.c.height * base.s); cx.globalAlpha = 1; }
  fx.setTransform(1, 0, 0, 1, 0, 0); fx.clearRect(0, 0, W, H); fx.setTransform(...T); fx.imageSmoothingEnabled = smooth;
  for (const L of M.layers) if (soloOn ? L === cur : L.on || L === cur) fx.drawImage(L.src, L.x0, L.y0, L.x1 - L.x0, L.y1 - L.y0);
  cx.setTransform(1, 0, 0, 1, 0, 0); cx.globalAlpha = +$('layerA').value / 100; cx.drawImage(flat, 0, 0); cx.globalAlpha = 1;
  cx.setTransform(...T);
  cx.lineWidth = 1.5 / view.s;
  if (cur) { cx.strokeStyle = '#8a6fd1'; cx.setLineDash([6 / view.s, 4 / view.s]); cx.strokeRect(cur.x0, cur.y0, cur.x1 - cur.x0, cur.y1 - cur.y0); }
  if (cur && view.s >= GRID_AT) drawGrid(r.width, r.height);
  const pts = draft ?? sel?.pts;
  if (pts) {
    cx.beginPath(); pts.forEach((p, i) => (i ? cx.lineTo(p[0], p[1]) : cx.moveTo(p[0], p[1]))); cx.closePath();
    cx.setLineDash([]); cx.strokeStyle = '#fff'; cx.lineWidth = 3 / view.s; cx.stroke();
    cx.setLineDash([5 / view.s, 5 / view.s]); cx.strokeStyle = '#000'; cx.lineWidth = 1.5 / view.s; cx.stroke();
  }
  cx.setLineDash([]);
  if (cursor && tool === 'pixel' && cur) {
    const b = pixelBox(cur, cursor), k = cur.w / (cur.x1 - cur.x0);
    cx.lineWidth = 3 / view.s; cx.strokeStyle = '#fff'; cx.strokeRect(cur.x0 + b[0] / k, cur.y0 + b[1] / k, b[2] / k, b[2] / k);
    cx.lineWidth = 1 / view.s; cx.strokeStyle = '#000'; cx.strokeRect(cur.x0 + b[0] / k, cur.y0 + b[1] / k, b[2] / k, b[2] / k);
  }
  if (cursor && ['brush', 'erase', 'clone'].includes(tool)) {
    cx.beginPath(); cx.arc(cursor[0], cursor[1], +$('size').value / 2, 0, 7);
    cx.strokeStyle = '#fff'; cx.lineWidth = 3 / view.s; cx.stroke(); cx.strokeStyle = '#000'; cx.lineWidth = 1 / view.s; cx.stroke();
  }
}

function drawGrid(W, H) {                         // the current layer's own pixels, once they are big enough to aim at
  const L = cur, k = L.w / (L.x1 - L.x0);
  const left = Math.max(0, Math.floor((-view.x / view.s - L.x0) * k)), right = Math.min(L.w, Math.ceil(((W - view.x) / view.s - L.x0) * k));
  const top = Math.max(0, Math.floor((-view.y / view.s - L.y0) * k)), bottom = Math.min(L.h, Math.ceil(((H - view.y) / view.s - L.y0) * k));
  cx.beginPath();
  for (let x = left; x <= right; x++) { cx.moveTo(L.x0 + x / k, L.y0 + top / k); cx.lineTo(L.x0 + x / k, L.y0 + bottom / k); }
  for (let y = top; y <= bottom; y++) { cx.moveTo(L.x0 + left / k, L.y0 + y / k); cx.lineTo(L.x0 + right / k, L.y0 + y / k); }
  cx.setLineDash([]); cx.strokeStyle = 'rgba(0,0,0,.22)'; cx.lineWidth = 1 / view.s; cx.stroke();
}
function zoomBy(k) {
  const r = cv.getBoundingClientRect(), x = r.width / 2, y = r.height / 2, s = clamp(view.s * k, 0.05, ZOOM_MAX);
  view.x = x - (x - view.x) * (s / view.s); view.y = y - (y - view.y) * (s / view.s); view.s = s; paint();
}

function modelBox() {
  const on = M.layers.filter((l) => l.on);
  return [Math.min(...on.map((l) => l.x0)), Math.min(...on.map((l) => l.y0)), Math.max(...on.map((l) => l.x1)), Math.max(...on.map((l) => l.y1))];
}
function fitView() {
  const r = cv.getBoundingClientRect(), [a, b, c, d] = modelBox();
  fitted = r.width > 0 && r.height > 0;           // (a hidden page has no size: the ResizeObserver fits it when it shows)
  if (!fitted) return;
  view.s = Math.min(r.width / (c - a), r.height / (d - b)) * 0.94;
  view.x = (r.width - (c - a) * view.s) / 2 - a * view.s; view.y = (r.height - (d - b) * view.s) / 2 - b * view.s;
  paint();
}
function toWorld(e) { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left - view.x) / view.s, (e.clientY - r.top - view.y) / view.s]; }

// ---- selection ----------------------------------------------------------------------------------------------------
function setSelection(pts) {
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x = Math.floor(Math.min(...xs)), y = Math.floor(Math.min(...ys));
  const w = Math.ceil(Math.max(...xs)) - x + 1, h = Math.ceil(Math.max(...ys)) - y + 1;
  if (w < 3 || h < 3) { sel = null; syncSel(); return; }
  const c = new OffscreenCanvas(w, h), g = c.getContext('2d', { willReadFrequently: true });
  g.translate(-x, -y); g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fill();
  sel = { pts, x, y, w, h, a: g.getImageData(0, 0, w, h).data };
  syncSel();
}
function inSel(wx, wy) {                    // 0..1 (the outline is antialiased), 1 with no selection
  if (!sel) return 1;
  const x = Math.floor(wx - sel.x), y = Math.floor(wy - sel.y);
  return x < 0 || y < 0 || x >= sel.w || y >= sel.h ? 0 : sel.a[(y * sel.w + x) * 4 + 3] / 255;
}
function syncSel() {
  const on = !!sel && !!cur;
  $('fromBase').disabled = !on || !base;
  for (const b of ['cutLayer', 'copyLayer', 'clearSel']) $(b).disabled = !on;
  $('dropSel').disabled = !sel;
  $('followNote').textContent = cur ? `新圖層會複製「${cur.node.name}」的網格與全部綁定，動作跟著它走。` : '先選一個圖層，新圖層會跟著它動。';
}

// ---- base image ---------------------------------------------------------------------------------------------------
function showBaseScale() { $('baseS').value = Math.round(base.s * 100); $('baseSO').textContent = $('baseS').value; }
function setBase(c, x, y, s) {
  base = { c, x, y, s, px: c.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, c.width, c.height).data };
  showBaseScale();
  for (const b of ['baseFit', 'baseDrop']) $(b).disabled = false;
  syncSel(); paint();
}
function baseFit() {
  const [l, a, r, b] = modelBox();
  base.s = (b - a) / base.c.height; base.y = a; base.x = (l + r) / 2 - base.c.width * base.s / 2;
  showBaseScale(); paint();
}
function sampleBase(wx, wy, out) {          // bilinear, straight alpha; false outside the image
  const px = (wx - base.x) / base.s - 0.5, py = (wy - base.y) / base.s - 0.5, w = base.c.width, h = base.c.height;
  if (px < -0.5 || py < -0.5 || px > w - 0.5 || py > h - 0.5) return false;
  const x0 = clamp(Math.floor(px), 0, w - 1), y0 = clamp(Math.floor(py), 0, h - 1), x1 = Math.min(w - 1, x0 + 1), y1 = Math.min(h - 1, y0 + 1);
  const tx = clamp(px - x0, 0, 1), ty = clamp(py - y0, 0, 1), p = base.px;
  let r = 0, g = 0, b = 0, a = 0;
  const take = (x, y, k) => { const i = (y * w + x) * 4, al = p[i + 3] * k; r += p[i] * al; g += p[i + 1] * al; b += p[i + 2] * al; a += al; };
  take(x0, y0, (1 - tx) * (1 - ty)); take(x1, y0, tx * (1 - ty)); take(x0, y1, (1 - tx) * ty); take(x1, y1, tx * ty);
  if (a <= 0) { out[3] = 0; return true; }
  out[0] = r / a; out[1] = g / a; out[2] = b / a; out[3] = a;
  return true;
}

// ---- brush tools --------------------------------------------------------------------------------------------------
let stroke = null;
async function beginStroke(e) {
  const L = cur;
  await ensure(L);
  stroke = { L, before: fullState(L), src: L.rgba.slice(), mask: new Float32Array(L.w * L.h), last: null, tool, pen: e.pointerType === 'pen' };
  strokeTo(toWorld(e), e.pressure);
}
function strokeTo(w, pressure) {
  const s = stroke, pixel = s.tool === 'pixel', r = +$('size').value / 2 * (s.pen && !pixel ? Math.max(0.15, pressure) : 1);
  const a = s.last ?? w, d = Math.hypot(w[0] - a[0], w[1] - a[1]);
  const n = Math.max(1, Math.ceil(pixel ? d * s.L.w / (s.L.x1 - s.L.x0) : d / Math.max(0.5, r / 4)));
  for (let i = s.last ? 1 : 0; i <= n; i++) dab(a[0] + (w[0] - a[0]) * i / n, a[1] + (w[1] - a[1]) * i / n, r);
  s.last = w;
}
// 單格筆刷: an N x N block of the layer's own pixels, hard edged. It REPLACES what is there, so the colour and alpha the
// dropper read go back exactly (不透明 = the pixel's alpha).
function pixelBox(L, w) {
  const N = Math.round(+$('size').value), [u, v] = toTex(L, w[0], w[1]), back = Math.floor((N - 1) / 2);
  return [Math.floor(u) - back, Math.floor(v) - back, N];
}
function pixelDab(wx, wy) {
  const { L } = stroke, [bx, by, N] = pixelBox(L, [wx, wy]), k = L.w / (L.x1 - L.x0);
  const x0 = Math.max(0, bx), y0 = Math.max(0, by), x1 = Math.min(L.w - 1, bx + N - 1), y1 = Math.min(L.h - 1, by + N - 1);
  if (x1 < x0 || y1 < y0) { toast('畫到圖層範圍外了：到圖層分頁按「擴大範圍」'); return; }
  const c = $('color').value, lock = $('lockA').checked, al = Math.round(+$('flow').value * 2.55);
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    if (inSel(L.x0 + (x + 0.5) / k, L.y0 + (y + 0.5) / k) < 0.5) continue;
    const i = (y * L.w + x) * 4;
    for (let n = 0; n < 3; n++) L.rgba[i + n] = parseInt(c.slice(1 + n * 2, 3 + n * 2), 16);
    if (!lock) L.rgba[i + 3] = al;
  }
  touched(L, x0, y0, x1 - x0 + 1, y1 - y0 + 1);
}
function dab(wx, wy, r) {
  const { L, mask, src, tool: t } = stroke;
  if (t === 'pixel') return pixelDab(wx, wy);
  const [px0, py0] = toTex(L, wx, wy), k = L.w / (L.x1 - L.x0), R = Math.max(0.5, r * k);
  const x0 = Math.max(0, Math.floor(px0 - R)), x1 = Math.min(L.w - 1, Math.ceil(px0 + R));
  const y0 = Math.max(0, Math.floor(py0 - R)), y1 = Math.min(L.h - 1, Math.ceil(py0 + R));
  if (x1 < x0 || y1 < y0) { toast('畫到圖層範圍外了：到圖層分頁按「擴大範圍」'); return; }
  const hard = +$('hard').value / 100, op = +$('flow').value / 100, lock = $('lockA').checked;
  const c = $('color').value, cr = parseInt(c.slice(1, 3), 16), cg = parseInt(c.slice(3, 5), 16), cb = parseInt(c.slice(5, 7), 16);
  const px = L.rgba, b = [0, 0, 0, 0];
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const dist = Math.hypot(x + 0.5 - px0, y + 0.5 - py0) / R;
    if (dist >= 1) continue;
    let m = dist <= hard ? 1 : (1 - dist) / Math.max(1e-3, 1 - hard);
    const worldX = L.x0 + (x + 0.5) / k, worldY = L.y0 + (y + 0.5) * (L.y1 - L.y0) / L.h;
    m *= inSel(worldX, worldY);
    const mi = y * L.w + x;
    if (m <= mask[mi]) continue;
    mask[mi] = m;
    const i = mi * 4, ba = src[i + 3] / 255;
    let a = m * op;
    if (t === 'erase') { px[i + 3] = src[i + 3] * (1 - a); continue; }
    let sr = cr, sg = cg, sb = cb;
    if (t === 'clone') {
      if (!sampleBase(worldX, worldY, b)) continue;
      sr = b[0]; sg = b[1]; sb = b[2]; a *= b[3] / 255;
    }
    if (lock) {
      px[i] = src[i] + (sr - src[i]) * a; px[i + 1] = src[i + 1] + (sg - src[i + 1]) * a; px[i + 2] = src[i + 2] + (sb - src[i + 2]) * a;
      continue;
    }
    const oa = a + ba * (1 - a);
    if (oa <= 0) continue;
    px[i] = (sr * a + src[i] * ba * (1 - a)) / oa; px[i + 1] = (sg * a + src[i + 1] * ba * (1 - a)) / oa;
    px[i + 2] = (sb * a + src[i + 2] * ba * (1 - a)) / oa; px[i + 3] = oa * 255;
  }
  touched(L, x0, y0, x1 - x0 + 1, y1 - y0 + 1);
}
function endStroke() {
  if (!stroke) return;
  const { L, before } = stroke; stroke = null;
  record(pixelEntry(L, before)); drawThumb(L);
}

// ---- move the layer's content (or the selected part of it) -----------------------------------------------------------
let moving = null;
async function beginMove(e) {
  const L = cur;
  await ensure(L);
  const k = L.w / (L.x1 - L.x0), m = new Float32Array(L.w * L.h);
  for (let y = 0; y < L.h; y++) for (let x = 0; x < L.w; x++) m[y * L.w + x] = inSel(L.x0 + (x + 0.5) / k, L.y0 + (y + 0.5) / k);
  moving = { L, start: toWorld(e), before: fullState(L), src: L.rgba.slice(), m, k };
}
function moveTo(w) {
  const { L, start, src, m, k } = moving, dx = Math.round((w[0] - start[0]) * k), dy = Math.round((w[1] - start[1]) * k);
  const px = L.rgba; px.set(src);
  for (let i = 0; i < m.length; i++) px[i * 4 + 3] = src[i * 4 + 3] * (1 - m[i]);
  for (let y = 0; y < L.h; y++) for (let x = 0; x < L.w; x++) {
    const s = y * L.w + x, a = m[s] * src[s * 4 + 3] / 255, tx = x + dx, ty = y + dy;
    if (a <= 0 || tx < 0 || ty < 0 || tx >= L.w || ty >= L.h) continue;
    const i = (ty * L.w + tx) * 4, ba = px[i + 3] / 255, oa = a + ba * (1 - a);
    for (let c = 0; c < 3; c++) px[i + c] = (src[s * 4 + c] * a + px[i + c] * ba * (1 - a)) / oa;
    px[i + 3] = oa * 255;
  }
  touched(L);
}

// ---- layer operations -----------------------------------------------------------------------------------------------
function expand(L, l, t, r, b) {                  // the box grows, the texture stays 1:1, deform bindings stay per vertex
  const W = L.w + l + r, H = L.h + t + b, out = new Uint8ClampedArray(W * H * 4), v = L.node.mesh.verts;
  for (let y = 0; y < L.h; y++) out.set(L.rgba.subarray(y * L.w * 4, (y + 1) * L.w * 4), ((y + t) * W + l) * 4);
  const kx = (L.x1 - L.x0) / L.w, ky = (L.y1 - L.y0) / L.h, a = L.x0 - L.wx, c = L.y0 - L.wy;
  const oldW = L.x1 - L.x0, oldH = L.y1 - L.y0, newW = W * kx, newH = H * ky, nx = a - l * kx, ny = c - t * ky;
  for (let i = 0; i < v.length; i += 2) { v[i] = nx + (v[i] - a) / oldW * newW; v[i + 1] = ny + (v[i + 1] - c) / oldH * newH; }
  adopt(L, W, H, out); setBox(L); L.edited = true;
}

function insertAbove(L, ref) {
  M.layers.splice(M.layers.indexOf(ref) + 1, 0, L);
  L.parent.children.splice(L.parent.children.indexOf(ref.node) + 1, 0, L.node);
}
function removeLayer(L) {
  M.layers.splice(M.layers.indexOf(L), 1);
  L.parent.children.splice(L.parent.children.indexOf(L.node), 1);
  L.bindings = [];
  for (const p of M.json.param) {
    const gone = p.bindings.filter((b) => b.node === L.node.uuid);
    if (gone.length) { L.bindings.push([p, gone]); p.bindings = p.bindings.filter((b) => b.node !== L.node.uuid); }
  }
}
function restoreLayer(L, ref) { insertAbove(L, ref); for (const [p, bs] of L.bindings) p.bindings.push(...bs); }
function newUuid() {
  const used = new Set(); const w = (n) => { used.add(n.uuid); (n.children ?? []).forEach(w); }; w(M.json.nodes);
  let u; do { u = Math.floor(Math.random() * 2147483000) + 1000; } while (used.has(u));
  return u;
}

function makeLayer(ref, name) {
  const node = structuredClone(ref.node);
  delete node.children;
  node.uuid = newUuid(); node.name = name;
  const next = M.layers[M.layers.indexOf(ref) + 1];
  const lift = Math.min(0.001, next ? Math.max(1e-5, (ref.z - next.z) / 2) : 0.001);
  node.zsort = ref.node.zsort - lift;
  node.textures = [M.textures.length, NO_TEX, NO_TEX];
  M.textures.push({ enc: 0, bytes: new Uint8Array(0) });
  for (const p of M.json.param)
    p.bindings.push(...p.bindings.filter((b) => b.node === ref.node.uuid).map((b) => ({ ...structuredClone(b), node: node.uuid })));
  const L = layerOf(node, ref.parent, ref.wx, ref.wy, ref.z - lift, ref.group, ref.hidden);
  L.on = true;
  adopt(L, ref.w, ref.h, new Uint8ClampedArray(ref.w * ref.h * 4));
  insertAbove(L, ref);
  return L;
}

async function selectionToLayer(mode) {          // mode: base | cut | copy
  const ref = cur, s = sel;
  await ensure(ref);
  const before = fullState(ref), name = `${ref.node.name}_新${M.layers.length}`;
  const L = makeLayer(ref, name);
  const l = Math.max(0, Math.ceil(L.x0 - s.x)), t = Math.max(0, Math.ceil(L.y0 - s.y));
  const r = Math.max(0, Math.ceil(s.x + s.w - L.x1)), b = Math.max(0, Math.ceil(s.y + s.h - L.y1));
  if (mode === 'base' && l + t + r + b) expand(L, l, t, r, b);
  const k = L.w / (L.x1 - L.x0), rk = ref.w / (ref.x1 - ref.x0), o = [0, 0, 0, 0];
  for (let y = 0; y < L.h; y++) for (let x = 0; x < L.w; x++) {
    const wx = L.x0 + (x + 0.5) / k, wy = L.y0 + (y + 0.5) / k, m = inSel(wx, wy);
    if (m <= 0) continue;
    const i = (y * L.w + x) * 4;
    if (mode === 'base') {
      if (!sampleBase(wx, wy, o)) continue;
      L.rgba[i] = o[0]; L.rgba[i + 1] = o[1]; L.rgba[i + 2] = o[2]; L.rgba[i + 3] = o[3] * m;
    } else {
      const rx = Math.floor((wx - ref.x0) * rk), ry = Math.floor((wy - ref.y0) * rk);
      if (rx < 0 || ry < 0 || rx >= ref.w || ry >= ref.h) continue;
      const q = (ry * ref.w + rx) * 4;
      L.rgba[i] = ref.rgba[q]; L.rgba[i + 1] = ref.rgba[q + 1]; L.rgba[i + 2] = ref.rgba[q + 2]; L.rgba[i + 3] = ref.rgba[q + 3] * m;
      if (mode === 'cut') ref.rgba[q + 3] *= 1 - m;
    }
  }
  touched(L); if (mode === 'cut') touched(ref);
  const after = mode === 'cut' ? fullState(ref) : null;
  record({
    undo: () => { removeLayer(L); if (after) restore(ref, before); select(ref); },
    redo: () => { restoreLayer(L, ref); if (after) restore(ref, after); select(L); },
  });
  sel = null; renderList(); select(L);
  toast(`已建立「${name}」，動作跟著「${ref.node.name}」`);
}

async function clearSelection() {
  const L = cur; await ensure(L);
  const before = fullState(L), k = L.w / (L.x1 - L.x0);
  for (let y = 0; y < L.h; y++) for (let x = 0; x < L.w; x++) {
    const m = inSel(L.x0 + (x + 0.5) / k, L.y0 + (y + 0.5) / k);
    if (m > 0) L.rgba[(y * L.w + x) * 4 + 3] *= 1 - m;
  }
  touched(L); drawThumb(L); record(pixelEntry(L, before));
}

function reorder(dir) {                           // dir 1 = towards the front (the front has the smaller accumulated zsort)
  const i = M.layers.indexOf(cur), other = M.layers[i + dir];
  if (!other) return;
  const L = cur, dz = other.z - L.z + (dir > 0 ? -1e-5 : 1e-5), order = M.layers.slice(), next = order.slice();
  next.splice(i, 1); next.splice(i + dir, 0, L);
  const apply = (d, list) => { L.node.zsort += d; L.z += d; M.layers = list.slice(); renderList(); };
  apply(dz, next);
  record({ undo: () => apply(-dz, order), redo: () => apply(dz, next) });
  dirty = true; paint();
}

function layerAt(w) {
  const c = new OffscreenCanvas(1, 1), g = c.getContext('2d', { willReadFrequently: true });
  for (let i = M.layers.length - 1; i >= 0; i--) {
    const L = M.layers[i];
    if (!(L.on || L === cur) || w[0] < L.x0 || w[0] >= L.x1 || w[1] < L.y0 || w[1] >= L.y1) continue;
    const [x, y] = toTex(L, w[0], w[1]);
    g.clearRect(0, 0, 1, 1); g.drawImage(L.src, -Math.floor(x), -Math.floor(y));
    if (g.getImageData(0, 0, 1, 1).data[3] > 24) return L;
  }
  return null;
}
const hex = (r, g, b) => '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('');
function layerPixel(L, w) {                        // the layer's own stored value, colour under low alpha included
  if (!L?.rgba || w[0] < L.x0 || w[0] >= L.x1 || w[1] < L.y0 || w[1] >= L.y1) return null;
  const [u, v] = toTex(L, w[0], w[1]), x = Math.floor(u), y = Math.floor(v), i = (y * L.w + x) * 4, p = L.rgba;
  return { x, y, r: p[i], g: p[i + 1], b: p[i + 2], a: p[i + 3] };
}
function showPixel(w) {
  const e = $('px'), p = layerPixel(cur, w), top = layerAt(w);
  e.hidden = false; e.textContent = '';
  const add = (t) => e.append(t), sw = (c) => { const i = document.createElement('i'); i.style.background = c; add(i); };
  if (p) { sw(`rgba(${p.r},${p.g},${p.b},${p.a / 255})`); add(`${cur.node.name} (${p.x}, ${p.y}) ${hex(p.r, p.g, p.b)} RGB ${p.r},${p.g},${p.b} A ${p.a}（${Math.round(p.a / 2.55)}%）`); }
  else add(`${cur?.node.name ?? ''} 範圍外`);
  add(`／最上層：${top?.node.name ?? '無'}`);
}
// 附近色 (2026-11-01, user: 滴管點下去自動算周圍色號，可選加深或淡化): the colours around the picked pixel, dark to light
const NEAR_R = 8, NEAR_MAX = 7;
const luma = (c) => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
const rgbOf = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
let near = [];
function nearbyPixels(w) {
  const out = [], L = cur;
  if (layerPixel(L, w)?.a) {
    const [u, v] = toTex(L, w[0], w[1]), cx0 = Math.floor(u), cy0 = Math.floor(v);
    for (let y = Math.max(0, cy0 - NEAR_R); y <= Math.min(L.h - 1, cy0 + NEAR_R); y++)
      for (let x = Math.max(0, cx0 - NEAR_R); x <= Math.min(L.w - 1, cx0 + NEAR_R); x++) {
        const i = (y * L.w + x) * 4;
        if (L.rgba[i + 3] > 127) out.push([L.rgba[i], L.rgba[i + 1], L.rgba[i + 2]]);
      }
  }
  if (out.length >= 8) return out;
  const n = NEAR_R * 2 + 1, c = new OffscreenCanvas(n, n), g = c.getContext('2d', { willReadFrequently: true });
  g.translate(NEAR_R - Math.floor(w[0]), NEAR_R - Math.floor(w[1]));
  if (base) g.drawImage(base.c, base.x, base.y, base.c.width * base.s, base.c.height * base.s);
  for (const L2 of M.layers) if (L2.on || L2 === cur) g.drawImage(L2.src, L2.x0, L2.y0, L2.x1 - L2.x0, L2.y1 - L2.y0);
  const d = g.getImageData(0, 0, n, n).data;
  for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 127) out.push([d[i], d[i + 1], d[i + 2]]);
  return out;
}
function pickNear(w) {
  const groups = new Map(), me = rgbOf($('color').value);
  for (const p of nearbyPixels(w)) {
    const k = (p[0] >> 4) << 8 | (p[1] >> 4) << 4 | p[2] >> 4, s = groups.get(k) ?? [0, 0, 0, 0];
    s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; s[3]++; groups.set(k, s);
  }
  const dist = (c) => Math.hypot(c[0] - me[0], c[1] - me[1], c[2] - me[2]);
  near = [...groups.values()].map((s) => [s[0] / s[3], s[1] / s[3], s[2] / s[3]].map(Math.round))
    .sort((a, b) => dist(a) - dist(b)).slice(0, NEAR_MAX).sort((a, b) => luma(a) - luma(b));
  renderNear();
}
function renderNear() {
  const box = $('near'), now = $('color').value;
  box.textContent = '';
  for (const c of near) {
    const b = document.createElement('button'), h = hex(...c);
    b.style.background = h; b.title = h; b.setAttribute('aria-label', `使用 ${h}`); b.setAttribute('aria-pressed', h === now);
    b.onclick = () => { $('color').value = h; renderNear(); };
    box.append(b);
  }
}
function shade(dir) {                              // -1 加深, 1 淡化: the next nearby colour that way, else a small step
  const me = rgbOf($('color').value), l = luma(me);
  const hit = near.filter((c) => (luma(c) - l) * dir >= 4).sort((a, b) => (luma(a) - luma(b)) * dir)[0];
  const next = hit ?? me.map((v) => Math.round(dir < 0 ? v * 0.92 : v + (255 - v) * 0.1));
  $('color').value = hex(...next); renderNear();
}
function dropper(w) {
  const own = layerPixel(cur, w);
  if (own?.a) {                                    // the layer's pixel, alpha included; a transparent one falls through to the screen
    $('color').value = hex(own.r, own.g, own.b);
    $('flow').value = Math.max(1, Math.round(own.a / 2.55)); $('flowO').textContent = $('flow').value;
    return;
  }
  const c = new OffscreenCanvas(1, 1), g = c.getContext('2d', { willReadFrequently: true });
  g.translate(-Math.floor(w[0]), -Math.floor(w[1]));
  if (base) g.drawImage(base.c, base.x, base.y, base.c.width * base.s, base.c.height * base.s);
  for (const L of M.layers) if (L.on || L === cur) g.drawImage(L.src, L.x0, L.y0, L.x1 - L.x0, L.y1 - L.y0);
  const d = g.getImageData(0, 0, 1, 1).data;
  $('color').value = hex(d[0], d[1], d[2]);
}

// ---- layer list ---------------------------------------------------------------------------------------------------
function drawThumb(L) {
  const c = L.thumb; if (!c) return;
  const g = c.getContext('2d'), s = Math.min(c.width / L.w, c.height / L.h);
  g.clearRect(0, 0, c.width, c.height);
  g.drawImage(L.src, (c.width - L.w * s) / 2, (c.height - L.h * s) / 2, L.w * s, L.h * s);
}
function renderList() {
  const q = $('find').value.trim(), box = $('list');
  box.textContent = '';
  for (const L of M.layers.slice().reverse()) {
    L.row = null;
    if (q && !`${L.node.name} ${L.group}`.includes(q)) continue;
    const r = document.createElement('div'); r.className = 'row' + (L === cur ? ' sel' : ''); L.row = r;
    const c = document.createElement('input'); c.type = 'checkbox'; c.checked = L.on;
    c.setAttribute('aria-label', `顯示 ${L.node.name}`);
    c.onclick = (e) => { e.stopPropagation(); L.on = c.checked; paint(); };
    const t = document.createElement('canvas'); t.width = t.height = 60; L.thumb = t;
    const n = document.createElement('span'); n.className = 'nm'; n.textContent = L.node.name; n.title = L.group;
    r.append(c, t, n);
    if (L.hidden) { const h = document.createElement('span'); h.className = 'tag'; h.textContent = '表情／姿勢'; r.append(h); }
    r.onclick = () => select(L);
    box.append(r); drawThumb(L);
  }
}
function select(L) {
  if (cur?.row) cur.row.classList.remove('sel');
  cur = L;
  if (L?.row) L.row.classList.add('sel');
  $('rename').value = L ? L.node.name : '';
  syncButtons(); syncSel(); paint();
}
function syncButtons() {
  $('undo').disabled = !undo.length; $('redo').disabled = !redo.length;
  for (const b of ['up', 'down', 'grow', 'del', 'exportPng', 'importPng', 'rename']) $(b).disabled = !cur;
  $('baseComp').disabled = !M;
}

// ---- save -----------------------------------------------------------------------------------------------------------
async function buildBytes() {
  for (const L of M.layers) if (L.edited) { texOf(L).bytes = await encodePNG(L.w, L.h, L.rgba); L.edited = false; }
  const used = new Set(); const w = (n) => { if (n.type === 'Part') used.add(n.textures[0]); (n.children ?? []).forEach(w); }; w(M.json.nodes);
  const blank = await encodePNG(1, 1, new Uint8ClampedArray(4));
  const tex = M.textures.map((t, i) => (used.has(i) ? t : { enc: 0, bytes: blank }));      // (a deleted layer's slot: indices stay put)
  return buildINP(M.json, tex, M.tail);
}
async function save(ext) {
  const bytes = await buildBytes(), name = `${M.id}.${ext}`, blob = new Blob([bytes], { type: 'application/octet-stream' });
  if (window.showSaveFilePicker) {
    try {
      const h = await showSaveFilePicker({ suggestedName: name, types: [{ description: 'Inochi2D', accept: { 'application/octet-stream': [`.${ext}`] } }] });
      const s = await h.createWritable(); await s.write(blob); await s.close();
      dirty = false; toast(`已儲存 ${h.name}`);
    } catch (e) { if (e.name !== 'AbortError') toast(`存檔失敗：${e.message}`); }
    return;
  }
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 30000);
  dirty = false; toast(`已下載 ${name}`);
}

// ---- preview: the saved bytes in the real player -----------------------------------------------------------------------
let R = null, P = null, pvRun = false;
async function preview() {
  const url = URL.createObjectURL(new Blob([await buildBytes()]));
  $('dlg').showModal();
  const c = $('pv'), r = c.getBoundingClientRect(), dpr = devicePixelRatio || 1;
  c.width = r.width * dpr; c.height = r.height * dpr;
  R ??= new Renderer(c);
  P = new Puppet(await loadINP(url)); URL.revokeObjectURL(url);
  R.attach(P);
  const list = $('pvParam'); list.textContent = '';
  P.params.forEach((p, i) => { const o = document.createElement('option'); o.value = i; o.textContent = p.name; list.append(o); });
  syncParam();
  P.update();
  const b = P.bounds(), v = { cx: (b.x0 + b.x1) / 2, cy: (b.y0 + b.y1) / 2, scale: Math.min(c.width / (b.x1 - b.x0), c.height / (b.y1 - b.y0)) * 0.92 };
  pvRun = true;
  const loop = () => { if (!pvRun) return; P.update(); P.stepPhysics(1 / 60); R.draw(v); requestAnimationFrame(loop); };
  loop();
}
function syncParam() {
  const p = P.params[+$('pvParam').value];
  const set = (e, a) => { e.min = p.min[a]; e.max = p.max[a]; e.step = (p.max[a] - p.min[a]) / 100 || 0.01; e.value = p.value[a]; e.disabled = a === 1 && !p.is_vec2; };
  set($('pvX'), 0); set($('pvY'), 1);
}

// ---- input --------------------------------------------------------------------------------------------------------
let pan = null, pinch = null, drag = null;
function pinchState() {
  const [a, b] = [...ptrs.values()];
  return { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), mx: (a.clientX + b.clientX) / 2, my: (a.clientY + b.clientY) / 2 };
}
cv.addEventListener('pointerdown', async (e) => {
  if (!M) return;
  cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, e);
  if (ptrs.size === 2) {                    // a second finger: the view gesture wins, a stroke just started is dropped
    if (stroke) { restore(stroke.L, stroke.before); stroke = null; }
    moving = null; drag = null; draft = null; pan = null; pinch = pinchState(); return;
  }
  const w = toWorld(e);
  if (tool === 'hand' || e.button === 1) { pan = { x: e.clientX - view.x, y: e.clientY - view.y }; return; }
  if (['brush', 'pixel', 'erase', 'clone'].includes(tool)) {
    if (!cur) return toast('先選一個圖層');
    if (tool === 'clone' && !base) return toast('先到底圖分頁載入底圖');
    await beginStroke(e);
  } else if (tool === 'dropper') { if (cur) await ensure(cur); dropper(w); pickNear(w); showPixel(w); }
  else if (tool === 'layer') { const L = layerAt(w); if (L) { select(L); L.row?.scrollIntoView({ block: 'nearest' }); toast(L.node.name); } }
  else if (tool === 'rect' || tool === 'lasso') { drag = { o: w }; draft = [w]; }
  else if (tool === 'move') { if (cur) await beginMove(e); }
  else if (tool === 'movebase') { if (base) drag = { bx: base.x - w[0], by: base.y - w[1] }; else toast('先到底圖分頁載入底圖'); }
});
cv.addEventListener('pointermove', (e) => {
  if (!M) return;
  if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, e);
  const w = toWorld(e); cursor = w;
  if (pinch && ptrs.size === 2) {
    const n = pinchState(), r = cv.getBoundingClientRect(), k = n.d / pinch.d, s = clamp(view.s * k, 0.05, ZOOM_MAX);
    const ax = pinch.mx - r.left, ay = pinch.my - r.top, nx = n.mx - r.left, ny = n.my - r.top;
    view.x = nx - (ax - view.x) * (s / view.s); view.y = ny - (ay - view.y) * (s / view.s); view.s = s; pinch = n;
  } else if (pan) { view.x = e.clientX - pan.x; view.y = e.clientY - pan.y; }
  else if (stroke) strokeTo(w, e.pressure);
  else if (tool === 'dropper') { showPixel(w); if (ptrs.has(e.pointerId)) { dropper(w); pickNear(w); } }
  else if (moving) moveTo(w);
  else if (drag && tool === 'rect') { const o = drag.o; draft = [o, [w[0], o[1]], w, [o[0], w[1]]]; }
  else if (drag && tool === 'lasso') draft.push(w);
  else if (drag && tool === 'movebase') { base.x = w[0] + drag.bx; base.y = w[1] + drag.by; }
  paint();
});
function up(e) {
  ptrs.delete(e.pointerId);
  if (ptrs.size < 2) pinch = null;
  pan = null;
  endStroke();
  if (moving) { const { L, before } = moving; moving = null; drawThumb(L); record(pixelEntry(L, before)); }
  if (draft && drag) { if (draft.length > 2) setSelection(draft); draft = null; }
  drag = null; paint();
}
cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
cv.addEventListener('pointerleave', () => { cursor = null; paint(); });
cv.addEventListener('wheel', (e) => {
  if (!M) return;
  e.preventDefault();
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, s = clamp(view.s * Math.exp(-e.deltaY * 0.0015), 0.05, ZOOM_MAX);
  view.x = x - (x - view.x) * (s / view.s); view.y = y - (y - view.y) * (s / view.s); view.s = s; paint();
}, { passive: false });

document.querySelectorAll('[data-tool]').forEach((b) => { b.onclick = () => {
  const was = tool;
  tool = b.dataset.tool; document.querySelectorAll('[data-tool]').forEach((o) => o.setAttribute('aria-pressed', o === b));
  if (tool === 'pixel' && was !== 'pixel') { softSize = +$('size').value; setSize(1); }   // (each brush keeps its own size)
  if (tool !== 'pixel' && was === 'pixel') setSize(softSize);
  if (tool === 'dropper' && cur) ensure(cur); else $('px').hidden = true;
  paint();
}; });
document.querySelectorAll('[data-tab]').forEach((b) => { b.onclick = () => {
  document.querySelectorAll('[data-tab]').forEach((o) => o.setAttribute('aria-pressed', o === b));
  document.querySelectorAll('.pane').forEach((p) => p.classList.toggle('on', p.id === `tab-${b.dataset.tab}`));
}; });
function setSize(v) { const n = clamp(Math.round(v) || 1, 1, 200); $('size').value = n; $('sizeN').value = n; paint(); }
$('size').oninput = () => setSize(+$('size').value);
$('sizeN').onchange = () => setSize(+$('sizeN').value);
$('sizeD').onclick = () => setSize(+$('size').value - 1);
$('sizeU').onclick = () => setSize(+$('size').value + 1);
$('darker').onclick = () => shade(-1); $('lighter').onclick = () => shade(1);
$('color').oninput = renderNear;
$('zoomIn').onclick = () => zoomBy(2); $('zoomOut').onclick = () => zoomBy(0.5);
for (const [id, o] of [['hard', 'hardO'], ['flow', 'flowO'], ['baseA', 'baseAO'], ['layerA', 'layerAO']])
  $(id).oninput = () => { $(o).textContent = $(id).value; paint(); };
$('baseS').oninput = () => {
  $('baseSO').textContent = $('baseS').value;
  if (!base) return;
  const s = +$('baseS').value / 100, mx = base.x + base.c.width * base.s / 2, my = base.y + base.c.height * base.s / 2;
  base.s = s; base.x = mx - base.c.width * s / 2; base.y = my - base.c.height * s / 2; paint();
};
$('solo').onchange = () => { soloOn = $('solo').checked; paint(); };
$('find').oninput = renderList;
$('undo').onclick = () => step(undo, redo); $('redo').onclick = () => step(redo, undo);
$('fit').onclick = fitView;
$('openBtn').onclick = () => $('openFile').click();
$('openFile').onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try { await openModel(new Uint8Array(await f.arrayBuffer()), f.name.replace(/\.(inp|inx)$/i, '')); }
  catch (err) { $('hint').hidden = false; $('hint').textContent = err.message; }
};
$('model').onchange = () => { if ($('model').value) loadById($('model').value); };
$('saveInp').onclick = () => save('inp'); $('saveInx').onclick = () => save('inx');
$('preview').onclick = preview;
$('pvParam').onchange = syncParam;
const pvSet = () => { const p = P.params[+$('pvParam').value]; if (p.is_vec2) P.set(p.name, +$('pvX').value, +$('pvY').value); else P.set(p.name, +$('pvX').value); };
$('pvX').oninput = pvSet; $('pvY').oninput = pvSet;
$('pvReset').onclick = () => { P.reset(); syncParam(); };
$('pvClose').onclick = () => { pvRun = false; $('dlg').close(); };
$('fromBase').onclick = () => selectionToLayer('base');
$('cutLayer').onclick = () => selectionToLayer('cut');
$('copyLayer').onclick = () => selectionToLayer('copy');
$('clearSel').onclick = clearSelection;
$('dropSel').onclick = () => { sel = null; syncSel(); paint(); };
$('up').onclick = () => reorder(1); $('down').onclick = () => reorder(-1);
$('grow').onclick = async () => { const L = cur; await ensure(L); const b = fullState(L); expand(L, 40, 40, 40, 40); dirty = true; record(pixelEntry(L, b)); paint(); };
$('del').onclick = () => {
  const L = cur, i = M.layers.indexOf(L), ref = M.layers[i - 1] ?? M.layers[i + 1];
  removeLayer(L); dirty = true; renderList(); select(ref);
  record({ undo: () => { restoreLayer(L, ref); select(L); }, redo: () => { removeLayer(L); select(ref); } });
};
$('rename').onchange = () => { if (cur) { cur.node.name = $('rename').value; dirty = true; renderList(); select(cur); } };
$('exportPng').onclick = async () => {
  await ensure(cur);
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([await encodePNG(cur.w, cur.h, cur.rgba)], { type: 'image/png' }));
  a.download = `${cur.node.name}.png`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000);
};
$('importPng').onclick = () => $('pngFile').click();
$('pngFile').onchange = async (e) => {
  const f = e.target.files[0], L = cur; if (!f || !L) return; e.target.value = '';
  await ensure(L);
  const before = fullState(L), bm = await createImageBitmap(f), c = new OffscreenCanvas(L.w, L.h), g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(bm, 0, 0, L.w, L.h); L.rgba.set(g.getImageData(0, 0, L.w, L.h).data);
  touched(L); drawThumb(L); record(pixelEntry(L, before));
  if (bm.width !== L.w || bm.height !== L.h) toast(`圖片尺寸不同，已縮放成 ${L.w}×${L.h}`);
};
$('baseBtn').onclick = () => $('baseFile').click();
$('baseFile').onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return; e.target.value = '';
  const bm = await createImageBitmap(f), c = document.createElement('canvas'); c.width = bm.width; c.height = bm.height;
  c.getContext('2d', { willReadFrequently: true }).drawImage(bm, 0, 0);
  setBase(c, 0, 0, 1); if (M) baseFit();
};
$('baseFit').onclick = () => { if (base && M) baseFit(); };
$('baseDrop').onclick = () => { base = null; $('baseFit').disabled = $('baseDrop').disabled = true; syncSel(); paint(); };
$('baseComp').onclick = () => {                 // what the stage shows now (1:1 model px) becomes the base
  const on = M.layers.filter((l) => l.on || l === cur);
  const a = Math.floor(Math.min(...on.map((l) => l.x0))), b = Math.floor(Math.min(...on.map((l) => l.y0)));
  const c = document.createElement('canvas');
  c.width = Math.ceil(Math.max(...on.map((l) => l.x1))) - a; c.height = Math.ceil(Math.max(...on.map((l) => l.y1))) - b;
  const g = c.getContext('2d', { willReadFrequently: true });
  for (const L of on) g.drawImage(L.src, L.x0 - a, L.y0 - b, L.x1 - L.x0, L.y1 - L.y0);
  setBase(c, a, b, 1);
};
addEventListener('keydown', (e) => {
  if (e.target.matches('input[type=text]')) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? step(redo, undo) : step(undo, redo); }
});
addEventListener('beforeunload', (e) => { if (dirty) e.preventDefault(); });
new ResizeObserver(() => { if (M && !fitted) fitView(); paint(); }).observe(cv);

const ask = new URLSearchParams(location.search).get('model');
fetch('layers/models.json').then((r) => r.json()).then((list) => {
  for (const m of list) if (!m.private) { const o = document.createElement('option'); o.value = m.id; o.textContent = m.name; $('model').append(o); }
  if (ask) { $('model').value = ask; loadById(ask); }
});
