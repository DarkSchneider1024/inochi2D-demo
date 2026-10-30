// lipsync.js — VTuber-style talking for our puppets: Mouth:: Open (0 closed .. 1 wide) x Mouth:: Form (0 啊, 0.5 咿,
// 1 喔). (2026-10-30, user: 說話嘴巴的啊跟喔差太多，不自然) the storytelling outro and a VTuber reel use 5-6 mouths and
// pass through the in-between sizes; the old drivers jumped Form 0 <-> 1 with the mouth wide open. Now every syllable
// (~4.6 a second, Mandarin) picks a vowel and how wide, and the mouth eases to it; the vowel changes mostly while the
// mouth is nearly shut between syllables. Deterministic: the same t always gives the same target.
const VOWELS = [[1.0, 0.0], [0.5, 0.5], [0.45, 1.0], [0.75, 0.5], [0.8, 1.0], [0.65, 0.0]];   // [open, form]: a i u e o a
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };

export function lipTarget(t, level, rate = 4.6) {
  const k = t * rate, i = Math.floor(k), u = k - i;
  const [o, f] = VOWELS[Math.floor(hash(i) * VOWELS.length)];
  const env = Math.sin(Math.PI * Math.min(1, u * 1.2));       // opens within the syllable, shuts briefly at its end
  return { open: Math.min(1, level) * o * (0.05 + 0.95 * Math.max(0, env)), form: f };
}

// a rig whose Mouth:: Form has the 啊 / 咿 / 喔 families (make_carol3_puppet.py: six axis points); older rigs keep their
// own drivers (Form 0 / 1 only)
export const isMidMouth = (p) => !!p && (p.axis_points?.[0]?.length ?? 0) >= 6;

// m = { open, form } carried from frame to frame
export function lipStep(m, tgt, dt) {
  m.open += (tgt.open - m.open) * (1 - Math.exp(-dt * 22));
  // (a vowel change with the mouth still open eases fast, so 咿 does not flash between 啊 and 喔 for frames)
  m.form += (tgt.form - m.form) * (m.open < 0.25 ? 1 : 1 - Math.exp(-dt * 30));
  return m;
}
