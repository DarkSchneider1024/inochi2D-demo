// 手機版控制面板 (2026-10-23, user: 動作效果在手機版要往下拉才看得到 -> 改成收合的，點三條線的按鈕彈出，角色始終置頂).
// Phones (<= 760 px): the stage stays fixed at the top of the screen and the page never scrolls; the controls (<aside>)
// live in a bottom sheet behind a ☰ button. Open, the stage shrinks to the top 46 % and the character is refitted
// into it, so a move or an expression can be watched while its button is tapped. Desktop is unchanged.
// The CSS is injected here so every page that calls mobilePanel() gets the same layout.
const CSS = `
.menu-btn { display: none; }
@media (max-width: 760px) {
  html, body { height: 100dvh !important; min-height: 0 !important; overflow: hidden !important; }
  .app, .wrap { display: block !important; height: 100dvh !important; }
  .stage { position: fixed !important; left: 0; right: 0; top: 0; height: 100dvh !important; min-height: 0 !important;
           transition: height .28s ease; z-index: 1; }
  body.panel-open .stage { height: 46dvh !important; }
  aside { position: fixed !important; left: 0; right: 0; bottom: 0; top: auto; height: 54dvh !important; width: auto !important;
          overflow-y: auto !important; overscroll-behavior: contain; border: 0 !important; border-top: 1px solid var(--line) !important;
          border-radius: 16px 16px 0 0; box-shadow: 0 -8px 24px rgba(0,0,0,.18); transform: translateY(100%);
          transition: transform .28s ease; z-index: 20; visibility: hidden; }
  body.panel-open aside { transform: none; visibility: visible; }
  .menu-btn { display: grid; place-items: center; position: absolute; right: 10px; top: 8px; z-index: 30; width: 42px; height: 42px;
              border-radius: 12px; border: 1px solid var(--line); background: var(--panel, var(--card)); color: var(--ink);
              backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); font: 600 20px/1 system-ui, sans-serif;
              box-shadow: 0 3px 12px rgba(0,0,0,.14); cursor: pointer; }
  .menu-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .overlay { right: 62px !important; }          /* the page tabs over the stage leave room for ☰ */
  #zoom { display: none !important; }            /* the sheet replaces 放大 on phones: closed = the full character */
  body.full .menu-btn { display: none; }
  body.panel-open .shakebar, body.panel-open .hint { display: none !important; }   /* (they covered the feet) */
  /* (2026-10-30 user: UI 有點多按鈕，有些會擋到人；手機版縮合到右邊選單才展開，沒展開的話手機滿版都是人物)
     closed: only the character and the ☰ button; the page tabs, view buttons, hint and shake bar come with the menu */
  body:not(.panel-open) .overlay, body:not(.panel-open) .viewctl, body:not(.panel-open) .hint,
  body:not(.panel-open) .shakebar { display: none !important; }
}`;

// onToggle(open): the page re-centres its character (a stray swipe on the stage pans it off to the side)
export function mobilePanel(stage, aside, onToggle) {
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  const btn = document.createElement('button');
  btn.className = 'menu-btn';
  btn.type = 'button';
  btn.textContent = '☰';
  btn.setAttribute('aria-label', '開啟控制面板');
  btn.setAttribute('aria-expanded', 'false');
  stage.appendChild(btn);
  const set = (open) => {
    document.body.classList.toggle('panel-open', open);
    btn.textContent = open ? '✕' : '☰';
    btn.setAttribute('aria-label', open ? '收起控制面板' : '開啟控制面板');
    btn.setAttribute('aria-expanded', String(open));
    if (onToggle) onToggle(open);
    // the stage height animates (.28 s): refit the character along the way
    let n = 0;
    const tick = () => { dispatchEvent(new Event('resize')); if (++n < 24) requestAnimationFrame(tick); };
    tick();
  };
  btn.addEventListener('click', () => set(!document.body.classList.contains('panel-open')));
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.body.classList.contains('panel-open')) set(false); });
  return set;
}
