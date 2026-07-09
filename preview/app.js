const stage = document.querySelector("#stage");
const rig = document.querySelector("#rig");
const xInput = document.querySelector("#angle-x");
const yInput = document.querySelector("#angle-y");
const xOut = document.querySelector("#x-out");
const yOut = document.querySelector("#y-out");
const tracking = document.querySelector("#tracking");
const state = document.querySelector("#state");

const layers = {
  face: document.querySelector(".face"),
  hairBack: document.querySelector(".hair-back"),
  hairFront: document.querySelector(".hair-front"),
  eyeL: document.querySelector(".eye-l"),
  eyeR: document.querySelector(".eye-r"),
  browL: document.querySelector(".brow-l"),
  browR: document.querySelector(".brow-r"),
  nose: document.querySelector(".nose"),
  mouth: document.querySelector(".mouth"),
};

function setLayer(el, tx, ty, sx = 1, sy = 1, rot = 0, skew = 0) {
  el.style.transform = [
    `translate3d(${tx}px, ${ty}px, 0)`,
    `rotate(${rot}deg)`,
    `skewX(${skew}deg)`,
    `scale(${sx}, ${sy})`,
  ].join(" ");
}

function labelFor(x, y) {
  const h = x < -0.2 ? "LEFT" : x > 0.2 ? "RIGHT" : "CENTER";
  const v = y < -0.2 ? "UP" : y > 0.2 ? "DOWN" : "CENTER";
  return h === "CENTER" && v === "CENTER" ? "CENTER" : `${v} ${h}`.trim();
}

function applyRig() {
  const x = Number(xInput.value);
  const y = Number(yInput.value);

  xOut.value = x.toFixed(2);
  yOut.value = y.toFixed(2);
  state.textContent = labelFor(x, y);

  rig.style.transform = `translate(-50%, -52%) rotateY(${x * -9}deg) rotateX(${y * 5}deg)`;

  setLayer(layers.hairBack, x * -22, y * 8, 1 + Math.abs(x) * .015, 1 + y * .015, x * -2.2, x * 1.2);
  setLayer(layers.face, x * -10, y * 7, 1 - Math.abs(x) * .018, 1 + y * .012, x * -1.0, x * .8);
  setLayer(layers.hairFront, x * -17, y * 12, 1 + Math.abs(x) * .01, 1 + y * .018, x * -2.8, x * 1.5);

  setLayer(layers.eyeL, x * -18 + Math.max(x, 0) * -7, y * 10, 1 - x * .05, 1 - Math.abs(x) * .04, x * -1.8, x * 1.6);
  setLayer(layers.eyeR, x * -18 + Math.min(x, 0) * -7, y * 10, 1 + x * .05, 1 - Math.abs(x) * .04, x * -1.8, x * 1.6);
  setLayer(layers.browL, x * -17 + Math.max(x, 0) * -6, y * 9 - 2, 1 - x * .04, 1, x * -2, x * 1.5);
  setLayer(layers.browR, x * -17 + Math.min(x, 0) * -6, y * 9 - 2, 1 + x * .04, 1, x * -2, x * 1.5);

  setLayer(layers.nose, x * -28, y * 12, 1 - Math.abs(x) * .06, 1 + y * .03, x * -2.5, x * 2.8);
  setLayer(layers.mouth, x * -20, y * 16, 1 - Math.abs(x) * .045, 1 + y * .025, x * -1.6, x * 1.5);

  const shade = Math.abs(x) * 0.12 + Math.max(y, 0) * 0.06;
  const shadowFilter = `drop-shadow(${x * -4}px ${4 + y * 2}px ${10 + Math.abs(x) * 6}px rgba(84,38,12,${0.12 + shade}))`;
  
  // Apply drop-shadow only to the main head and hair parts
  [layers.face, layers.hairBack, layers.hairFront].forEach((el) => {
    el.style.filter = shadowFilter;
  });
  
  // Clear filter for facial features to prevent ugly seams
  [layers.eyeL, layers.eyeR, layers.browL, layers.browR, layers.nose, layers.mouth].forEach((el) => {
    el.style.filter = "none";
  });
}

stage.addEventListener("pointermove", (event) => {
  if (!tracking.checked) return;
  const rect = stage.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
  xInput.value = Math.max(-1, Math.min(1, x)).toFixed(2);
  yInput.value = Math.max(-1, Math.min(1, y)).toFixed(2);
  applyRig();
});

[xInput, yInput].forEach((input) => input.addEventListener("input", applyRig));
applyRig();
