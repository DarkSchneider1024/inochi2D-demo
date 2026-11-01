// 細節座標對位 (2026-11-01 user: 一樣要對座標，請在檢查功能新增底圖座標對位疑點；或是另一個功能 細節座標對位)
// Reads layers/<id>/align.json (psd-create/src/inochi2d/base_align_report.py): how far each GPT expression base's head is
// from the model's rest face, and what is left after the recorded fit.
//   import { showAlign } from './align-qa.js';  showAlign({ id, name });
export async function showAlign({ id, name }) {
  document.getElementById('alignBox')?.remove();
  const css = `#alignBox{position:fixed;inset:0;z-index:60;background:rgba(40,30,55,.72);overflow:auto;padding:12px;font:15px/1.6 system-ui,"Noto Sans TC",sans-serif;color:#3a3048}
#alignBox .in{max-width:900px;margin:0 auto;background:#f6efea;border-radius:18px;padding:16px}
#alignBox h2{margin:0 0 8px;font-size:20px}#alignBox .top{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
#alignBox button{border:1px solid rgba(60,40,80,.2);background:#fff;border-radius:999px;padding:6px 14px;font:inherit;color:inherit}
#alignBox button[aria-pressed=true]{background:#8a6fd1;color:#fff}
#alignBox .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
#alignBox .card{background:#fff;border-radius:12px;padding:8px;border:2px solid #e6dfe8}#alignBox .card.bad{border-color:#d9480f}
#alignBox img{width:100%;display:block;border-radius:8px}#alignBox b.bad{color:#d9480f}#alignBox b.ok{color:#2b8a3e}#alignBox small{display:block;font-size:13px}`;
  const box = document.createElement('div'); box.id = 'alignBox';
  box.innerHTML = `<style>${css}</style><div class="in"><h2>細節座標對位 · ${name}</h2><div class="top"><button id="alOnly" aria-pressed="true">只看有疑點</button><button id="alClose">× 關閉</button></div><p id="alInfo">讀取中…</p><div class="grid" id="alGrid"></div></div>`;
  document.body.append(box);
  box.querySelector('#alClose').onclick = () => box.remove();
  let d;
  try { const r = await fetch(`layers/${id}/align.json?v=${Date.now()}`); if (!r.ok) throw 0; d = await r.json(); }
  catch { box.querySelector('#alInfo').textContent = '這個模型還沒有對位資料（目前只有 Linda喵）。'; box.querySelector('#alOnly').hidden = true; return; }
  const bad = d.items.filter(i => i.status !== 'ok');
  box.querySelector('#alInfo').innerHTML = `共 ${d.items.length} 張 GPT 底圖，用眼睛、耳朵和下巴線疊到模型平常臉上比對（疊圖有雙線＝還沒對齊）。容許誤差：大小 ${d.tol.scale * 100}%、位置 ${d.tol.px} px。` +
    (bad.length ? `<b class="bad">${bad.length} 張有對位疑點。</b>` : '<b class="ok">全部對齊。</b>');
  const pct = v => `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;
  const draw = only => { box.querySelector('#alGrid').innerHTML = d.items.filter(i => !only || i.status !== 'ok').map(i =>
    `<div class="card ${i.status === 'ok' ? '' : 'bad'}"><img src="layers/${id}/${i.img}" alt="${i.name}" loading="lazy"><b class="${i.status === 'ok' ? 'ok' : 'bad'}">${i.name}：${i.status === 'ok' ? '通過' : '疑點'}</b>` +
    `<small>底圖要放大 ×${i.scale}，已補 ×${i.fit.join('／')}，剩 ${pct(i.left)}</small><small>水平差 ${i.dx} px・垂直差 ${i.dy} px・部件 ${i.parts} 層</small></div>`).join('') || '<p>沒有疑點。</p>'; };
  const only = box.querySelector('#alOnly');
  only.onclick = () => { const v = only.getAttribute('aria-pressed') !== 'true'; only.setAttribute('aria-pressed', String(v)); draw(v); };
  draw(bad.length > 0); only.setAttribute('aria-pressed', String(bad.length > 0));
}
