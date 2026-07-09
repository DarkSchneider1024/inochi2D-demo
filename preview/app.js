const stage = document.querySelector("#stage");
const rig = document.querySelector("#rig");
const xInput = document.querySelector("#angle-x");
const yInput = document.querySelector("#angle-y");
const xOut = document.querySelector("#x-out");
const yOut = document.querySelector("#y-out");
const tracking = document.querySelector("#tracking");
const state = document.querySelector("#state");
const mainTitle = document.querySelector("#main-title");
const downloadBtn = document.querySelector("#download-btn");
const tabBtns = document.querySelectorAll(".tab-btn");

// Expressions controls
const eyeOpenLInput = document.querySelector("#eye-open-l");
const eyeOpenRInput = document.querySelector("#eye-open-r");
const mouthOpenInput = document.querySelector("#mouth-open");
const mouthFormInput = document.querySelector("#mouth-form");

const eyeLOut = document.querySelector("#eye-l-out");
const eyeROut = document.querySelector("#eye-r-out");
const mouthOpenOut = document.querySelector("#mouth-open-out");
const mouthFormOut = document.querySelector("#mouth-form-out");

let currentWork = "1";
let activeLayers = {};

const work1Config = [
  { key: 'hairBack', name: 'hair-back', src: '../assets/native_head_layers/hair_back.png' },
  { key: 'face', name: 'face', src: '../assets/native_head_layers/face_base.png' },
  { key: 'browL', name: 'brow-l', src: '../assets/native_head_layers/brow_l.png' },
  { key: 'browR', name: 'brow-r', src: '../assets/native_head_layers/brow_r.png' },
  { key: 'eyeL', name: 'eye-l', src: '../assets/native_head_layers/eye_l.png' },
  { key: 'eyeR', name: 'eye-r', src: '../assets/native_head_layers/eye_r.png' },
  { key: 'nose', name: 'nose', src: '../assets/native_head_layers/nose.png' },
  { key: 'mouth', name: 'mouth', src: '../assets/native_head_layers/mouth.png' },
  { key: 'hairFront', name: 'hair-front', src: '../assets/native_head_layers/hair_front.png' },
];

const work2Config = [
  { key: 'ribbonsBack', name: 'ribbons-back', src: '../assets/full_body_layers/ribbons_back.png' },
  { key: 'legLeft', name: 'leg-left', src: '../assets/full_body_layers/leg_left.png' },
  { key: 'legRight', name: 'leg-right', src: '../assets/full_body_layers/leg_right.png' },
  { key: 'torso', name: 'torso', src: '../assets/full_body_layers/torso.png' },
  { key: 'armLeft', name: 'arm-left', src: '../assets/full_body_layers/arm_left.png' },
  { key: 'armRight', name: 'arm-right', src: '../assets/full_body_layers/arm_right.png' },
  { key: 'hairBack', name: 'hair-back', src: '../assets/full_body_layers/hair_back.png' },
  { key: 'face', name: 'face', src: '../assets/full_body_layers/face_base.png' },
  { key: 'eyeL', name: 'eye-l', src: '../assets/full_body_layers/eye_l.png' },
  { key: 'eyeR', name: 'eye-r', src: '../assets/full_body_layers/eye_r.png' },
  { key: 'browL', name: 'brow-l', src: '../assets/full_body_layers/brow_l.png' },
  { key: 'browR', name: 'brow-r', src: '../assets/full_body_layers/brow_r.png' },
  { key: 'nose', name: 'nose', src: '../assets/full_body_layers/nose.png' },
  { key: 'mouth', name: 'mouth', src: '../assets/full_body_layers/mouth.png' },
  { key: 'hairFront', name: 'hair-front', src: '../assets/full_body_layers/hair_front.png' },
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

function loadWork(workId) {
  currentWork = workId;
  rig.innerHTML = "";
  activeLayers = {};
  
  const config = workId === "1" ? work1Config : work2Config;
  
  // Set class on rig for aspect ratio
  rig.className = workId === "1" ? "work-1" : "work-2";
  
  // Load layers
  config.forEach((cfg, index) => {
    const img = document.createElement("img");
    img.className = `layer ${cfg.name}`;
    img.src = cfg.src;
    img.style.zIndex = index + 1;
    rig.appendChild(img);
    activeLayers[cfg.key] = img;
  });
  
  // Update header and download button
  if (workId === "1") {
    mainTitle.textContent = "作品一 (頭部綁定預覽)";
    downloadBtn.textContent = "下載 .inx 模型";
    downloadBtn.href = "../models/carrot_vtuber_detailed_head.inx";
  } else {
    mainTitle.textContent = "作品二 (全身分層 PSD)";
    downloadBtn.textContent = "下載 .psd 圖層檔";
    downloadBtn.href = "../models/carrot_vtuber_detailed_head.psd";
  }
  
  // Update tabs buttons UI
  tabBtns.forEach(btn => {
    if (btn.getAttribute("data-work") === workId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
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

  // Update expression labels
  eyeLOut.value = eyeOpenL.toFixed(2);
  eyeROut.value = eyeOpenR.toFixed(2);
  mouthOpenOut.value = mouthOpen.toFixed(2);
  mouthFormOut.value = mouthForm.toFixed(2);

  if (currentWork === "1") {
    // WORK 1 (Head Only Rig)
    rig.style.transform = `translate(-50%, -52%) rotateY(${x * -9}deg) rotateX(${y * 5}deg)`;

    setLayer(activeLayers.hairBack, x * -22, y * 8, 1 + Math.abs(x) * .015, 1 + y * .015, x * -2.2, x * 1.2);
    setLayer(activeLayers.face, x * -10, y * 7, 1 - Math.abs(x) * .018, 1 + y * .012, x * -1.0, x * .8);
    setLayer(activeLayers.hairFront, x * -17, y * 12, 1 + Math.abs(x) * .01, 1 + y * .018, x * -2.8, x * 1.5);
    
    // Animate left/right eyes blinking with vertical scaling (sy * eyeOpen)
    setLayer(activeLayers.eyeL, x * -18 + Math.max(x, 0) * -7, y * 10, 1 - x * .05, (1 - Math.abs(x) * .04) * eyeOpenL, x * -1.8, x * 1.6);
    setLayer(activeLayers.eyeR, x * -18 + Math.min(x, 0) * -7, y * 10, 1 + x * .05, (1 - Math.abs(x) * .04) * eyeOpenR, x * -1.8, x * 1.6);
    
    setLayer(activeLayers.browL, x * -17 + Math.max(x, 0) * -6, y * 9 - 2, 1 - x * .04, 1, x * -2, x * 1.5);
    setLayer(activeLayers.browR, x * -17 + Math.min(x, 0) * -6, y * 9 - 2, 1 + x * .04, 1, x * -2, x * 1.5);
    setLayer(activeLayers.nose, x * -28, y * 12, 1 - Math.abs(x) * .06, 1 + y * .03, x * -2.5, x * 2.8);
    
    // Animate mouth opening (sy * (1 + mouthOpen)) and smiling (sx * (1 + mouthForm * 0.1))
    setLayer(activeLayers.mouth, x * -20, y * 16, 1 - Math.abs(x) * .045 + mouthForm * 0.1, (1 + y * .025) * (1 + mouthOpen * 0.8), x * -1.6, x * 1.5);

    const shade = Math.abs(x) * 0.12 + Math.max(y, 0) * 0.06;
    const shadowFilter = `drop-shadow(${x * -4}px ${4 + y * 2}px ${10 + Math.abs(x) * 6}px rgba(84,38,12,${0.12 + shade}))`;
    
    // Apply drop-shadow only to the main head and hair parts
    [activeLayers.face, activeLayers.hairBack, activeLayers.hairFront].forEach((el) => {
      if (el) el.style.filter = shadowFilter;
    });
    
    // Clear filter for facial features to prevent ugly seams
    [activeLayers.eyeL, activeLayers.eyeR, activeLayers.browL, activeLayers.browR, activeLayers.nose, activeLayers.mouth].forEach((el) => {
      if (el) el.style.filter = "none";
    });
  } else {
    // WORK 2 (Full Body Rig)
    // Dynamic 3D tilt for the entire body
    rig.style.transform = `translate(-50%, -52%) rotateY(${x * -6}deg) rotateX(${y * 4}deg)`;

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
    
    // Blink/scale eyes
    setLayer(activeLayers.eyeL, x * -18 + Math.max(x, 0) * -7, y * 10, 1 - x * .05, (1 - Math.abs(x) * .04) * eyeOpenL, x * -1.8, x * 1.6);
    setLayer(activeLayers.eyeR, x * -18 + Math.min(x, 0) * -7, y * 10, 1 + x * .05, (1 - Math.abs(x) * .04) * eyeOpenR, x * -1.8, x * 1.6);
    
    setLayer(activeLayers.browL, x * -17 + Math.max(x, 0) * -6, y * 9 - 2, 1 - x * .04, 1, x * -2, x * 1.5);
    setLayer(activeLayers.browR, x * -17 + Math.min(x, 0) * -6, y * 9 - 2, 1 + x * .04, 1, x * -2, x * 1.5);
    setLayer(activeLayers.nose, x * -28, y * 12, 1 - Math.abs(x) * .06, 1 + y * .03, x * -2.5, x * 2.8);
    
    // Open/scale mouth
    setLayer(activeLayers.mouth, x * -20, y * 16, 1 - Math.abs(x) * .045 + mouthForm * 0.1, (1 + y * .025) * (1 + mouthOpen * 0.8), x * -1.6, x * 1.5);
    
    setLayer(activeLayers.hairFront, x * -26, y * 20, 1 + Math.abs(x) * .015, 1 + y * .02, x * -2.6, x * 1.5);

    const shade = Math.abs(x) * 0.12 + Math.max(y, 0) * 0.06;
    const shadowFilter = `drop-shadow(${x * -3}px ${3 + y * 2}px ${8 + Math.abs(x) * 4}px rgba(84,38,12,${0.1 + shade}))`;
    
    // Apply shadows to major structural layers to give depth
    [activeLayers.torso, activeLayers.face, activeLayers.hairBack, activeLayers.hairFront, activeLayers.armLeft, activeLayers.armRight].forEach((el) => {
      if (el) el.style.filter = shadowFilter;
    });
    
    // Clear shadows for secondary elements/facial details
    [activeLayers.eyeL, activeLayers.eyeR, activeLayers.browL, activeLayers.browR, activeLayers.nose, activeLayers.mouth, activeLayers.legLeft, activeLayers.legRight, activeLayers.ribbonsBack].forEach((el) => {
      if (el) el.style.filter = "none";
    });
  }
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

// Hook up tab click events
tabBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    const workId = btn.getAttribute("data-work");
    loadWork(workId);
  });
});

// Initialize with Work 1
loadWork("1");
