const BASE = "../assets/lily_v1/layers/";
const EXTRA = "../assets/lily_v1/extras/";
const V = "20260716-armfix";

// back -> front, d = parallax depth, g = motion group
const LAYERS = [
  { n: "hair_back_main", d: 0.4, g: "hairB" },
  { n: "body_underfill", d: 0.62, g: "body" },
  { n: "leg_L", d: 0.6, g: "body" },
  { n: "leg_R", d: 0.6, g: "body" },
  { n: "forearm_L", d: 0.68, g: "body" },
  { n: "forearm_R", d: 0.68, g: "body" },
  { n: "hand_L", d: 0.68, g: "body" },
  { n: "hand_R", d: 0.68, g: "body" },
  { n: "sleeve_L", d: 0.7, g: "body" },
  { n: "sleeve_R", d: 0.7, g: "body" },
  { n: "bodice", d: 0.7, g: "body" },
  { n: "skirt", d: 0.66, g: "body" },
  { n: "bald_head", d: 0.95, g: "head" },
  { n: "brow_L", d: 1.0, g: "head" },
  { n: "brow_R", d: 1.0, g: "head" },
  { n: "blush_L", d: 1.0, g: "head" },
  { n: "blush_R", d: 1.0, g: "head" },
  { n: "mouth", d: 1.0, g: "head" },
  { n: "eye_L", d: 1.12, g: "eyesOpen" },
  { n: "eye_R", d: 1.12, g: "eyesOpen" },
  { n: "eye_closed_L", d: 1.0, g: "eyesClosed", extra: true },
  { n: "eye_closed_R", d: 1.0, g: "eyesClosed", extra: true },
  { n: "bangs", d: 1.08, g: "hairF" },
  { n: "side_lock_L", d: 1.08, g: "hairF" },
  { n: "side_lock_R", d: 1.08, g: "hairF" },
  { n: "earring_L", d: 1.1, g: "hairF" },
  { n: "earring_R", d: 1.1, g: "hairF" },
  { n: "necklace", d: 1.1, g: "hairF" },
];

const rig = document.getElementById("rig");
const state = document.getElementById("state");
const hint = document.getElementById("hint");
const pOut = document.getElementById("p-out");
const parallax = document.getElementById("parallax");
const tracking = document.getElementById("tracking");
const breathBox = document.getElementById("breath");
const blinkBox = document.getElementById("blink");

let loaded = 0;
const imgs = LAYERS.map((spec) => {
  const img = document.createElement("img");
  img.className = "layer";
  img.src = (spec.extra ? EXTRA : BASE) + spec.n + ".png?v=" + V;
  img.alt = spec.n;
  if (spec.g === "eyesClosed") img.style.opacity = 0;
  img.onload = () => { hint.textContent = `已載入 ${++loaded}/${LAYERS.length} 圖層`; };
  rig.appendChild(img);
  return img;
});

let tx = 0, ty = 0, cx = 0, cy = 0, closed = false;
const stage = document.getElementById("stage");
stage.addEventListener("pointermove", (e) => {
  if (!tracking.checked) return;
  const r = stage.getBoundingClientRect();
  tx = ((e.clientX - r.left) / r.width) * 2 - 1;
  ty = ((e.clientY - r.top) / r.height) * 2 - 1;
});
stage.addEventListener("pointerleave", () => { tx = ty = 0; });
parallax.addEventListener("input", () => { pOut.value = parallax.value; });

function scheduleBlink() {
  setTimeout(() => {
    if (blinkBox.checked) {
      closed = true;
      state.textContent = "BLINK";
      setTimeout(() => { closed = false; state.textContent = tracking.checked ? "TRACKING" : "IDLE"; }, 130);
    }
    scheduleBlink();
  }, 2600 + Math.random() * 2800);
}
scheduleBlink();

function frame(t) {
  cx += (tx - cx) * 0.08;
  cy += (ty - cy) * 0.08;
  const s = +parallax.value;
  const breath = breathBox.checked ? Math.sin(t / 1600) * 5 : 0;
  const sway = breathBox.checked ? Math.sin(t / 2300) * 3 : 0;
  LAYERS.forEach((spec, i) => {
    let dy = 0, dx = 0;
    if (spec.g === "body") dy = breath;
    else if (spec.g === "head" || spec.g.startsWith("eyes")) dy = breath * 0.6;
    else if (spec.g === "hairF") { dy = breath * 0.6; dx = sway * 0.4; }
    else if (spec.g === "hairB") { dy = breath * 0.35; dx = sway; }
    const open = spec.g === "eyesOpen" ? (closed ? 0 : 1) : spec.g === "eyesClosed" ? (closed ? 1 : 0) : null;
    if (open !== null) imgs[i].style.opacity = open;
    imgs[i].style.transform = `translate(${cx * s * spec.d + dx}px, ${cy * s * spec.d * 0.6 + dy}px)`;
  });
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
