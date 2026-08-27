const stage = document.querySelector("#stage");
const rig = document.querySelector("#rig");
const xInput = document.querySelector("#angle-x");
const yInput = document.querySelector("#angle-y");
const xOut = document.querySelector("#x-out");
const yOut = document.querySelector("#y-out");
const tracking = document.querySelector("#tracking");
const state = document.querySelector("#state");

// Expression controls
const eyeOpenLInput = document.querySelector("#eye-open-l");
const eyeOpenRInput = document.querySelector("#eye-open-r");
const mouthOpenInput = document.querySelector("#mouth-open");
const mouthFormInput = document.querySelector("#mouth-form");

const eyeLOut = document.querySelector("#eye-l-out");
const eyeROut = document.querySelector("#eye-r-out");
const mouthOpenOut = document.querySelector("#mouth-open-out");
const mouthFormOut = document.querySelector("#mouth-form-out");

let activeLayers = {};

// Full-body 15 layers configuration (with cache buster ?v=5)
const layersConfig = [
  { key: 'ribbonsBack', name: 'ribbons-back', src: '../assets/full_body_layers/ribbons_back.png?v=5' },
  { key: 'legLeft', name: 'leg-left', src: '../assets/full_body_layers/leg_left.png?v=5' },
  { key: 'legRight', name: 'leg-right', src: '../assets/full_body_layers/leg_right.png?v=5' },
  { key: 'torso', name: 'torso', src: '../assets/full_body_layers/torso.png?v=5' },
  { key: 'armLeft', name: 'arm-left', src: '../assets/full_body_layers/arm_left.png?v=5' },
  { key: 'armRight', name: 'arm-right', src: '../assets/full_body_layers/arm_right.png?v=5' },
  { key: 'hairBack', name: 'hair-back', src: '../assets/full_body_layers/hair_back.png?v=5' },
  { key: 'face', name: 'face', src: '../assets/full_body_layers/face_base.png?v=5' },
  { key: 'eyeL', name: 'eye-l', src: '../assets/full_body_layers/eye_l.png?v=5' },
  { key: 'eyeR', name: 'eye-r', src: '../assets/full_body_layers/eye_r.png?v=5' },
  { key: 'browL', name: 'brow-l', src: '../assets/full_body_layers/brow_l.png?v=5' },
  { key: 'browR', name: 'brow-r', src: '../assets/full_body_layers/brow_r.png?v=5' },
  { key: 'nose', name: 'nose', src: '../assets/full_body_layers/nose.png?v=5' },
  { key: 'mouth', name: 'mouth', src: '../assets/full_body_layers/mouth.png?v=5' },
  { key: 'hairFront', name: 'hair-front', src: '../assets/full_body_layers/hair_front.png?v=5' },
];

function setLayer(el, tx, ty, sx = 1, sy = 1, rot = 0, skew = 0) {
  if (!el) return;
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

function initRig() {
  rig.innerHTML = "";
  activeLayers = {};
  
  layersConfig.forEach((cfg, index) => {
    const img = document.createElement("img");
    img.className = `layer ${cfg.name}`;
    img.src = cfg.src;
    img.style.zIndex = index + 1;
    rig.appendChild(img);
    activeLayers[cfg.key] = img;
  });
  
  applyRig();
}

function applyRig() {
  const x = Number(xInput.value);
  const y = Number(yInput.value);

  // Expression values
  const eyeOpenL = Number(eyeOpenLInput.value);
  const eyeOpenR = Number(eyeOpenRInput.value);
  const mouthOpen = Number(mouthOpenInput.value);
  const mouthForm = Number(mouthFormInput.value);

  xOut.value = x.toFixed(2);
  yOut.value = y.toFixed(2);
  state.textContent = labelFor(x, y);

  // Update expression outputs
  eyeLOut.value = eyeOpenL.toFixed(2);
  eyeROut.value = eyeOpenR.toFixed(2);
  mouthOpenOut.value = mouthOpen.toFixed(2);
  mouthFormOut.value = mouthForm.toFixed(2);

  // Dynamic 3D tilt for the entire full-body rig
  rig.style.transform = `translate(-50%, -50%) rotateY(${x * -6}deg) rotateX(${y * 4}deg)`;

  // Ribbons back (Z-index 1)
  setLayer(activeLayers.ribbonsBack, x * 8, y * -6, 1 + Math.abs(x) * .02, 1, x * 1.2, x * -0.8);
  
  // Legs (Z-index 2-3)
  setLayer(activeLayers.legLeft, x * -1.5, y * 1.2, 1, 1, x * -0.2, 0);
  setLayer(activeLayers.legRight, x * -1.5, y * 1.2, 1, 1, x * -0.2, 0);
  
  // Torso (Z-index 4)
  setLayer(activeLayers.torso, x * -6, y * 3.5, 1 - Math.abs(x) * .01, 1 + y * .006, x * -0.8, x * 0.5);
  
  // Arms (Z-index 5-6)
  setLayer(activeLayers.armLeft, x * -8, y * 4.5, 1, 1, x * -1.2, x * 0.8);
  setLayer(activeLayers.armRight, x * -8, y * 4.5, 1, 1, x * -1.2, x * 0.8);
  
  // Head parts (Z-index 7-15)
  setLayer(activeLayers.hairBack, x * -14, y * 6, 1 + Math.abs(x) * .012, 1 + y * .012, x * -1.8, x * 1.0);
  setLayer(activeLayers.face, x * -22, y * 14, 1 - Math.abs(x) * .018, 1 + y * .012, x * -1.0, x * .8);
  
  // Blink/scale eyes with vertical scaling (sy * eyeOpen)
  setLayer(activeLayers.eyeL, x * -18 + Math.max(x, 0) * -7, y * 10, 1 - x * .05, (1 - Math.abs(x) * .04) * eyeOpenL, x * -1.8, x * 1.6);
  setLayer(activeLayers.eyeR, x * -18 + Math.min(x, 0) * -7, y * 10, 1 + x * .05, (1 - Math.abs(x) * .04) * eyeOpenR, x * -1.8, x * 1.6);
  
  setLayer(activeLayers.browL, x * -17 + Math.max(x, 0) * -6, y * 9 - 2, 1 - x * .04, 1, x * -2, x * 1.5);
  setLayer(activeLayers.browR, x * -17 + Math.min(x, 0) * -6, y * 9 - 2, 1 + x * .04, 1, x * -2, x * 1.5);
  setLayer(activeLayers.nose, x * -28, y * 12, 1 - Math.abs(x) * .06, 1 + y * .03, x * -2.5, x * 2.8);
  
  // Open/scale mouth (sy * (1 + mouthOpen)) and smiling (sx * (1 + mouthForm * 0.1))
  setLayer(activeLayers.mouth, x * -20, y * 16, 1 - Math.abs(x) * .045 + mouthForm * 0.1, (1 + y * .025) * (1 + mouthOpen * 0.8), x * -1.6, x * 1.5);
  
  setLayer(activeLayers.hairFront, x * -26, y * 20, 1 + Math.abs(x) * .015, 1 + y * .02, x * -2.6, x * 1.5);

  const shade = Math.abs(x) * 0.12 + Math.max(y, 0) * 0.06;
  const shadowFilter = `drop-shadow(${x * -3}px ${3 + y * 2}px ${8 + Math.abs(x) * 4}px rgba(84,38,12,${0.1 + shade}))`;
  
  // Apply drop-shadow only to major structural layers to give depth
  [activeLayers.torso, activeLayers.face, activeLayers.hairBack, activeLayers.hairFront, activeLayers.armLeft, activeLayers.armRight].forEach((el) => {
    if (el) el.style.filter = shadowFilter;
  });
  
  // Clear drop-shadow for secondary facial details
  [activeLayers.eyeL, activeLayers.eyeR, activeLayers.browL, activeLayers.browR, activeLayers.nose, activeLayers.mouth, activeLayers.legLeft, activeLayers.legRight, activeLayers.ribbonsBack].forEach((el) => {
    if (el) el.style.filter = "none";
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

// Listen to expression inputs
[eyeOpenLInput, eyeOpenRInput, mouthOpenInput, mouthFormInput].forEach((input) => {
  input.addEventListener("input", applyRig);
});

// Initialize with the full-body rig
initRig();
