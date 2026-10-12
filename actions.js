// 動作 (2026-10-13): the desk / storytelling actions of the Spine models, for the Inochi2D puppets.
// Each action is a function of time u (s) -> { param: value | [x, y] }; the demo applies it on top of everything
// else while it plays (gaze, blink, idle arms, walk), then hands back. Head:: Yaw-Pitch y + = looking up.
// Parameters come from the rigs: carol_v2 Arm:: Left:: Raise (0 hanging .. 1 the wave drawing, five key drawings,
// 0.5 = forearm level), mr_carrot_v2 Arm:: Right:: Raise (0 hanging, 0.5 palm-up present, 1 wave) + Point (present ->
// index finger), bobo Carrot:: Hold (1 hugging, 0 empty paws), Arm:: Right / Left:: Raise (paw up, 1 = 183 deg),
// Ears:: Droop, Body:: Hop (- = up).

const sm = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
// keyframes [[t, v], ...], eased between keys
export function K(keys) {
  return (u) => {
    if (u <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t0, v0] = keys[i - 1], [t1, v1] = keys[i];
      if (u <= t1) return v0 + (v1 - v0) * sm((u - t0) / Math.max(1e-6, t1 - t0));
    }
    return keys[keys.length - 1][1];
  };
}
const win = (u, a, b) => (u > a && u < b ? 1 : 0);
const env = (a, b, fade = 0.2) => K([[a, 0], [a + fade, 1], [b - fade, 1], [b, 0]]);
// ^ ^ smile = both blinks closed (the rigs cross-fade into the smiling arc); mouth held open
const smile = (u, a, b) => K([[a - 0.06, 0], [a, 1], [b, 1], [b + 0.08, 0]])(u);
const face = (o, u, s) => {
  if (s) { const v = smile(u, s[0], s[1]); o['Eye:: Left:: Blink'] = v; o['Eye:: Right:: Blink'] = v; }
  return o;
};

const CAROL = [
  { id: 'cheer', label: '好耶！', hint: '舉手歡呼', dur: 1.9, f: (u) => face({
      'Arm:: Left:: Raise': K([[0.05, 0], [0.45, 1], [1.3, 1], [1.8, 0]])(u),
      'Hand:: Left:: Wave': -0.9 * Math.sin(2 * Math.PI * (u - 0.45) / 0.42) * win(u, 0.45, 1.3),
      'Head:: Roll': K([[0, 0], [0.4, -0.35], [1.3, -0.35], [1.8, 0]])(u),
      'Mouth:: Open': K([[0, 0], [0.35, 0.8], [1.3, 0.8], [1.6, 0]])(u)}, u, [0.35, 1.45]) },
  { id: 'think', label: '思考', hint: '倒數時想答案', dur: 4.0, f: (u) => {
      const e = env(0, 4, 0.5)(u);
      return { 'Head:: Yaw-Pitch': [0.3 * e, 0.45 * e], 'Head:: Roll': e * (0.5 + 0.12 * Math.sin(2 * Math.PI * u / 1.5)),
               'Mouth:: Open': 0 }; } },
  { id: 'confident', label: '自信回答', hint: '挺胸點頭', dur: 2.0, f: (u) => face({
      'Head:: Yaw-Pitch': [0.1, K([[0, 0], [0.25, 0.25], [0.5, -0.5], [0.75, 0.15], [1.6, 0.1], [2, 0]])(u)],
      'Head:: Roll': K([[0, 0], [0.3, 0.25], [1.6, 0.25], [2, 0]])(u)}, u, [1.15, 1.85]) },
  { id: 'tsukkomi', label: '吐槽', hint: '不對不對', dur: 1.6, f: (u) => ({
      'Arm:: Left:: Raise': K([[0.04, 0], [0.3, 1], [1.0, 1], [1.5, 0]])(u),
      'Hand:: Left:: Wave': Math.sin(2 * Math.PI * (u - 0.3) / 0.22) * win(u, 0.3, 0.96),
      'Hand:: Left:: Wave Wrist': 0.8 * Math.sin(2 * Math.PI * (u - 0.34) / 0.22) * win(u, 0.3, 0.96),
      'Head:: Yaw-Pitch': [K([[0, 0], [0.2, 0.5], [0.95, 0.45], [1.5, 0]])(u), 0],
      'Head:: Roll': K([[0, 0], [0.25, -0.35], [0.95, -0.3], [1.4, 0]])(u)}) },
  { id: 'point', label: '指向', hint: '手往外打開', dur: 2.8, f: (u) => ({
      'Arm:: Left:: Raise': K([[0, 0], [0.4, 0.5], [2.4, 0.5], [2.8, 0]])(u),
      'Head:: Yaw-Pitch': [K([[0, 0], [0.4, 0.35], [2.4, 0.35], [2.8, 0]])(u), 0]}) },
  { id: 'wave_bye', label: '掰掰', hint: '舉手揮個不停', dur: 2.6, f: (u) => face({
      'Arm:: Left:: Raise': K([[0.03, 0], [0.6, 1], [1.95, 1], [2.55, 0]])(u),
      'Hand:: Left:: Wave': -Math.sin(2 * Math.PI * (u - 0.65) / 0.56) * env(0.55, 2.0, 0.15)(u),
      'Hand:: Left:: Wave Wrist': -Math.sin(2 * Math.PI * (u - 0.73) / 0.56) * env(0.55, 2.0, 0.15)(u),
      'Head:: Roll': K([[0, 0], [0.65, -0.35], [1.95, -0.35], [2.6, 0]])(u)}, u, [0.5, 2.05]) },
];

// his rule: the shoulder never moves; the right forearm comes up through the key drawings
const restArmR = { 'Arm:: Right:: Swing': 0, 'Arm:: Right:: Bend': 0, 'Hand:: Right:: Wrist': 0 };
const MRCARROT = [
  { id: 'greet', label: '打招呼', hint: '手肘在身側、張開手掌揮', dur: 3.2, f: (u) => face({ ...restArmR,
      'Arm:: Right:: Raise': K([[0.05, 0], [0.55, 1], [2.45, 1], [3.05, 0]])(u),
      'Hand:: Right:: Wave': Math.sin(2 * Math.PI * (u - 0.6) / 0.5) * env(0.55, 2.45, 0.15)(u),
      'Head:: Roll': K([[0, 0], [0.6, 0.3], [2.4, 0.3], [3.1, 0]])(u),
      'Mouth:: Open': K([[0.6, 0], [0.8, 0.6], [2.3, 0.6], [2.5, 0]])(u)}, u, [0.6, 2.5]) },
  { id: 'present', label: '請看', hint: '手掌朝上往外', dur: 3.3, f: (u) => ({ ...restArmR,
      'Arm:: Right:: Raise': K([[0, 0], [0.45, 0.5], [2.85, 0.5], [3.3, 0]])(u)}) },
  { id: 'ask', label: '出題', hint: '舉食指「第一題！」', dur: 3.0, f: (u) => ({ ...restArmR,
      'Arm:: Right:: Raise': K([[0, 0], [0.25, 0.5], [2.75, 0.5], [3.0, 0]])(u),
      'Arm:: Right:: Point': K([[0.25, 0], [0.5, 1], [2.5, 1], [2.75, 0]])(u),
      'Head:: Yaw-Pitch': [-0.08 * env(0, 3, 0.4)(u), K([[0.5, 0], [0.75, -0.35], [1.0, 0.08], [1.5, 0], [1.75, -0.35], [2.0, 0.08], [2.5, 0]])(u)]}) },
  { id: 'recap', label: '回顧', hint: '舉食指看大螢幕', dur: 3.4, f: (u) => ({ ...restArmR,
      'Arm:: Right:: Raise': K([[0, 0], [0.25, 0.5], [3.15, 0.5], [3.4, 0]])(u),
      'Arm:: Right:: Point': K([[0.25, 0], [0.5, 1], [2.9, 1], [3.15, 0]])(u),
      'Head:: Yaw-Pitch': [K([[0, 0], [0.5, -0.3], [1.7, -0.05], [2.9, -0.3], [3.4, 0]])(u),
                            K([[0, 0], [0.5, 0.35], [1.7, 0.05], [2.9, 0.35], [3.4, 0]])(u)]}) },
  { id: 'correct', label: '答對了', hint: '手掌＋笑眼點頭', dur: 1.9, f: (u) => face({ ...restArmR,
      'Arm:: Right:: Raise': K([[0.05, 0], [0.38, 0.5], [1.3, 0.5], [1.8, 0]])(u),
      'Head:: Yaw-Pitch': [0, K([[0, 0], [0.25, -0.4], [0.45, 0.1], [0.7, -0.3], [0.9, 0], [1.9, 0]])(u)],
      'Head:: Roll': K([[0, 0], [0.3, 0.25], [1.4, 0.25], [1.9, 0]])(u)}, u, [0.3, 1.45]) },
  { id: 'gentle', label: '溫柔對鏡頭', hint: '慢慢點頭', dur: 3.8, f: (u) => {
      const e = env(0, 3.8, 0.4)(u);
      return { 'Head:: Yaw-Pitch': [0, e * (-0.2 + 0.15 * Math.cos(2 * Math.PI * (u - 0.4) / 1.5))],
               'Head:: Roll': e * (0.25 + 0.08 * Math.sin(2 * Math.PI * u / 1.5)) }; } },
  { id: 'wave_bye', label: '掰掰', hint: '舉手揮個不停', dur: 2.1, f: (u) => face({ ...restArmR,
      'Arm:: Right:: Raise': K([[0.02, 0], [0.55, 1], [1.55, 1], [2.08, 0]])(u),
      'Hand:: Right:: Wave': Math.sin(2 * Math.PI * (u - 0.55) / 0.5) * env(0.5, 1.6, 0.1)(u),
      'Head:: Roll': K([[0, 0], [0.55, 0.3], [1.55, 0.3], [2.1, 0]])(u)}, u, [0.45, 1.65]) },
];

const BOBO = [
  { id: 'slam', label: '拍桌搶答', hint: '放下胡蘿蔔、拍兩下', dur: 2.2, f: (u) => ({
      'Carrot:: Hold': u < 2.15 ? 0 : 1,
      'Arm:: Right:: Raise': K([[0, 0], [0.18, 0.5], [0.3, -0.05], [0.5, 0.42], [0.62, -0.05], [0.9, 0]])(u),
      'Arm:: Left:: Raise': K([[0, 0], [0.18, 0.5], [0.3, -0.05], [0.5, 0.42], [0.62, -0.05], [0.9, 0]])(u),
      'Body:: Hop': K([[0, 0], [0.18, -0.2], [0.3, 0.14], [0.5, -0.14], [0.62, 0.11], [0.9, 0]])(u),
      'Head:: Yaw-Pitch': [0, K([[0, 0], [0.2, 0.4], [0.32, -0.3], [0.52, 0.3], [0.64, -0.3], [1.0, 0]])(u)],
      'Mouth:: Open': K([[0.15, 0], [0.3, 1], [1.6, 1], [1.75, 0]])(u)}) },
  { id: 'raise_paw', label: '舉手搶答', hint: '舉手跳跳', dur: 2.4, f: (u) => ({
      'Carrot:: Hold': u < 2.35 ? 0 : 1,
      'Arm:: Right:: Raise': K([[0, 0], [0.18, 1], [2.0, 1], [2.4, 0]])(u) + 0.04 * Math.sin(2 * Math.PI * u / 0.4) * win(u, 0.18, 2.0),
      'Arm:: Left:: Raise': K([[0, 0], [0.25, 0.11], [2.0, 0.11], [2.4, 0]])(u),
      'Body:: Hop': -0.14 * Math.abs(Math.sin(Math.PI * u / 0.45)) * win(u, 0.1, 1.9),
      'Head:: Yaw-Pitch': [-0.1 * env(0, 2.4, 0.3)(u), 0.3 * env(0, 2.4, 0.3)(u)],
      'Mouth:: Open': K([[0.2, 0], [0.35, 0.9], [1.45, 0.9], [1.6, 0]])(u)}) },
  { id: 'shy', label: '心虛', hint: '耳朵垂、眼神飄', dur: 3.0, f: (u) => {
      const e = K([[0, 0], [0.4, 1], [2.5, 1], [3.0, 0]])(u);
      return { 'Ears:: Droop': e, 'Head:: Yaw-Pitch': [-0.35 * e, -0.4 * e], 'Body:: Hop': 0.06 * e,
               'Mouth:: Open': K([[0.5, 0], [0.65, 0.35], [1.5, 0.35], [1.65, 0]])(u), 'Mouth:: Form': 1 }; } },
  { id: 'happy', label: '開心跳跳', hint: '笑眼、耳朵甩', dur: 2.0, f: (u) => face({
      'Body:: Hop': K([[0, 0], [0.14, 0.2], [0.3, -0.1], [0.45, -0.5], [0.62, 0], [0.7, 0.17], [0.88, 0], [1, 0],
                       [1.14, 0.2], [1.3, -0.1], [1.45, -0.5], [1.62, 0], [1.7, 0.17], [1.88, 0], [2, 0]])(u),
      'Head:: Roll': 0.4 * Math.sin(2 * Math.PI * u / 2.0),
      'Mouth:: Open': K([[0.12, 0], [0.25, 0.9], [1.8, 0.9], [1.9, 0]])(u)}, u, [0.08, 1.92]) },
  { id: 'wave', label: '揮手', hint: '空手揮', dur: 3.0, f: (u) => face({
      'Carrot:: Hold': u < 2.95 ? 0 : 1,
      'Arm:: Right:: Raise': K([[0, 0], [0.3, 0.95], [2.5, 0.95], [3.0, 0]])(u) + 0.1 * Math.sin(2 * Math.PI * (u - 0.3) / 0.45) * env(0.3, 2.5, 0.2)(u),
      'Head:: Roll': K([[0, 0], [0.5, -0.4], [2.5, -0.4], [3.0, 0]])(u),
      'Mouth:: Open': K([[0.45, 0], [0.6, 0.8], [2.4, 0.8], [2.5, 0]])(u)}, u, [0.4, 2.6]) },
];

export const ACTIONS = { carol_v2: CAROL, mr_carrot_v2: MRCARROT, bobo: BOBO };
