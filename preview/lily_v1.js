const BASE = "../assets/lily_v1/layers/";
const V = "20260716-masterbase";

// back -> front, d = parallax depth, g = motion group
const LAYERS = [
  { n: "master_base", d: 0.65, g: "body" },
];

const rig = document.getElementById("rig");
const state = document.getElementById("state");
const hint = document.getElementById("hint");
const pOut = document.getElementById("p-out");
const parallax = document.getElementById("parallax");
const tracking = document.getElementById("tracking");
const breathBox = document.getElementById("breath");

let loaded = 0;
const imgs = LAYERS.map((spec) => {
  const img = document.createElement("img");
  img.className = "layer";
  img.src = BASE + spec.n + ".png?v=" + V;
  img.alt = spec.n;
  img.onload = () => { hint.textContent = `已載入 ${++loaded}/${LAYERS.length} 圖層`; };
  rig.appendChild(img);
  return img;
});

let tx = 0, ty = 0, cx = 0, cy = 0;
const stage = document.getElementById("stage");
stage.addEventListener("pointermove", (e) => {
  if (!tracking.checked) return;
  const r = stage.getBoundingClientRect();
  tx = ((e.clientX - r.left) / r.width) * 2 - 1;
  ty = ((e.clientY - r.top) / r.height) * 2 - 1;
});
stage.addEventListener("pointerleave", () => { tx = ty = 0; });
parallax.addEventListener("input", () => { pOut.value = parallax.value; });

function frame(t) {
  cx += (tx - cx) * 0.08;
  cy += (ty - cy) * 0.08;
  const s = +parallax.value;
  const breath = breathBox.checked ? Math.sin(t / 1600) * 5 : 0;
  LAYERS.forEach((spec, i) => {
    imgs[i].style.transform = `translate(${cx * s * spec.d}px, ${cy * s * spec.d * 0.6 + breath}px)`;
  });
  state.textContent = tracking.checked ? "TRACKING" : "IDLE";
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
