// 喜怒哀樂 (2026-10-23): the feelings table and the 漫符 drawing, shared by index.html and official.html.
// Moved out of index.html unchanged.

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export const FEEL = {
  neutral: { label: '😐 平常' },
  happy: { label: '😊 微笑', brow: -0.15, raise: 0.3, mouth: 1.0, blush: 0.45, emote: 'sparkle' },
  laugh: { label: '😆 大笑', raise: 0.5, mouth: 1.0, blush: 0.6, smile: 1, open: 0.85, laugh: 1, roll: 0.12, emote: 'notes' },
  angry: { label: '😠 生氣', brow: 1.0, mouth: -0.8, lid: 0.3, pitch: 0.12, shake: 0.35, emote: 'vein' },
  sad: { label: '😢 難過', brow: -1.0, mouth: -1.0, lid: 0.35, pitch: 0.45, emote: 'tears' },
  surprise: { label: '😲 驚訝', raise: 1.0, shock: 0.6, open: 0.6, form: 1, pitch: -0.2, emote: 'bang' },
  scared: { label: '😨 害怕', brow: -0.7, raise: 0.6, shock: 0.8, mouth: -0.6, open: 0.3, form: 1, tremble: 1, emote: 'sweat' },
  smug: { label: '😏 得意', brow: 0.45, mouth: 0.9, lid: 0.38, roll: -0.12, emote: 'glint' },
  shy: { label: '😳 害羞', brow: -0.4, mouth: 0.5, blush: 1.0, lid: 0.2, pitch: 0.3, emote: 'blush' },
};

// the video stage's drawing code (carrot-video/live2d/player/stage.js Stage.uiEmote), shared verbatim
export const stageEmote = {
  // 漫符 (2026-10-19): the manga symbol of the actor's feeling, on its face box (fallback: the top of the figure)
  uiEmote(c, a, S, z) {
    const kind = (FEEL[a.emo.v] || {}).emote;
    if (!kind) return;
    const F = S.face || { x0: S.sx - 0.09 * S.h, x1: S.sx + 0.09 * S.h, y0: S.top, y1: S.top + 0.2 * S.h };
    const r = Math.max(14 * z, (F.x1 - F.x0) / 2), cx = (F.x0 + F.x1) / 2, eyeY = F.y0 + 0.45 * (F.y1 - F.y0);
    const w = a.emo.w, u = a.emo.u, d = S.dir || 1, front = d > 0 ? F.x1 : F.x0;   // the side the actor faces
    const pop = (q) => { q = clamp(q, 0, 1); return 1 + 0.35 * Math.sin(q * Math.PI) * (1 - q); };
    const A = clamp(w * 1.4, 0, 1);
    c.save();
    c.globalAlpha = A;
    c.lineCap = 'round'; c.lineJoin = 'round';
    const drop = (x, y, s, fill, ink) => {       // teardrop, point up
      c.beginPath(); c.moveTo(x, y - s * 1.5);
      c.bezierCurveTo(x + s * 0.2, y - s * 0.9, x + s, y - s * 0.3, x + s, y + s * 0.15);
      c.arc(x, y + s * 0.15, s, 0, Math.PI);
      c.bezierCurveTo(x - s, y - s * 0.3, x - s * 0.2, y - s * 0.9, x, y - s * 1.5);
      c.fillStyle = fill; c.fill(); c.lineWidth = Math.max(1.5, s * 0.22); c.strokeStyle = ink; c.stroke();
      c.beginPath(); c.ellipse(x - s * 0.35, y, s * 0.2, s * 0.32, -0.3, 0, Math.PI * 2); c.fillStyle = 'rgba(255,255,255,0.85)'; c.fill();
    };
    const star = (x, y, s, col) => {
      c.beginPath();
      for (let i = 0; i < 8; i++) { const ang = (i / 8) * Math.PI * 2, rr = i % 2 ? s * 0.28 : s; c.lineTo(x + rr * Math.cos(ang), y + rr * Math.sin(ang)); }
      c.closePath(); c.fillStyle = col; c.fill(); c.lineWidth = Math.max(1.2, s * 0.12); c.strokeStyle = '#ffffff'; c.stroke();
    };
    if (kind === 'vein') {                         // 💢 four bulging arcs, pulsing
      const s = 0.42 * r * pop(u / 0.3) * (1 + 0.1 * Math.sin(u * 11)), x = F.x1 - 0.05 * r, y = F.y0 + 0.12 * r;
      c.translate(x, y); c.rotate(0.2);
      for (const white of [true, false]) {
        for (let k = 0; k < 4; k++) {
          c.save(); c.rotate((k * Math.PI) / 2);
          c.beginPath(); c.arc(s * 0.62, s * 0.62, s * 0.48, Math.PI * 1.02, Math.PI * 1.48);
          c.lineWidth = white ? 0.34 * s : 0.17 * s; c.strokeStyle = white ? '#ffffff' : '#e3263a'; c.stroke();
          c.restore();
        }
      }
    } else if (kind === 'tears') {                 // falling tears + gloom lines on the forehead
      const E = S.eyes && S.eyes.length ? S.eyes
        : [-1, 1].map((sx) => ({ cx: cx + sx * 0.36 * r, x0: cx + sx * 0.36 * r, x1: cx + sx * 0.36 * r, y1: eyeY + 0.1 * r }));
      const ts = 0.15 * r;
      for (const e of E) if (e.x1 > e.x0) {             // wet shine along the lower lid: where the tears come from
        c.globalAlpha = 0.8 * A;
        c.beginPath(); c.ellipse(e.cx, e.y1 - 0.02 * r, 0.5 * (e.x1 - e.x0), 0.06 * r, 0, 0.1 * Math.PI, 0.9 * Math.PI);
        c.lineWidth = Math.max(2, 0.05 * r); c.strokeStyle = '#8fd6ff'; c.stroke();
      }
      for (const e of E) for (let i = 0; i < 2; i++) {
        const q = (u * 1.1 + i * 0.5) % 1;
        // welling at the lower lid (outer half of the eye), then running down the cheek; the tip starts on the lid
        const x = e.cx + (e.cx < cx ? -1 : 1) * 0.15 * (e.x1 - e.x0);
        c.globalAlpha = A * (1 - q * q);
        drop(x, e.y1 + ts * 1.5 + q * 0.85 * r, ts * (0.75 + 0.25 * Math.min(1, q * 4)), '#8fd6ff', '#2f86c8');
      }
      c.globalAlpha = 0.55 * A;
      c.strokeStyle = '#5a5fa8'; c.lineWidth = Math.max(1.5, 0.05 * r);
      for (let i = 0; i < 5; i++) {
        const x = F.x0 + (0.25 + 0.125 * i) * (F.x1 - F.x0);
        c.beginPath(); c.moveTo(x, F.y0 + 0.08 * r); c.lineTo(x, F.y0 + (0.42 + 0.08 * (i % 2)) * r); c.stroke();
      }
    } else if (kind === 'bang') {                  // ! with burst lines, popping in
      const s = r * pop(u / 0.25), x = front + d * 0.35 * r, y = F.y0 - 0.25 * r;
      c.font = `900 ${Math.round(0.95 * s)}px "Microsoft JhengHei", "Noto Sans TC", sans-serif`;
      c.textAlign = 'center'; c.textBaseline = 'middle';
      c.lineWidth = 0.14 * s; c.strokeStyle = '#3a2410'; c.strokeText('!', x, y);
      c.fillStyle = '#ffd23a'; c.fillText('!', x, y);
      c.lineWidth = Math.max(2, 0.06 * s);
      for (const q of [-2.3, -1.6, -0.9]) {
        const ang = d > 0 ? q : -Math.PI - q;
        c.beginPath(); c.moveTo(x + Math.cos(ang) * 0.55 * s, y + Math.sin(ang) * 0.55 * s);
        c.lineTo(x + Math.cos(ang) * 0.8 * s, y + Math.sin(ang) * 0.8 * s); c.stroke();
      }
    } else if (kind === 'sweat') {                 // one big sweat drop sliding down the temple
      const q = (u * 0.5) % 1;
      drop((d > 0 ? F.x0 : F.x1) - d * 0.02 * r, F.y0 + (0.25 + 0.25 * q) * r, 0.17 * r, '#c7ecff', '#3b8fd0');
    } else if (kind === 'sparkle' || kind === 'glint') {
      const pts = kind === 'glint' ? [[front + d * 0.15 * r, eyeY - 0.25 * r, 0.22, 0]]
        : [[F.x0 - 0.25 * r, F.y0 + 0.3 * r, 0.2, 0], [F.x1 + 0.3 * r, F.y0 + 0.05 * r, 0.26, 1.3], [F.x1 + 0.15 * r, F.y1 - 0.05 * r, 0.16, 2.4]];
      for (const [x, y, s, ph] of pts) {
        const tw = Math.max(0, Math.sin(u * (kind === 'glint' ? 5 : 4) + ph));
        if (tw > 0.05) star(x, y, s * r * (0.4 + 0.6 * tw), '#ffe46b');
      }
    } else if (kind === 'notes') {                 // ♪ ♫ floating up
      c.textAlign = 'center'; c.textBaseline = 'middle';
      for (let i = 0; i < 2; i++) {
        const q = (u * 0.7 + i * 0.5) % 1, x = front + d * (0.3 + 0.25 * q) * r + Math.sin(q * 6) * 0.08 * r, y = F.y0 + 0.2 * r - q * 0.9 * r;
        c.globalAlpha = A * Math.sin(q * Math.PI);
        c.font = `700 ${Math.round(0.55 * r)}px "Segoe UI Symbol", sans-serif`;
        c.lineWidth = 0.08 * r; c.strokeStyle = '#ffffff'; c.strokeText(i ? '♫' : '♪', x, y);
        c.fillStyle = '#ff6f91'; c.fillText(i ? '♫' : '♪', x, y);
      }
    } else if (kind === 'blush') {                 // /// hatching on both cheeks
      c.strokeStyle = '#ff5f86'; c.lineWidth = Math.max(1.5, 0.045 * r);
      const E = S.eyes && S.eyes.length ? S.eyes
        : [-1, 1].map((sx) => ({ cx: cx + sx * 0.45 * r, y0: eyeY, y1: eyeY + 0.1 * r }));
      for (const e of E) for (let i = 0; i < 3; i++) {
        // on the cheek: just under the eye, a touch to its outer side
        const out = e.cx < cx ? -1 : 1, x = e.cx + out * 0.06 * r + (i - 1) * 0.11 * r, y = e.y1 + 0.2 * r;
        c.beginPath(); c.moveTo(x + 0.05 * r, y - 0.09 * r); c.lineTo(x - 0.05 * r, y + 0.09 * r); c.stroke();
      }
    }
    c.restore();
  },
};
