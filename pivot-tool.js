// 支點與新動作 (2026-11-02 user: 新增一個可以調整各種動作支點的按鈕，定位後可以儲存新動作).
// Pick a body part, tap the stage to place its pivot, turn or move it, record key poses, save them as a new action. The pose is
// laid on the finished vertices (n.pos) just before drawing, so the model file and its parameters stay as they are.
// Saved in this browser (localStorage), per model; 匯出 gives a JSON file to carry to another device or to bake into the model.
const $ = (id) => document.getElementById(id);
const PRESETS = [['畫面左手臂', /手臂_R/], ['畫面右手臂', /手臂_L/], ['畫面左腿', /(^|_)腿_R$|跪_腳_R|跪_小腿_R/], ['畫面右腿', /(^|_)腿_L$|跪_腳_L|跪_小腿_L/],
  ['跪姿左小腿', /跪_小腿_R/], ['跪姿右小腿', /跪_小腿_L/], ['尾巴', /^貓尾|尾/], ['耳朵', /貓耳|耳/], ['後髮', /^後髮/], ['側髮', /^側髮/], ['裙子', /裙/]];
const sm = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };

const st = { puppet: null, placing: false, playing: null, t0: 0, tracks: [], edit: { names: [], pivot: null, soft: 60, a: 0, dx: 0, dy: 0, keys: [], label: '' } };
const key = () => 'pivot-actions:' + (window.demo.modelId || 'model');
const load = () => { try { return JSON.parse(localStorage.getItem(key())) || []; } catch { return []; } };
const store = (list) => { try { localStorage.setItem(key(), JSON.stringify(list)); return true; } catch { return false; } };

function pose(track, a, dx, dy, P) {
  const set = new Set(track.names), c = Math.cos(a * Math.PI / 180), s = Math.sin(a * Math.PI / 180), [px, py] = track.pivot;
  for (const n of P.parts) {
    if (!set.has(n.name) || !n.pos) continue;
    const p = n.pos;
    for (let i = 0; i < p.length; i += 2) {
      const x = p[i] - px, y = p[i + 1] - py, w = track.soft > 0 ? sm(Math.hypot(x, y) / track.soft) : 1;
      p[i] += (c * x - s * y - x) * w + dx * w;
      p[i + 1] += (s * x + c * y - y) * w + dy * w;
    }
  }
}
function sample(keys, t) {
  if (!keys.length) return { a: 0, dx: 0, dy: 0 };
  if (t <= keys[0].t) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i].t) {
      const u = sm((t - keys[i - 1].t) / Math.max(1e-6, keys[i].t - keys[i - 1].t)), q = keys[i - 1], r = keys[i];
      return { a: q.a + (r.a - q.a) * u, dx: q.dx + (r.dx - q.dx) * u, dy: q.dy + (r.dy - q.dy) * u };
    }
  }
  return keys[keys.length - 1];
}
// called every frame between P.update() and R.draw()
window.__pivotApply = () => {
  const P = window.demo?.puppet;
  if (!P) return;
  if (P !== st.puppet) { st.puppet = P; st.playing = null; st.tracks = []; resetEdit(); fillParts(); listSaved(); }
  if (st.playing) {
    const dur = Math.max(0.1, st.playing.dur), t = ((performance.now() - st.t0) / 1000) % dur;
    for (const tr of st.playing.tracks) { const k = sample(tr.keys, t); pose(tr, k.a, k.dx, k.dy, P); }
  } else if (!$('pivotSec')?.hidden && st.edit.pivot && st.edit.names.length) {
    for (const tr of st.tracks) { const k = sample(tr.keys, 0); pose(tr, k.a, k.dx, k.dy, P); }
    pose(st.edit, st.edit.a, st.edit.dx, st.edit.dy, P);
  }
  mark();
};

function resetEdit() { Object.assign(st.edit, { names: [], pivot: null, a: 0, dx: 0, dy: 0, keys: [], label: '' }); syncSliders(); showKeys(); }
function syncSliders() { for (const k of ['a', 'dx', 'dy', 'soft']) { if ($('pv_' + k)) { $('pv_' + k).value = st.edit[k]; $('pv_' + k + 'V').textContent = st.edit[k]; } } }
function fillParts() {
  const P = window.demo.puppet, box = $('pvPresets');
  box.textContent = '';
  for (const [label, re] of PRESETS) {
    const names = P.parts.map((n) => n.name).filter((n) => re.test(n));
    if (!names.length) continue;
    const b = document.createElement('button');
    b.textContent = label;
    b.onclick = () => { commitEdit(); st.edit.names = names; st.edit.label = label; for (const x of box.children) x.setAttribute('aria-pressed', x === b); $('pvHint').textContent = `已選 ${label}（${names.length} 層），點「定位支點」再點畫面。`; };
    box.appendChild(b);
  }
  const sel = $('pvLayer');
  sel.textContent = '';
  sel.add(new Option('或選單一圖層…', ''));
  for (const n of [...new Set(P.parts.map((p) => p.name))]) sel.add(new Option(n, n));
}
function commitEdit() {                    // the part being edited joins the action when it has key poses
  if (st.edit.keys.length && st.edit.pivot) st.tracks.push({ label: st.edit.label, names: st.edit.names, pivot: st.edit.pivot, soft: st.edit.soft, keys: st.edit.keys });
  resetEdit();
  showKeys();
}
function showKeys() {
  const b = $('pvKeys');
  if (!b) return;
  const parts = st.tracks.map((t) => `${t.label}（${t.keys.length} 格）`);
  b.textContent = (parts.length ? '已完成：' + parts.join('、') + '。' : '') + (st.edit.keys.length ? `目前 ${st.edit.label}：` + st.edit.keys.map((k) => `${k.t}s ${k.a}°`).join('、') : '');
}
function mark() {
  const m = $('pvMark'), v = window.demo?.view, c = $('cv');
  if (!m) return;
  const p = st.edit.pivot;
  if (!p || $('pivotSec').hidden || !v) { m.style.display = 'none'; return; }
  const r = c.getBoundingClientRect(), sx = 2 * v.scale / c.width, sy = 2 * v.scale / c.height;
  m.style.display = 'block';
  m.style.left = ((p[0] - v.cx) * sx + 1) / 2 * r.width + 'px';
  m.style.top = ((p[1] - v.cy) * sy + 1) / 2 * r.height + 'px';
}
function nudge(dx, dy) { if (st.edit.pivot) { st.edit.pivot = [st.edit.pivot[0] + dx, st.edit.pivot[1] + dy]; } }
function listSaved() {
  const box = $('pvSaved');
  if (!box) return;
  box.textContent = '';
  load().forEach((act, i) => {
    const row = document.createElement('div'); row.className = 'row';
    const mk = (t, f) => { const b = document.createElement('button'); b.textContent = t; b.onclick = f; row.appendChild(b); };
    mk('▶ ' + act.name, () => { st.playing = st.playing === act ? null : act; st.t0 = performance.now(); });
    mk('匯出', () => download(act));
    mk('刪除', () => { const l = load(); l.splice(i, 1); store(l); st.playing = null; listSaved(); });
    box.appendChild(row);
  });
}
function download(act) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(act, null, 1)], { type: 'application/json' }));
  a.download = act.name + '.json';
  a.click();
}

export function init() {
  const anchor = $('scriptSec');
  anchor.insertAdjacentHTML('beforebegin', `<button id="pvOpen" aria-pressed="false">🦴 支點與新動作</button>
  <div id="pivotSec" hidden><h3>支點與新動作</h3>
   <div class="row" id="pvPresets"></div><div class="row"><select id="pvLayer"></select></div>
   <p id="pvHint">先選部位。</p>
   <div class="row"><button id="pvPlace" aria-pressed="false">📍 定位支點</button><button id="pvL">◀</button><button id="pvU">▲</button><button id="pvD">▼</button><button id="pvR">▶</button></div>
   ${[['a', '旋轉 °', -180, 180, 1], ['dx', '左右移動', -300, 300, 1], ['dy', '上下移動', -300, 300, 1], ['soft', '支點柔邊', 0, 400, 5]].map(([k, l, a, b, s]) => `<label>${l} <span id="pv_${k}V">0</span><input id="pv_${k}" type="range" min="${a}" max="${b}" step="${s}" value="0" style="width:100%"></label>`).join('')}
   <div class="row"><label>時間（秒）<input id="pvT" type="number" min="0" step="0.1" value="0" style="width:5em"></label><button id="pvKey">＋ 記錄這一格</button><button id="pvUndo">刪最後一格</button></div>
   <p id="pvKeys"></p>
   <div class="row"><button id="pvNext">完成這個部位，換下一個</button><button id="pvPlay">▶ 預覽／停止</button></div>
   <div class="row"><input id="pvName" placeholder="新動作名稱" style="flex:1"><button id="pvSave">💾 儲存新動作</button></div>
   <h3>已儲存</h3><div id="pvSaved"></div><div class="row"><label>匯入 <input id="pvImport" type="file" accept=".json"></label></div>
  </div>`);
  const stage = $('cv').parentElement;
  stage.insertAdjacentHTML('beforeend', '<div id="pvMark" style="display:none;position:absolute;width:18px;height:18px;margin:-9px 0 0 -9px;border:2px solid #e11;border-radius:50%;background:#fff8;pointer-events:none;z-index:5"></div>');
  $('pvOpen').onclick = () => { const s = $('pivotSec'); s.hidden = !s.hidden; $('pvOpen').setAttribute('aria-pressed', !s.hidden); st.playing = null; fillParts(); listSaved(); };
  $('pvLayer').onchange = (e) => { if (!e.target.value) return; commitEdit(); st.edit.names = [e.target.value]; st.edit.label = e.target.value; $('pvHint').textContent = `已選 ${e.target.value}，點「定位支點」再點畫面。`; };
  $('pvPlace').onclick = () => { if (!st.edit.names.length) { $('pvHint').textContent = '請先選部位。'; return; } st.placing = !st.placing; $('pvPlace').setAttribute('aria-pressed', st.placing); $('pvHint').textContent = st.placing ? '點畫面上的支點位置。' : ''; };
  // capture, so the tap does not also pan the view
  $('cv').addEventListener('pointerdown', (e) => {
    if (!st.placing) return;
    e.stopPropagation(); e.preventDefault();
    const c = $('cv'), v = window.demo.view, r = c.getBoundingClientRect(), sx = 2 * v.scale / c.width, sy = 2 * v.scale / c.height;
    st.edit.pivot = [v.cx + ((e.clientX - r.left) / r.width * 2 - 1) / sx, v.cy + ((e.clientY - r.top) / r.height * 2 - 1) / sy];
    st.placing = false; $('pvPlace').setAttribute('aria-pressed', false);
    $('pvHint').textContent = '支點已定位，可用方向鍵微調，再拉旋轉。';
  }, true);
  const step = () => 4 / Math.max(0.05, window.demo.view.scale);
  $('pvL').onclick = () => nudge(-step(), 0); $('pvR').onclick = () => nudge(step(), 0); $('pvU').onclick = () => nudge(0, -step()); $('pvD').onclick = () => nudge(0, step());
  for (const k of ['a', 'dx', 'dy', 'soft']) $('pv_' + k).oninput = (e) => { st.edit[k] = +e.target.value; $('pv_' + k + 'V').textContent = e.target.value; };
  $('pvKey').onclick = () => {
    if (!st.edit.pivot) { $('pvHint').textContent = '請先定位支點。'; return; }
    const t = +$('pvT').value;
    st.edit.keys = st.edit.keys.filter((k) => k.t !== t).concat({ t, a: st.edit.a, dx: st.edit.dx, dy: st.edit.dy }).sort((p, q) => p.t - q.t);
    $('pvT').value = +(t + 0.5).toFixed(2);
    showKeys();
  };
  $('pvUndo').onclick = () => { st.edit.keys.pop(); showKeys(); };
  $('pvNext').onclick = () => { commitEdit(); for (const x of $('pvPresets').children) x.setAttribute('aria-pressed', false); $('pvHint').textContent = '選下一個部位。'; };
  const build = (name) => {
    const tracks = st.tracks.concat(st.edit.keys.length && st.edit.pivot ? [{ label: st.edit.label, names: st.edit.names, pivot: st.edit.pivot, soft: st.edit.soft, keys: st.edit.keys }] : []);
    return { name, tracks, dur: Math.max(1, ...tracks.flatMap((t) => t.keys.map((k) => k.t))) };
  };
  $('pvPlay').onclick = () => {
    if (st.playing) { st.playing = null; return; }
    const a = build('預覽');
    if (!a.tracks.length) { $('pvHint').textContent = '請先記錄至少一格。'; return; }
    st.playing = a; st.t0 = performance.now();
  };
  $('pvSave').onclick = () => {
    const name = $('pvName').value.trim(), a = build(name);
    if (!name || !a.tracks.length) { $('pvHint').textContent = '請輸入名稱，並記錄至少一格。'; return; }
    const l = load().filter((x) => x.name !== name).concat(a);
    $('pvHint').textContent = store(l) ? `已儲存「${name}」。` : '這個瀏覽器無法儲存，請用匯出。';
    st.tracks = []; resetEdit(); st.playing = null; listSaved();
  };
  $('pvImport').onchange = async (e) => {
    try { const a = JSON.parse(await e.target.files[0].text()); store(load().filter((x) => x.name !== a.name).concat(a)); listSaved(); $('pvHint').textContent = `已匯入「${a.name}」。`; }
    catch { $('pvHint').textContent = '這個檔案無法匯入。'; }
  };
  fillParts();
  listSaved();
}
