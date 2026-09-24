// stage.js — Vyond-style stage for Inochi2D puppets: parallax backgrounds + several puppets + camera,
// driven by the timeline.json that live2d/make_video.py compiles.  Deterministic: frame i always looks the same
// (random blinks are seeded, springs are stepped at the video frame rate from the start of each scene).
import { loadINP, Puppet } from './inochi-lite.js';

const W = 1920, H = 1080;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
export const FEET = { red_hood: 996, wolf: 999, red_hood_side: 961, wolf_side: 971 };
const TURN_AT = 0.18, TURN_FADE = 0.16;   // walk start: head turns 30 deg first, then front -> profile cross-fade         // lowest opaque row of the puppet (puppet units, y down)
const TALL = { red_hood: 1901, wolf: 1886 };       // head top -> feet, puppet units

function rng(seed) {                                // mulberry32
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export class GL {                     // also used by the web demo (transparent canvas of any size)
  constructor(canvas, { alpha = false } = {}) {
    this.canvas = canvas;
    const gl = (this.gl = canvas.getContext('webgl2', { premultipliedAlpha: true, alpha, antialias: true,
      preserveDrawingBuffer: true }));
    const vs = `#version 300 es
      in vec2 aPos; in vec2 aUV; uniform vec4 uView; out vec2 vUV;
      void main(){ vUV=aUV; gl_Position=vec4(aPos.x*uView.x+uView.z, -(aPos.y*uView.y+uView.w), 0., 1.); }`;
    const fs = `#version 300 es
      precision mediump float; in vec2 vUV; uniform sampler2D uTex; uniform float uOpacity; out vec4 o;
      void main(){ o = texture(uTex, vUV) * uOpacity; }`;
    const sh = (t, s) => { const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x);
      if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; };
    const p = (this.prog = gl.createProgram());
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
    this.loc = { pos: gl.getAttribLocation(p, 'aPos'), uv: gl.getAttribLocation(p, 'aUV'),
      view: gl.getUniformLocation(p, 'uView'), op: gl.getUniformLocation(p, 'uOpacity') };
    this.posBuf = gl.createBuffer(); this.uvBuf = gl.createBuffer(); this.idxBuf = gl.createBuffer();
    this.black = this.texture(Object.assign(document.createElement('canvas'), { width: 2, height: 2 }), '#000');
  }

  // upload premultiplied on the CPU (filtering straight alpha draws dark fringes)
  texture(src, fill) {
    const gl = this.gl, cv = document.createElement('canvas'), cx = cv.getContext('2d', { willReadFrequently: true });
    cv.width = src.width; cv.height = src.height;
    if (fill) { cx.fillStyle = fill; cx.fillRect(0, 0, cv.width, cv.height); } else cx.drawImage(src, 0, 0);
    const px = cx.getImageData(0, 0, cv.width, cv.height).data;
    for (let i = 0; i < px.length; i += 4) {
      const a = px[i + 3] / 255;
      px[i] = Math.round(px[i] * a); px[i + 1] = Math.round(px[i + 1] * a); px[i + 2] = Math.round(px[i + 2] * a);
    }
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, cv.width, cv.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(px.buffer));
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  get w() { return this.canvas.width; }
  get h() { return this.canvas.height; }

  begin(clear = [0, 0, 0, 1]) {
    const gl = this.gl;
    gl.viewport(0, 0, this.w, this.h); gl.clearColor(...clear); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.useProgram(this.prog);
  }

  // local px -> screen px = p * k + (ox, oy)
  mesh(pos, uvs, idx, tex, k, ox, oy, opacity = 1) {      // k: scale, or [kx, ky] (kx < 0 mirrors)
    const gl = this.gl, kx = Array.isArray(k) ? k[0] : k, ky = Array.isArray(k) ? k[1] : k, w = this.w, h = this.h;
    gl.uniform4f(this.loc.view, 2 * kx / w, 2 * ky / h, 2 * ox / w - 1, 2 * oy / h - 1);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuf); gl.bufferData(gl.ARRAY_BUFFER, pos, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(this.loc.pos); gl.vertexAttribPointer(this.loc.pos, 2, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.uvBuf); gl.bufferData(gl.ARRAY_BUFFER, uvs, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(this.loc.uv); gl.vertexAttribPointer(this.loc.uv, 2, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.idxBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.DYNAMIC_DRAW);
    gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1f(this.loc.op, opacity);
    gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
  }

  // offscreen layer: draw a whole puppet, then composite it with one opacity (a cross-fade must not show
  // the puppet's inner layers through each other)
  layer(i) {
    const gl = this.gl;
    this.layers = this.layers || [];
    if (this.layers[i] && (this.layers[i].w !== this.w || this.layers[i].h !== this.h)) this.layers[i] = null;
    if (!this.layers[i]) {
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, this.w, this.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      this.layers[i] = { fb, tex, w: this.w, h: this.h };
    }
    return this.layers[i];
  }

  toLayer(i, draw) {
    const gl = this.gl, L = this.layer(i);
    gl.bindFramebuffer(gl.FRAMEBUFFER, L.fb);
    gl.viewport(0, 0, this.w, this.h); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    draw();
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.w, this.h);
  }

  showLayer(i, opacity) {                   // framebuffer textures are bottom-up: flip v
    const w = this.w, h = this.h;
    this.mesh(new Float32Array([0, 0, w, 0, w, h, 0, h]), new Float32Array([0, 1, 1, 1, 1, 0, 0, 0]),
      new Uint16Array([0, 1, 2, 0, 2, 3]), this.layer(i).tex, 1, 0, 0, opacity);
  }

  quad(tex, w, h, k, ox, oy, opacity = 1) {
    this.mesh(new Float32Array([0, 0, w, 0, w, h, 0, h]), new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]),
      new Uint16Array([0, 1, 2, 0, 2, 3]), tex, k, ox, oy, opacity);
  }

  // only: undefined = whole puppet; 'body' = parts not under the Head node; 'headBack' / 'headFront' = head
  // parts drawn behind / in front of the neck (back hair and the back of a hood must stay behind the body)
  puppet(p, texs, k, ox, oy, only) {
    if (only) {
      if (!p._headTagged) {
        for (const n of p.parts) { let q = n.parent, h = false; while (q) { if (q.name === 'Head') { h = true; break; } q = q.parent; } n.inHead = h; }
        p._headTagged = true;
      }
      const neck = p.parts.find((n) => n.name === '脖子');
      p._neckZ = neck ? neck.z : -Infinity;
    }
    const keep = (n) => !only || (only === 'body' ? !n.inHead
      : n.inHead && ((only === 'headBack') === (n.z > p._neckZ)));
    const order = [...p.parts].filter((n) => n.enabled && keep(n)).sort((a, b) => b.z - a.z);
    for (const n of order) {
      const m = n.mesh, M = n.world, nv = m.verts.length / 2;
      const pos = new Float32Array(nv * 2);
      for (let i = 0; i < nv; i++) {
        let x = m.verts[2 * i], y = m.verts[2 * i + 1];
        if (n.deform) { x += n.deform[2 * i]; y += n.deform[2 * i + 1]; }
        pos[2 * i] = M[0] * x + M[2] * y + M[4];
        pos[2 * i + 1] = M[1] * x + M[3] * y + M[5];
      }
      if (!m._uv) { m._uv = new Float32Array(m.uvs); m._idx = new Uint16Array(m.indices); }
      this.mesh(pos, m._uv, m._idx, texs[n.textures[0]], k, ox, oy, n.opacity ?? 1);
    }
  }
}

// ------------------------------------------------------------------------------------------------ actor
class Actor {
  constructor(spec, sceneT0, fps, puppet, side) {
    this.s = spec; this.t0 = sceneT0; this.fps = fps; this.p = puppet;
    this.side = side || null;                  // {p, joints}: profile puppet used while walking
    if (side) {
      const j = side.joints;
      this.Lt = j['Shin F'][1] - j['Thigh F'][1]; this.Ls = j['Foot F'][1] - j['Shin F'][1];
      this.sideFeet = FEET[spec.side];
    }
    this.k = spec.height / TALL[spec.puppet];
    this.feet = FEET[spec.puppet];
    const r = rng([...spec.id].reduce((a, c) => a * 31 + c.charCodeAt(0), 7) + Math.round(sceneT0 * 10));
    this.blinks = []; for (let t = 0.8 + r() * 1.5; t < 400; t += 2.2 + r() * 3.2) this.blinks.push(t);
    this.reset();
  }

  reset() {
    this.st = { yaw: this.s.look, pitch: 0, roll: 0, armR: 0, armL: 0, bendR: 0, bendL: 0, wR: 0, wL: 0,
      vYaw: 0, hair: 0, hairV: 0, basket: 0, basketV: 0, phase: 0, x: this.s.x, prevX: this.s.x,
      sb: 0, sbV: 0, sh: 0, shV: 0, lastDir: 1 };
  }

  // 0 = front puppet, 1 = profile puppet; natural turn: nine-axis head turn first, then a short cross-fade
  sideWeight(t) {
    let w = 0;
    for (const s of this.s.walks) {
      const fin = clamp((t - (s.t0 + TURN_AT)) / TURN_FADE, 0, 1);
      const fout = clamp((s.t1 - t) / TURN_FADE, 0, 1);
      w = Math.max(w, Math.min(fin, fout));
    }
    return this.side ? w : 0;
  }

  // side puppet's Head:: Turn (1 = 70 deg half-profile, 0 = 90 deg profile): it arrives at 70 deg (matching the
  // front view's 30 deg as closely as one drawing can), then eases to 90 deg; the reverse before stopping
  turnAt(t) {
    let v = 0;
    for (const s of this.s.walks) {
      const a = s.t0 + TURN_AT + TURN_FADE, b = s.t1 - TURN_FADE;
      v = Math.max(v, t < s.t0 || t > s.t1 ? 0 : Math.max(1 - ease((t - a) / 0.3), 1 - ease((b - t) / 0.3)));
    }
    return v;
  }

  xAt(t) {                                    // absolute time -> ground x (walks are eased segments)
    let x = this.s.x, walking = 0, dir = 0, active = false;
    for (const w of this.s.walks) {
      if (t <= w.t0) break;
      const from = x, u = clamp((t - w.t0) / (w.t1 - w.t0), 0, 1);
      // trapezoid velocity profile: 12% accel / decel ramps
      const r = 0.12, vm = 1 / (1 - r);
      const v = u < r ? vm * u * u / (2 * r) : u > 1 - r ? 1 - vm * (1 - u) * (1 - u) / (2 * r) : vm * (u - r / 2);
      x = from + (w.to - from) * v;
      if (u < 1) { walking = u < r ? u / r : u > 1 - r ? (1 - u) / r : 1; dir = Math.sign(w.to - from); active = true; }
    }
    return { x, walking, dir, active };
  }

  env(t) {
    for (const c of this.s.talk) {
      const i = Math.floor((t - c.t0) * this.fps);
      if (i >= 0 && i < c.env.length) return c.env[i];
    }
    return 0;
  }

  gesture(t) {                                 // -> {type, w} with ramped weight
    let best = null;
    for (const g of this.s.gestures) {
      const w = Math.min(ease((t - g.t0) / 0.35), ease((g.t1 + 0.4 - t) / 0.45));
      if (w > 0 && (!best || w > best.w)) best = { type: g.type, w, t: t - g.t0 };
    }
    return best;
  }

  lookAt(t) {
    let v = this.s.look;
    for (const l of this.s.looks) if (t >= l.t) v = l.v;
    return v;
  }

  // advance springs one frame and set puppet params
  step(t) {
    const dt = 1 / this.fps, st = this.st, p = this.p;
    const lt = t - this.t0;
    const { x, walking, dir, active } = this.xAt(t);
    st.prevX = st.x; st.x = x;
    if (dir) st.lastDir = dir;
    // half-cycle stride: with the side rig it is exactly what the legs cover (2 L sin A) -> feet do not slide
    const stride = this.side ? 2 * (this.Lt + this.Ls) * this.k * Math.sin(0.42) : 0.26 * this.s.height;
    st.phase += (Math.abs(st.x - st.prevX) / stride) * Math.PI;
    const ph = st.phase, wk = walking;
    const talk = this.env(t);
    const g = this.gesture(t);

    // targets
    let yaw = this.lookAt(t), pitch = 0, roll = 0;
    let armR = 0.05 * Math.sin(lt * 0.9 + 1), armL = -0.05 * Math.sin(lt * 0.8), bendR = 0.08, bendL = 0.08,
      wR = 0.1 * Math.sin(lt * 1.1), wL = 0.1 * Math.sin(lt * 1.3 + 2), bob = 0;
    if (active) yaw = st.lastDir * 1.0;          // turn the head the full 30 deg toward where she walks
    if (wk > 0) {
      armR += wk * 0.85 * Math.sin(ph); armL += -wk * 0.85 * Math.sin(ph);
      bendR += wk * 0.25; bendL += wk * 0.25;
      roll += wk * 0.06 * Math.sin(ph);
      bob = -wk * Math.abs(Math.cos(ph)) * 0.012 * this.s.height;
      pitch += wk * 0.08 * Math.cos(2 * ph);
    }
    if (g) {
      const w = g.w, T = g.t;
      switch (g.type) {
        case 'shy':
          bendR += w * 0.8; bendL += w * 0.8; armR -= w * 0.5; armL -= w * 0.5; roll += w * 0.35; pitch += w * 0.35;
          wR += w * 0.4 * Math.sin(T * 2.2); break;
        case 'explain':
          bendR += w * 0.75; armR += w * (0.35 + 0.25 * Math.sin(T * 2.6)); wR += w * 0.8 * Math.sin(T * 3.3);
          roll += w * 0.08 * Math.sin(T * 1.7); break;
        case 'sly':
          bendL += w * 0.85; wL += w * (0.6 + 0.3 * Math.sin(T * 4)); bendR += w * 0.5; roll -= w * 0.25; pitch += w * 0.2;
          break;
        case 'point':
          armR += w * 1.0; bendR -= w * 0.05; wR -= w * 0.6; roll += w * 0.1; break;
        case 'happy':
          bendR += w * 0.6; bendL += w * 0.6; armR += w * 0.6; armL += w * 0.6;
          roll += w * 0.18 * Math.sin(T * 5); bob -= w * Math.max(0, Math.sin(T * 9)) * 0.012 * this.s.height;
          wR += w * 0.6 * Math.sin(T * 8); wL -= w * 0.6 * Math.sin(T * 8); break;
      }
    }
    for (const n of this.s.nods) {
      const u = t - n.t;
      if (u > 0 && u < 0.9) pitch += 0.7 * Math.sin((u / 0.9) * Math.PI * 2) ** 2 * (u < 0.45 ? 1 : 0.6);
    }
    if (talk > 0) { pitch += 0.12 * talk * Math.sin(lt * 7); roll += 0.04 * Math.sin(lt * 2.3); }

    // springs (critically-damped-ish exponential smoothing, arms a little laggy and asymmetric)
    const sm = (cur, tgt, rate) => cur + (tgt - cur) * (1 - Math.exp(-rate * dt));
    const prevYaw = st.yaw;
    st.yaw = sm(st.yaw, yaw, active ? 11 : 6); st.pitch = sm(st.pitch, pitch, 12); st.roll = sm(st.roll, roll, 6);
    st.armR = sm(st.armR, armR, wk > 0 ? 14 : 6.5); st.armL = sm(st.armL, armL, wk > 0 ? 14 : 5.5);
    st.bendR = sm(st.bendR, bendR, 7); st.bendL = sm(st.bendL, bendL, 6);
    st.wR = sm(st.wR, wR, 9); st.wL = sm(st.wL, wL, 8);
    // hair / basket / tail: driven pendulums
    const drive = -(st.yaw - prevYaw) / dt * 0.25 - wk * 0.15 * dir + wk * 0.25 * Math.sin(2 * ph);
    st.hairV += (-40 * (st.hair - drive) - 5 * st.hairV) * dt; st.hair += st.hairV * dt;
    const bd = (st.armR - armR) * 1.5 + wk * 0.4 * Math.sin(ph - 0.6);
    st.basketV += (-30 * (st.basket - bd) - 4 * st.basketV) * dt; st.basket += st.basketV * dt;

    // blink
    let blink = 0;
    for (const b of this.blinks) { const u = lt - b; if (u > -0.1 && u < 0.2) blink = Math.max(blink, 1 - Math.abs(u - 0.05) / 0.12); }
    blink = clamp(blink, 0, 1);

    p.set('Head:: Yaw-Pitch', clamp(st.yaw, -1, 1), clamp(-st.pitch, -1, 1));
    p.set('Head:: Roll', clamp(st.roll, -1, 1));
    p.set('Eye:: Left:: Blink', blink); p.set('Eye:: Right:: Blink', blink);
    p.set('Mouth:: Open', clamp(talk * 1.1, 0, 1));
    p.set('Body:: Breath', 0.5 + 0.5 * Math.sin((lt / 3.4) * Math.PI * 2));
    p.set('Arm:: Right:: Swing', clamp(st.armR, -1, 1)); p.set('Arm:: Left:: Swing', clamp(st.armL, -1, 1));
    p.set('Arm:: Right:: Bend', clamp(st.bendR, 0, 1)); p.set('Arm:: Left:: Bend', clamp(st.bendL, 0, 1));
    p.set('Hand:: Right:: Wrist', clamp(st.wR, -1, 1)); p.set('Hand:: Left:: Wrist', clamp(st.wL, -1, 1));
    p.set('Leg:: Right:: Step', wk * Math.max(0, Math.sin(ph))); p.set('Leg:: Left:: Step', wk * Math.max(0, -Math.sin(ph)));
    p.set('Hair:: Sway', clamp(st.hair + 0.08 * Math.sin(lt * 1.4), -1, 1));
    p.set('Basket:: Swing', clamp(st.basket, -1, 1));
    p.set('Tail:: Sway', clamp(0.55 * Math.sin(lt * 2.1) + wk * 0.4 * Math.sin(ph * 2) + 0.4 * talk, -1, 1));
    this.bob = bob;
    this.sideW = this.sideWeight(t);
    if (this.sideW > 0) this.stepSide(lt, ph, wk, talk, blink, dt);
  }

  // profile walk: joint angles in radians (+ = forward); body height follows the supporting leg
  stepSide(lt, ph, wk, talk, blink, dt) {
    const p = this.side.p, st = this.st, s = Math.sin(ph), c = Math.cos(ph), A = 0.42 * wk;
    const hipF = A * s, hipB = -A * s;
    const kneeF = wk * (0.06 + 0.8 * Math.max(0, c) ** 2), kneeB = wk * (0.06 + 0.8 * Math.max(0, -c) ** 2);
    const hF = this.Lt * Math.cos(hipF) + this.Ls * Math.cos(kneeF - hipF);
    const hB = this.Lt * Math.cos(hipB) + this.Ls * Math.cos(kneeB - hipB);
    this.sideDrop = (this.Lt + this.Ls - Math.max(hF, hB)) * this.k;
    const armF = -0.36 * wk * s, armB = 0.36 * wk * s;
    const elbF = 0.18 + 0.3 * wk * Math.max(0, -s), elbB = 0.18 + 0.3 * wk * Math.max(0, s);
    // basket / braid / tail: pendulums driven by the stride
    st.sbV += (-35 * (st.sb - 0.25 * wk * Math.sin(ph - 0.8)) - 4 * st.sbV) * dt; st.sb += st.sbV * dt;
    st.shV += (-30 * (st.sh - (-0.12 * wk + 0.08 * Math.sin(2 * ph))) - 4 * st.shV) * dt; st.sh += st.shV * dt;
    p.set('Leg:: Front:: Hip', hipF); p.set('Leg:: Front:: Knee', kneeF); p.set('Leg:: Front:: Foot', (kneeF - hipF) * 0.85);
    p.set('Leg:: Back:: Hip', hipB); p.set('Leg:: Back:: Knee', kneeB); p.set('Leg:: Back:: Foot', (kneeB - hipB) * 0.85);
    p.set('Arm:: Front:: Swing', armF); p.set('Arm:: Front:: Elbow', elbF);
    p.set('Arm:: Back:: Swing', armB); p.set('Arm:: Back:: Elbow', elbB);
    p.set('Basket:: Swing', clamp(-(armF + elbF) + st.sb, -1, 1));
    p.set('Hair:: Sway', clamp(st.sh, -1, 1));
    p.set('Tail:: Sway', clamp(0.25 * Math.sin(ph * 2) + 0.15 * Math.sin(lt * 2.1), -1, 1));
    p.set('Head:: Nod', -(0.025 * Math.sin(2 * ph) + 0.05 * talk * Math.sin(lt * 7)));
    p.set('Body:: Lean', -0.05 * wk);
    p.set('Eye:: Blink', blink);
    p.set('Head:: Turn', this.turnAt(this.t0 + lt));
    p.set('Mouth:: Open', clamp(talk * 1.1, 0, 1));
    p.set('Body:: Breath', 0.5 + 0.5 * Math.sin((lt / 3.4) * Math.PI * 2));
  }
}

// ------------------------------------------------------------------------------------------------ stage
export class Stage {
  constructor(canvas, timeline, bgs, base) {
    this.gl = new GL(canvas); this.tl = timeline; this.bgs = bgs; this.base = base;
    this.last = -2; this.sceneIdx = -1;
  }

  async load() {
    const img = (u) => new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = u; });
    this.bgTex = {};
    for (const sc of new Set(this.tl.scenes.map((s) => s.bg))) {
      const m = this.bgs[sc];
      this.bgTex[sc] = { width: m.width, height: m.height,
        layers: await Promise.all(m.layers.map(async (l) => ({ ...l, tex: this.gl.texture(await img(`${this.base}/backgrounds/${l.file}`)) }))) };
    }
    this.puppets = {};
    // one Puppet instance per actor per scene would be wasteful; one per puppet id + its textures is enough
    // as long as each actor sets all of its params before its own update() (actors are drawn one by one).
    for (const id of new Set(this.tl.scenes.flatMap((s) => s.actors.map((a) => a.puppet)))) {
      const d = await loadINP(`${this.base}/characters/${id}/${id}.inp`);
      const p = new Puppet(d);
      this.puppets[id] = { p, tex: d.textures.map((b) => this.gl.texture(b)) };
    }
    for (const id of new Set(this.tl.scenes.flatMap((s) => s.actors.map((a) => a.side)).filter(Boolean))) {
      const d = await loadINP(`${this.base}/characters/${id}/${id}.inp`);
      const joints = await (await fetch(`${this.base}/characters/${id}/joints.json`)).json();
      this.puppets[id] = { p: new Puppet(d), tex: d.textures.map((b) => this.gl.texture(b)), joints };
    }
  }

  scene(t) {
    const S = this.tl.scenes;
    for (let i = 0; i < S.length; i++) if (t < S[i].t1 || i === S.length - 1) return i;
  }

  enterScene(i) {
    const sc = this.tl.scenes[i];
    this.sceneIdx = i;
    this.actors = sc.actors.map((a) => new Actor(a, sc.t0, this.tl.fps, this.puppets[a.puppet].p,
      a.side ? this.puppets[a.side] : null));
  }

  camera(sc, t) {
    const u = (t - sc.t0) / (sc.t1 - sc.t0), K = sc.camera;
    let a = K[0], b = K[K.length - 1];
    for (let i = 0; i < K.length - 1; i++) if (u >= K[i].at && u <= K[i + 1].at) { a = K[i]; b = K[i + 1]; }
    const w = b.at > a.at ? ease((u - a.at) / (b.at - a.at)) : 0;
    const L = (k) => a[k] + (b[k] - a[k]) * w;
    return { x: L('x'), y: L('y'), zoom: L('zoom') };
  }

  // render frame i (must be called in order for springs; out-of-order calls fast-forward from the scene start)
  frame(i) {
    const fps = this.tl.fps, t = i / fps;
    const si = this.scene(t), sc = this.tl.scenes[si];
    if (si !== this.sceneIdx || i !== this.last + 1) {
      this.enterScene(si);
      for (let j = Math.ceil(sc.t0 * fps); j < i; j++) for (const a of this.actors) a.step(j / fps);
    }
    this.last = i;
    for (const a of this.actors) a.step(t);

    const gl = this.gl, bg = this.bgTex[sc.bg], cam = this.camera(sc, t), z = cam.zoom;
    const cy = clamp(cam.y, H / 2 / z, bg.height - H / 2 / z);
    const offX = (par) => clamp(cam.x * par + (bg.width / 2) * (1 - par), W / 2 / z, bg.width - W / 2 / z);
    gl.begin();
    const layer = (l) => gl.quad(l.tex, bg.width, bg.height, z, -offX(l.parallax) * z + W / 2, -cy * z + H / 2);
    for (const l of bg.layers) if (l.parallax <= 1 && !l.front) layer(l);
    const gx = offX(1);
    for (const a of [...this.actors].sort((m, n) => m.s.y - n.s.y)) {
      const k = a.k * z, sx = (a.st.x - gx) * z + W / 2, gy = (a.s.y - cy) * z + H / 2;
      const sw = a.sideW;
      const drawFront = (only) => {
        const P = this.puppets[a.s.puppet];
        a.p.update();
        gl.puppet(a.p, P.tex, k, sx, gy + a.bob * z - a.feet * k, only);
      };
      const drawSide = (only) => {             // profile puppet, mirrored when walking left
        const P = this.puppets[a.s.side];
        P.p.update();
        gl.puppet(P.p, P.tex, [a.st.lastDir < 0 ? -k : k, k], sx, gy - a.sideFeet * k + (a.sideDrop || 0) * z, only);
      };
      this.drawShadow(sx, gy, a.s.height * (0.2 + 0.06 * sw) * z, sw < 1 ? a.bob : 0);
      if (sw <= 0) drawFront();
      else if (sw >= 1) drawSide();
      else {
        // cross-fade the BODIES as whole images (not layer by layer); the HEAD comes from exactly one puppet
        // (switches at the midpoint, full opacity) -- never two noses / two mouths on screen
        const head = sw < 0.5 ? drawFront : drawSide;
        head('headBack');                                   // back hair / hood back: behind the bodies
        gl.toLayer(0, () => drawFront('body')); gl.toLayer(1, () => drawSide('body'));
        gl.showLayer(0, 1 - sw); gl.showLayer(1, sw);
        head('headFront');
      }
    }
    for (const l of bg.layers) if (l.parallax > 1 || l.front) layer(l);      // foreground: quilt, table, bushes
    // fade in/out at scene cuts
    const fin = ease((t - sc.t0) / 0.4), fout = ease((sc.t1 - t) / 0.4);
    const black = 1 - Math.min(si === 0 ? ease(t / 0.6) : fin, si === this.tl.scenes.length - 1 ? ease((sc.t1 - t) / 0.9) : fout);
    if (black > 0.001) gl.quad(gl.black, W, H, 1, 0, 0, black);
  }

  shadowTex() {
    if (!this._sh) {
      const c = Object.assign(document.createElement('canvas'), { width: 128, height: 32 }), x = c.getContext('2d');
      const g = x.createRadialGradient(64, 16, 2, 64, 16, 64);
      g.addColorStop(0, 'rgba(40,30,20,0.42)'); g.addColorStop(1, 'rgba(40,30,20,0)');
      x.setTransform(1, 0, 0, 0.25, 0, 12); x.fillStyle = g; x.fillRect(0, 0, 128, 128);
      this._sh = this.gl.texture(c);
    }
    return this._sh;
  }

  drawShadow(sx, sy, w, bob) {
    const s = w / 128 * (1 + bob / 200);
    this.gl.quad(this.shadowTex(), 128, 32, s, sx - 64 * s, sy - 16 * s);
  }
}
