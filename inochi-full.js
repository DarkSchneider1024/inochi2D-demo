// inochi-full.js — a WebGL2 player for "real" Inochi2D puppets made in Inochi Creator (0.7/0.8 INP),
// e.g. the official example models Aka and Midori. inochi-lite.js stays the small player for our own
// Python-built puppets; this one adds what Creator rigs use, following inochi2d v0.8 (D) and inox2d:
//   * 3-D node transforms: world = parent * T(trans + t_off) * Rz*Ry*Rx(rot + r_off) * S(scale * s_off)
//   * parameter bindings: transform.t/r/s.*, zSort, opacity, deform (bilinear between axis points)
//   * MeshGroup: children (stopping at nested groups) are warped through the group's deformed triangles;
//     dynamic_deformation looks up the already-deformed vertex, translate_children also moves plain Nodes
//   * masks (Mask / DodgeMask through the stencil buffer, alpha threshold), Composite (offscreen buffer),
//     blend modes Normal / Multiply / LinearDodge / ClipToLower / Screen, tint and screen tint
//   * SimplePhysics: Pendulum and SpringPendulum, XY and AngleLength output mapping
//   * animations (the 0.8 'animations' map: per-parameter lanes of keyframes) -- sampleAnimation() returns the values,
//     the page decides how to mix them (official.html: 動作 / 表情 loop, 手勢 once)
// Not implemented: Cubic interpolation (treated as linear), emission / bump maps.

const NONE = 4294967295;

export async function loadINP(url, onProgress) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const total = +res.headers.get('content-length') || 0;
  const chunks = []; let got = 0;
  const rd = res.body.getReader();
  for (;;) {
    const { done, value } = await rd.read();
    if (done) break;
    chunks.push(value); got += value.length;
    onProgress?.(total ? got / total : 0);
  }
  const buf = new Uint8Array(got); let o = 0;
  for (const c of chunks) { buf.set(c, o); o += c.length; }
  const dv = new DataView(buf.buffer);
  const tag = (p) => String.fromCharCode(...buf.slice(p, p + 8));
  if (tag(0) !== 'TRNSRTS\0') throw new Error('not an Inochi2D INP file');
  o = 8;
  const jlen = dv.getUint32(o); o += 4;
  const json = JSON.parse(new TextDecoder('utf-8').decode(buf.slice(o, o + jlen))); o += jlen;
  if (tag(o) !== 'TEX_SECT') throw new Error('missing TEX_SECT'); o += 8;
  const count = dv.getUint32(o); o += 4;
  const jobs = [];
  for (let i = 0; i < count; i++) {
    const len = dv.getUint32(o); const enc = buf[o + 4]; o += 5;
    if (enc !== 0) throw new Error('TGA textures: re-pack with tools/inx_to_inp.py');
    jobs.push(loadTexture(new Blob([buf.slice(o, o + len)], { type: 'image/png' })));
    o += len;
  }
  return { json, textures: await Promise.all(jobs), bytes: buf.length };
}

// Inochi Creator stores textures already premultiplied (rgb <= alpha everywhere); our Python-built
// puppets store straight alpha. Multiplying a premultiplied texture again darkens every soft edge
// (grey nose shadow, dark lip outline, dirty hair highlights), so look at the pixels and only
// premultiply straight ones. WebGL ignores UNPACK_PREMULTIPLY_ALPHA for ImageBitmap sources.
const probe = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
async function loadTexture(blob) {
  const raw = await createImageBitmap(blob, { premultiplyAlpha: 'none' });
  probe.canvas.width = raw.width; probe.canvas.height = raw.height;
  probe.clearRect(0, 0, raw.width, raw.height); probe.drawImage(raw, 0, 0);
  const px = probe.getImageData(0, 0, raw.width, raw.height).data;
  let soft = 0, over = 0;
  for (let i = 0; i < px.length; i += 4 * 3) {
    const a = px[i + 3];
    if (a < 24 || a > 232) continue;                  // low alpha rounds badly through the canvas
    soft++;
    if (Math.max(px[i], px[i + 1], px[i + 2]) > a + 6) over++;
  }
  if (soft && over / soft < 0.01) { raw.premultiplied = true; return raw; }
  raw.close();
  return createImageBitmap(blob, { premultiplyAlpha: 'premultiply' });
}

// ---- 4x4 column-major matrices (only the x/y rows matter for drawing, z is kept for 3-D rotation) ----
const mul = (A, B) => {
  const C = new Float64Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++)
    C[c * 4 + r] = A[r] * B[c * 4] + A[4 + r] * B[c * 4 + 1] + A[8 + r] * B[c * 4 + 2] + A[12 + r] * B[c * 4 + 3];
  return C;
};
const trs = (t, r, s) => {                     // T * Rz(r2) * Ry(r1) * Rx(r0) * S
  const [cx, sx] = [Math.cos(r[0]), Math.sin(r[0])], [cy, sy] = [Math.cos(r[1]), Math.sin(r[1])],
    [cz, sz] = [Math.cos(r[2]), Math.sin(r[2])];
  const R = [cz * cy, sz * cy, -sy, cz * sy * sx - sz * cx, sz * sy * sx + cz * cx, cy * sx,
    cz * sy * cx + sz * sx, sz * sy * cx - cz * sx, cy * cx];
  return Float64Array.of(R[0] * s[0], R[1] * s[0], R[2] * s[0], 0, R[3] * s[1], R[4] * s[1], R[5] * s[1], 0,
    R[6], R[7], R[8], 0, t[0], t[1], t[2], 1);
};
const inv2 = (M) => {                          // inverse of the 2-D affine part [a c e; b d f]
  const a = M[0], b = M[1], c = M[4], d = M[5], e = M[12], f = M[13], det = a * d - b * c || 1e-12;
  return [d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det];
};
const ap = (M, x, y) => [M[0] * x + M[4] * y + M[12], M[1] * x + M[5] * y + M[13]];
const ap2 = (I, x, y) => [I[0] * x + I[2] * y + I[4], I[1] * x + I[3] * y + I[5]];

export class Puppet {
  constructor({ json, textures }) {
    this.json = json;
    this.textures = textures;
    this.nodes = new Map();
    this.parts = []; this.groups = []; this.physics = [];
    const walk = (n, parent) => {
      const node = { ...n, parent };
      this.nodes.set(n.uuid, node);
      if (n.type === 'Part') this.parts.push(node);
      if (n.type === 'MeshGroup') this.groups.push(node);
      node.kids = (n.children || []).map((c) => walk(c, node));
      delete node.children;
      return node;
    };
    this.root = walk(json.nodes, null);
    for (const g of this.groups) this.prepGroup(g);

    this.params = json.param.map((p) => {
      const two = (v, d) => (Array.isArray(v) ? v : [v ?? d, 0]);
      const ax = p.axis_points || [[0, 1], [0]];
      return { ...p, defaults: two(p.defaults, 0), min: two(p.min, 0), max: two(p.max, 1),
        axis_points: [ax[0] || [0, 1], ax[1] || [0]], value: [...two(p.defaults, 0)] };
    });
    this.byName = Object.fromEntries(this.params.map((p) => [p.name.trim(), p]));
    this.byUuid = new Map(this.params.map((p) => [p.uuid, p]));
    const ph = json.physics || {};
    this.world = { ppm: ph.pixelsPerMeter ?? 1000, g: ph.gravity ?? 9.8 };
    for (const n of this.nodes.values()) if (n.type === 'SimplePhysics' && this.byUuid.has(n.param))
      this.physics.push({ node: n, param: this.byUuid.get(n.param), bob: null, v: [0, 0], ang: 0, dAng: 0 });

    // draw list (inochi2d Puppet.scanParts): Parts and their part children; a Composite is one entry
    // whose own sub-parts are drawn into an offscreen buffer
    this.drawList = [];
    const scanSub = (n, out) => { if (n.type === 'Part') out.push(n); for (const k of n.kids) scanSub(k, out); };
    const scan = (n) => {
      if (n.type === 'Part') { this.drawList.push(n); for (const k of n.kids) scan(k); }
      else if (n.type === 'Composite') { n.sub = []; for (const k of n.kids) scanSub(k, n.sub); this.drawList.push(n); }
      else for (const k of n.kids) scan(k);
    };
    scan(this.root);
    for (const n of this.nodes.values()) if (n.masks?.length)
      n.maskSrc = n.masks.map((m) => ({ src: this.nodes.get(m.source), dodge: m.mode === 'DodgeMask' })).filter((m) => m.src);
    this.update();
  }

  prepGroup(g) {                                // undeformed triangles for the barycentric lookup
    const v = g.mesh.verts, I = g.mesh.indices;
    g.tris = [];
    for (let i = 0; i < I.length; i += 3) {
      const [a, b, c] = [I[i], I[i + 1], I[i + 2]];
      const p = [v[2 * a], v[2 * a + 1]], e1 = [v[2 * b] - p[0], v[2 * b + 1] - p[1]], e2 = [v[2 * c] - p[0], v[2 * c + 1] - p[1]];
      const det = e1[0] * e2[1] - e1[1] * e2[0];
      if (Math.abs(det) < 1e-9) continue;
      g.tris.push({ a, b, c, p, inv: [e2[1] / det, -e1[1] / det, -e2[0] / det, e1[0] / det],
        x0: Math.min(v[2 * a], v[2 * b], v[2 * c]) - 0.01, x1: Math.max(v[2 * a], v[2 * b], v[2 * c]) + 0.01,
        y0: Math.min(v[2 * a + 1], v[2 * b + 1], v[2 * c + 1]) - 0.01, y1: Math.max(v[2 * a + 1], v[2 * b + 1], v[2 * c + 1]) + 0.01 });
    }
  }

  // point in the group's local space -> where the group's deformation moves it
  warp(g, x, y) {
    const d = g.deform, v = g.mesh.verts;
    for (const t of g.tris) {
      if (x < t.x0 || x > t.x1 || y < t.y0 || y > t.y1) continue;
      const dx = x - t.p[0], dy = y - t.p[1];
      const u = t.inv[0] * dx + t.inv[2] * dy, w = t.inv[1] * dx + t.inv[3] * dy;
      if (u < -1e-5 || w < -1e-5 || u + w > 1 + 1e-5) continue;
      if (!d) return [x, y];
      const q = (k) => [v[2 * k] + d[2 * k], v[2 * k + 1] + d[2 * k + 1]];
      const A = q(t.a), B = q(t.b), C = q(t.c);
      return [A[0] + u * (B[0] - A[0]) + w * (C[0] - A[0]), A[1] + u * (B[1] - A[1]) + w * (C[1] - A[1])];
    }
    return [x, y];
  }

  has(name) { return !!this.byName[name]; }

  // ---- animations: name -> {timestep, length (frames), lanes: [{uuid, target, keyframes: [{frame, value}]}]} ----
  get animations() { return this.json.animations || {}; }
  animationLength(name) { const a = this.animations[name]; return a ? a.length * a.timestep : 0; }
  sampleAnimation(name, t) {            // t in seconds -> [{param, axis, value}]; loops when the animation says so
    const a = this.animations[name];
    if (!a) return [];
    const len = a.length * a.timestep;
    t = a.loop === false ? Math.min(Math.max(t, 0), len) : ((t % len) + len) % len;
    const f = t / a.timestep, out = [];
    for (const l of a.lanes) {
      const p = this.byUuid.get(l.uuid), k = l.keyframes;
      if (!p || !k?.length) continue;
      let v = k[k.length - 1].value;
      for (let i = 0; i < k.length - 1; i++) {
        if (f > k[i + 1].frame) continue;
        const u = Math.min(1, Math.max(0, (f - k[i].frame) / ((k[i + 1].frame - k[i].frame) || 1)));
        v = /^(Nearest|Stepped)$/.test(l.interpolation) ? k[i].value : k[i].value + (k[i + 1].value - k[i].value) * u;
        break;
      }
      out.push({ param: p, axis: l.target || 0, value: v });
    }
    return out;
  }
  get(name) { return this.byName[name]?.value; }
  set(name, x, y) {
    const p = this.byName[name];
    if (!p) return;
    if (Array.isArray(x)) [x, y] = x;
    if (y === undefined) y = p.value[1];
    p.value = [Math.min(p.max[0], Math.max(p.min[0], x)), Math.min(p.max[1], Math.max(p.min[1], y))];
  }
  reset() {
    for (const p of this.params) p.value = [...p.defaults];
    for (const s of this.physics) { s.bob = null; s.v = [0, 0]; s.dAng = 0; }
  }

  static cell(points, t) {
    if (points.length === 1) return [0, 0, 0];
    for (let i = 0; i < points.length - 1; i++)
      if (t <= points[i + 1] || i === points.length - 2) {
        const span = points[i + 1] - points[i];
        return [i, i + 1, span > 0 ? Math.min(1, Math.max(0, (t - points[i]) / span)) : 0];
      }
  }

  update() {
    for (const n of this.nodes.values()) {
      n.off = { t: [0, 0, 0], r: [0, 0, 0], s: [1, 1], z: 0, op: 1 };
      n.deform = null;
    }
    for (const p of this.params) {
      const nx = (p.value[0] - p.min[0]) / ((p.max[0] - p.min[0]) || 1);
      const ny = p.is_vec2 ? (p.value[1] - p.min[1]) / ((p.max[1] - p.min[1]) || 1) : 0;
      const [x0, x1, wx] = Puppet.cell(p.axis_points[0], Math.min(1, Math.max(0, nx)));
      const [y0, y1, wy] = Puppet.cell(p.axis_points[1], Math.min(1, Math.max(0, ny)));
      const w00 = (1 - wx) * (1 - wy), w10 = wx * (1 - wy), w01 = (1 - wx) * wy, w11 = wx * wy;
      for (const b of p.bindings) {
        const n = this.nodes.get(b.node);
        if (!n) continue;
        const V = b.values;
        if (b.param_name === 'deform') {
          const a = V[x0][y0], c = V[x1][y0], d = V[x0][y1], e = V[x1][y1];
          if (!a?.length) continue;
          if (!n.deform) n.deform = new Float32Array(a.length * 2);
          for (let i = 0; i < a.length; i++) {
            n.deform[2 * i] += w00 * a[i][0] + w10 * c[i][0] + w01 * d[i][0] + w11 * e[i][0];
            n.deform[2 * i + 1] += w00 * a[i][1] + w10 * c[i][1] + w01 * d[i][1] + w11 * e[i][1];
          }
          continue;
        }
        const v = w00 * V[x0][y0] + w10 * V[x1][y0] + w01 * V[x0][y1] + w11 * V[x1][y1];
        const o = n.off;
        switch (b.param_name) {
          case 'transform.t.x': o.t[0] += v; break;
          case 'transform.t.y': o.t[1] += v; break;
          case 'transform.t.z': o.t[2] += v; break;
          case 'transform.r.x': o.r[0] += v; break;
          case 'transform.r.y': o.r[1] += v; break;
          case 'transform.r.z': o.r[2] += v; break;
          case 'transform.s.x': o.s[0] *= v; break;
          case 'transform.s.y': o.s[1] *= v; break;
          case 'zSort': o.z += v; break;
          case 'opacity': o.op *= v; break;
        }
      }
    }
    const rec = (n, M, z, on, grp) => {
      const t = n.transform, o = n.off;
      n.world = mul(M, trs([t.trans[0] + o.t[0], t.trans[1] + o.t[1], (t.trans[2] || 0) + o.t[2]],
        [t.rot[0] + o.r[0], t.rot[1] + o.r[1], t.rot[2] + o.r[2]], [t.scale[0] * o.s[0], t.scale[1] * o.s[1]]));
      n.grp = grp;
      if (grp && grp.translate_children && n.type !== 'Part' && n.type !== 'MeshGroup') {
        const [wx, wy] = ap(n.world, 0, 0), Gi = inv2(grp.world);
        const [cx, cy] = ap2(Gi, wx, wy), [qx, qy] = this.warp(grp, cx, cy);
        const [nx, ny] = ap(grp.world, qx, qy);
        n.world[12] = nx; n.world[13] = ny;
      }
      n.z = z + (n.zsort || 0) + o.z;
      n.alpha = (n.opacity ?? 1) * o.op;
      n.on = on && n.enabled !== false;
      const kidGrp = n.type === 'MeshGroup' && n.tris.length ? n : grp;
      for (const k of n.kids) rec(k, n.world, n.z, n.on, kidGrp);
    };
    rec(this.root, Float64Array.of(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), 0, true, null);
    for (const n of this.parts) this.positions(n);
  }

  positions(n) {                                 // world-space vertices of one part
    const v = n.mesh.verts, d = n.deform, W = n.world, g = n.grp, nv = v.length / 2;
    if (!n.pos || n.pos.length !== v.length) n.pos = new Float32Array(v.length);
    const P = n.pos;
    const Gi = g ? inv2(g.world) : null, G = g?.world;
    const C = g ? [Gi[0] * W[0] + Gi[2] * W[1], Gi[1] * W[0] + Gi[3] * W[1], Gi[0] * W[4] + Gi[2] * W[5],
      Gi[1] * W[4] + Gi[3] * W[5], Gi[0] * W[12] + Gi[2] * W[13] + Gi[4], Gi[1] * W[12] + Gi[3] * W[13] + Gi[5]] : null;
    for (let i = 0; i < nv; i++) {
      const lx = v[2 * i] + (d ? d[2 * i] : 0), ly = v[2 * i + 1] + (d ? d[2 * i + 1] : 0);
      let x = W[0] * lx + W[4] * ly + W[12], y = W[1] * lx + W[5] * ly + W[13];
      if (g) {
        const sx = g.dynamic_deformation ? lx : v[2 * i], sy = g.dynamic_deformation ? ly : v[2 * i + 1];
        const cx = C[0] * sx + C[2] * sy + C[4], cy = C[1] * sx + C[3] * sy + C[5];
        const [qx, qy] = this.warp(g, cx, cy), dx = qx - cx, dy = qy - cy;
        x += G[0] * dx + G[4] * dy; y += G[1] * dx + G[5] * dy;
      }
      P[2 * i] = x; P[2 * i + 1] = y;
    }
  }

  // ---- SimplePhysics (inochi2d phys/pendulum.d, springpendulum.d) ------------------------
  stepPhysics(dt) {
    dt = Math.min(dt, 0.1);
    const steps = Math.max(1, Math.ceil(dt / (1 / 240))), h = dt / steps;
    for (const s of this.physics) {
      const n = s.node;
      if (!n.on) continue;
      const g = (n.gravity ?? 1) * this.world.g * this.world.ppm, L = Math.max(1, n.length ?? 100);
      const [ax, ay] = ap(n.world, 0, 0);
      if (!s.bob) s.bob = [ax, ay + L];
      if (n.model_type === 'Pendulum') {
        s.ang = Math.atan2(-(s.bob[0] - ax), s.bob[1] - ay);
        const lr = g / L, crit = 2 * Math.sqrt(lr);
        for (let i = 0; i < steps; i++) {
          s.dAng += h * (-lr * Math.sin(s.ang) - s.dAng * (n.angle_damping ?? 0.5) * crit);
          s.ang += h * s.dAng;
        }
        s.bob = [ax - Math.sin(s.ang) * L, ay + Math.cos(s.ang) * L];
      } else {
        const ks = (n.frequency ?? 1) * 2 * Math.PI, k = ks * ks, rest = L - g / k;
        const critA = 2 * Math.sqrt(g / L), critL = 2 * ks;
        for (let i = 0; i < steps; i++) {
          const ox = s.bob[0] - ax, oy = s.bob[1] - ay, dist = Math.hypot(ox, oy) || 1e-6, nx = ox / dist, ny = oy / dist;
          const vr = s.v[0] * nx + s.v[1] * ny, tx = s.v[0] - vr * nx, ty = s.v[1] - vr * ny;
          const f = (dist - rest) * k;
          const fx = -nx * f - tx * (n.angle_damping ?? 0.5) * critA - nx * vr * (n.length_damping ?? 0.5) * critL;
          const fy = g - ny * f - ty * (n.angle_damping ?? 0.5) * critA - ny * vr * (n.length_damping ?? 0.5) * critL;
          s.v[0] += h * fx; s.v[1] += h * fy;
          s.bob[0] += h * s.v[0]; s.bob[1] += h * s.v[1];
        }
      }
      // physics output back into the node's local frame
      const I = inv2(n.world), [lx, ly] = ap2(I, s.bob[0], s.bob[1]);
      const len = Math.hypot(lx, ly) || 1e-6, rel = Math.hypot(s.bob[0] - ax, s.bob[1] - ay) / L;
      const os = n.output_scale || [1, 1];
      let out;
      if (n.map_mode === 'AngleLength') out = [Math.atan2(-lx / len, ly / len) / Math.PI, rel];
      else out = [(lx / len) * rel, -((ly / len) * rel - 1)];
      const p = s.param;
      p.value = [Math.min(p.max[0], Math.max(p.min[0], out[0] * os[0])), Math.min(p.max[1], Math.max(p.min[1], out[1] * os[1]))];
    }
  }

  bounds() {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const n of this.parts) {
      if (!n.on || n.alpha <= 0) continue;
      for (let i = 0; i < n.pos.length; i += 2) {
        x0 = Math.min(x0, n.pos[i]); x1 = Math.max(x1, n.pos[i]);
        y0 = Math.min(y0, n.pos[i + 1]); y1 = Math.max(y1, n.pos[i + 1]);
      }
    }
    return { x0, y0, x1, y1 };
  }
}

// ---- WebGL2 renderer -----------------------------------------------------------------------------
export class Renderer {
  constructor(canvas) {
    const gl = (this.gl = canvas.getContext('webgl2', { premultipliedAlpha: true, alpha: true, antialias: true, stencil: true, preserveDrawingBuffer: true }));
    if (!gl) throw new Error('WebGL2 not available');
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const prog = (vs, fs) => { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs));
      gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p; };
    this.part = prog(`#version 300 es
      layout(location=0) in vec2 aPos; layout(location=1) in vec2 aUV; uniform vec4 uView; out vec2 vUV;
      void main(){ vUV=aUV; gl_Position=vec4(aPos.x*uView.x+uView.z, -(aPos.y*uView.y+uView.w), 0., 1.); }`, `#version 300 es
      precision mediump float; in vec2 vUV; uniform sampler2D uTex; uniform float uOpacity, uThr, uHueMin; uniform vec4 uHue, uSkin;
      uniform vec3 uTint, uScreen; out vec4 o;
      void main(){ vec4 t = texture(uTex, vUV);
        // Creator meshes reach past the texture; inochi2d clamps to a transparent border, WebGL has no
        // CLAMP_TO_BORDER, so edge texels would smear into bars
        if (any(lessThan(vUV, vec2(0.))) || any(greaterThan(vUV, vec2(1.)))) t = vec4(0.);
        if (t.a <= uThr) discard;                                   // mask pass
        float sk = 0.;
        if (uSkin.y != 1. && t.a > 0.) {                            // n.skin (luma gain, chroma gain, cos, sin): only skin texels (YIQ angle ~12 deg, mid chroma, not dark)
          vec3 u = t.rgb / t.a; float Y = dot(u, vec3(.299, .587, .114)); vec2 c = vec2(dot(u, vec3(.596, -.274, -.322)), dot(u, vec3(.211, -.523, .312)));
          float l = length(c), k = l < .015 ? 0. : smoothstep(.72, .9, dot(c, vec2(.978, .208)) / l) * smoothstep(.035, .052, l) * (1. - smoothstep(.2, .27, l)) * smoothstep(.5, .62, Y);
          vec2 r = vec2(c.x * uSkin.z - c.y * uSkin.w, c.x * uSkin.w + c.y * uSkin.z) * uSkin.y; Y *= mix(1., uSkin.x, k); c = mix(c, r, k); sk = k;
          t.rgb = clamp(vec3(Y + .956 * c.x + .621 * c.y, Y - .272 * c.x - .647 * c.y, Y - 1.106 * c.x + 1.703 * c.y), 0., 1.) * t.a; }
        if (uHue.y != 0. && t.a > 0.) {                             // n.hue (cos, sin, luma gain, chroma gain): only purple texels (YIQ angle ~95 deg) change
          vec3 u = t.rgb / t.a; float Y = dot(u, vec3(.299, .587, .114)); vec2 c = vec2(dot(u, vec3(.596, -.274, -.322)), dot(u, vec3(.211, -.523, .312)));
          float l = length(c), w = l < .005 ? 0. : smoothstep(.55, .8, dot(c, vec2(-.087, .996)) / l);
          if (uHueMin > 0.) w *= smoothstep(uHueMin, uHueMin * 2., l);   // n.hueMin: pale tints (lavender shading on white cloth) stay
          else if (uHueMin < -2.5) w = 1. - smoothstep(.3, .42, Y);     // -3: dark cloth of any hue, bright trim stays
          else if (uHueMin < -1.5) w = 1.;                              // -2: the whole layer
          else if (uHueMin < 0.) w = max(w, 1. - smoothstep(.02, .05, l));   // negative: white cloth changes too
          w *= 1. - sk;                                              // texels n.skin already changed stay skin
          vec2 r = vec2(c.x * uHue.x - c.y * uHue.y, c.x * uHue.y + c.y * uHue.x) * uHue.w; Y *= mix(1., uHue.z, w); c = mix(c, r, w);
          t.rgb = clamp(vec3(Y + .956 * c.x + .621 * c.y, Y - .272 * c.x - .647 * c.y, Y - 1.106 * c.x + 1.703 * c.y), 0., 1.) * t.a; }
        vec3 s = vec3(1.) - (vec3(1.) - t.rgb) * (vec3(1.) - uScreen * t.a);
        o = vec4(s, t.a) * vec4(uTint, 1.) * uOpacity; }`);
    this.quad = prog(`#version 300 es
      layout(location=0) in vec2 aPos; out vec2 vUV; void main(){ vUV=aPos*.5+.5; gl_Position=vec4(aPos,0.,1.); }`, `#version 300 es
      precision mediump float; in vec2 vUV; uniform sampler2D uTex; uniform float uOpacity; uniform vec3 uTint, uScreen; out vec4 o;
      void main(){ vec4 t = texture(uTex, vUV);
        vec3 s = vec3(1.) - (vec3(1.) - t.rgb) * (vec3(1.) - uScreen * t.a);
        o = vec4(s, t.a) * vec4(uTint, 1.) * uOpacity; }`);
    const U = (p, ...names) => Object.fromEntries(names.map((n) => [n, gl.getUniformLocation(p, n)]));
    this.u = U(this.part, 'uView', 'uTex', 'uOpacity', 'uThr', 'uTint', 'uScreen', 'uHue', 'uHueMin', 'uSkin');
    this.uq = U(this.quad, 'uTex', 'uOpacity', 'uTint', 'uScreen');
    this.quadVao = gl.createVertexArray(); gl.bindVertexArray(this.quadVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, Float32Array.of(-1, -1, 1, -1, -1, 1, 1, 1), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    this.fb = null;
  }

  attach(puppet) {
    const gl = this.gl;
    this.detach();
    this.puppet = puppet;
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    this.tex = puppet.textures.map((bmp) => {
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bmp);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return t;
    });
    this.vao = new Map();
    for (const n of puppet.parts) {
      const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
      const pos = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, pos);
      gl.bufferData(gl.ARRAY_BUFFER, n.pos.byteLength, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(n.mesh.uvs), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(n.mesh.indices), gl.STATIC_DRAW);
      this.vao.set(n, { vao, pos, count: n.mesh.indices.length });
    }
    gl.bindVertexArray(null);
  }

  detach() {
    const gl = this.gl;
    for (const t of this.tex || []) gl.deleteTexture(t);
    this.tex = []; this.vao = new Map();
  }

  ensureFB(w, h) {
    const gl = this.gl;
    if (this.fb && this.fbW === w && this.fbH === h) return;
    if (this.fb) { gl.deleteFramebuffer(this.fb); gl.deleteTexture(this.fbTex); gl.deleteRenderbuffer(this.fbDS); }
    this.fbW = w; this.fbH = h;
    this.fbTex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, this.fbTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    this.fbDS = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, this.fbDS);
    gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH24_STENCIL8, w, h);
    this.fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.fbTex, 0);
    gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_STENCIL_ATTACHMENT, gl.RENDERBUFFER, this.fbDS);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  blend(mode) {
    const gl = this.gl;
    gl.blendEquation(gl.FUNC_ADD);
    switch (mode) {
      case 'Multiply': gl.blendFuncSeparate(gl.DST_COLOR, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE); break;
      case 'LinearDodge': case 'Additive': gl.blendFuncSeparate(gl.ONE, gl.ONE, gl.ZERO, gl.ONE); break;
      case 'Screen': gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_COLOR, gl.ZERO, gl.ONE); break;
      case 'ClipToLower': gl.blendFuncSeparate(gl.DST_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE); break;
      default: gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    }
  }

  geom(n, thr, opacity) {                        // one part's mesh with the part program
    const gl = this.gl, b = this.vao.get(n), ti = n.textures?.[0];
    if (!b || ti === undefined || ti === NONE || !this.tex[ti]) return;
    gl.bindVertexArray(b.vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, b.pos); gl.bufferSubData(gl.ARRAY_BUFFER, 0, n.pos);
    gl.bindTexture(gl.TEXTURE_2D, this.tex[ti]);
    gl.uniform1f(this.u.uThr, thr); gl.uniform1f(this.u.uOpacity, opacity);
    gl.uniform3fv(this.u.uTint, n.tint || [1, 1, 1]); gl.uniform3fv(this.u.uScreen, n.screenTint || [0, 0, 0]); gl.uniform4fv(this.u.uHue, n.hue || [1, 0, 1, 1]); gl.uniform1f(this.u.uHueMin, n.hueMin || 0); gl.uniform4fv(this.u.uSkin, n.skin || [1, 1, 1, 0]);
    gl.drawElements(gl.TRIANGLES, b.count, gl.UNSIGNED_SHORT, 0);
  }

  withMasks(n, drawSelf) {
    const gl = this.gl;
    if (!n.maskSrc?.length) return drawSelf();
    gl.useProgram(this.part);
    gl.enable(gl.STENCIL_TEST);
    gl.clearStencil(n.maskSrc.some((m) => !m.dodge) ? 0 : 1); gl.stencilMask(0xff); gl.clear(gl.STENCIL_BUFFER_BIT);
    gl.colorMask(false, false, false, false);
    gl.stencilOp(gl.KEEP, gl.KEEP, gl.REPLACE);
    for (const m of n.maskSrc) {
      gl.stencilFunc(gl.ALWAYS, m.dodge ? 0 : 1, 0xff);
      const thr = m.src.mask_threshold ?? 0.5;
      for (const p of m.src.type === 'Composite' ? m.src.sub : [m.src]) if (p.mesh) this.geom(p, thr, 1);
    }
    gl.colorMask(true, true, true, true);
    gl.stencilFunc(gl.EQUAL, 1, 0xff); gl.stencilMask(0x00);
    drawSelf();
    gl.stencilMask(0xff); gl.disable(gl.STENCIL_TEST);
  }

  drawPart(n) {
    if (!n.on || n.alpha <= 0 || n.hide) return;             // n.hide: the page's layer panel (隱藏／單看)
    this.withMasks(n, () => { this.gl.useProgram(this.part); this.blend(n.blend_mode); this.geom(n, -1, n.alpha); });
  }

  draw(view) {            // view: {cx, cy, scale}: camera centre in puppet px and px-per-unit
    const gl = this.gl, c = gl.canvas, p = this.puppet;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, c.width, c.height);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.STENCIL_BUFFER_BIT);
    if (!p) return;
    gl.enable(gl.BLEND); gl.activeTexture(gl.TEXTURE0);
    const sx = (2 * view.scale) / c.width, sy = (2 * view.scale) / c.height;
    gl.useProgram(this.part);
    gl.uniform4f(this.u.uView, sx, sy, -view.cx * sx, -view.cy * sy); gl.uniform1i(this.u.uTex, 0);
    const back = (a, b) => b.z - a.z;
    for (const n of [...p.drawList].sort(back)) {
      if (n.type !== 'Composite') { this.drawPart(n); continue; }
      if (!n.on || n.alpha <= 0 || !n.sub.length) continue;
      this.ensureFB(c.width, c.height);
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.STENCIL_BUFFER_BIT);
      for (const s of [...n.sub].sort(back)) this.drawPart(s);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      this.withMasks(n, () => {
        gl.useProgram(this.quad); this.blend(n.blend_mode);
        gl.bindVertexArray(this.quadVao); gl.bindTexture(gl.TEXTURE_2D, this.fbTex);
        gl.uniform1i(this.uq.uTex, 0); gl.uniform1f(this.uq.uOpacity, n.alpha);
        gl.uniform3fv(this.uq.uTint, n.tint || [1, 1, 1]); gl.uniform3fv(this.uq.uScreen, n.screenTint || [0, 0, 0]);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      });
      gl.useProgram(this.part);
    }
    gl.bindVertexArray(null);
  }
}
