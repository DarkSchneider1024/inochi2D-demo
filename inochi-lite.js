// inochi-lite.js — a small WebGL player for Inochi2D puppets (.inp / .inx, INP 0.8 "TRNSRTS" container).
//
// Implements the subset of the Inochi2D 0.8 runtime that this puppet uses, following the reference
// implementation (inochi2d v0.8.7, D) and inox2d (Rust):
//   * container: "TRNSRTS\0", u32 BE json length, JSON, "TEX_SECT", u32 BE count, (u32 BE len, u8 enc, PNG)*
//   * node transforms: world = parent * T(trans + t_off) * Rz(rot + r_off) * S(scale * s_off)
//   * parameters: value -> normalised 0..1 (clamped), axis points normalised, bilinear interpolation
//     between the neighbouring set keyframes; "transform.t.*"/"transform.r.*" add, "transform.s.*"
//     multiply, "deform" adds per-vertex offsets
//   * drawing: every Part, back to front by DESCENDING accumulated zsort, "Normal" blending,
//     premultiplied alpha
//   * SimplePhysics: approximated by a damped pendulum driven by the head motion (see stepPhysics)
// Not implemented (unused by this puppet): masks, composites, mesh groups, other blend modes, animations.

export async function loadINP(url) {
  const buf = new Uint8Array(await (await fetch(url)).arrayBuffer());
  const dv = new DataView(buf.buffer);
  const tag = (o) => String.fromCharCode(...buf.slice(o, o + 8));
  if (tag(0) !== 'TRNSRTS\0') throw new Error('not an Inochi2D INP file');
  let o = 8;
  const jlen = dv.getUint32(o); o += 4;                       // big endian
  const json = JSON.parse(new TextDecoder('utf-8').decode(buf.slice(o, o + jlen))); o += jlen;
  if (tag(o) !== 'TEX_SECT') throw new Error('missing TEX_SECT'); o += 8;
  const count = dv.getUint32(o); o += 4;
  const textures = [];
  for (let i = 0; i < count; i++) {
    const len = dv.getUint32(o); const enc = buf[o + 4]; o += 5;
    const blob = new Blob([buf.slice(o, o + len)], { type: enc === 1 ? 'image/x-tga' : 'image/png' }); o += len;
    textures.push(await createImageBitmap(blob, { premultiplyAlpha: 'none' }));
  }
  return { json, textures, bytes: buf.length };
}

export class Puppet {
  constructor({ json, textures }) {
    this.json = json;
    this.textures = textures;
    this.nodes = new Map();
    this.parts = [];
    const walk = (n, parent) => {
      const node = { ...n, parent, off: null, deform: null };
      this.nodes.set(n.uuid, node);
      if (n.type === 'Part') this.parts.push(node);
      node.kids = (n.children || []).map((c) => walk(c, node));
      return node;
    };
    this.root = walk(json.nodes, null);
    this.params = json.param.map((p) => ({ ...p, value: [...p.defaults] }));
    this.byName = Object.fromEntries(this.params.map((p) => [p.name, p]));
    this.physics = [...this.nodes.values()].filter((n) => n.type === 'SimplePhysics')
      .map((n) => ({ node: n, param: this.params.find((p) => p.uuid === n.param), angle: 0, vel: 0 }));
  }

  set(name, x, y = 0) {
    const p = this.byName[name];
    if (p) p.value = [x, y];
  }

  // ---- parameter evaluation -------------------------------------------------------------
  static axisCell(points, t) {            // -> [i0, i1, w] with t between points[i0] and points[i1]
    if (points.length === 1) return [0, 0, 0];
    for (let i = 0; i < points.length - 1; i++) {
      if (t <= points[i + 1] || i === points.length - 2) {
        const span = points[i + 1] - points[i];
        return [i, i + 1, span > 0 ? Math.min(1, Math.max(0, (t - points[i]) / span)) : 0];
      }
    }
  }

  update() {
    for (const n of this.nodes.values()) {
      n.off = { tx: 0, ty: 0, rz: 0, sx: 1, sy: 1, z: 0 };
      n.deform = null;
    }
    for (const p of this.params) {
      const nx = (p.value[0] - p.min[0]) / (p.max[0] - p.min[0]);
      const ny = p.is_vec2 ? (p.value[1] - p.min[1]) / (p.max[1] - p.min[1]) : 0;
      const [x0, x1, wx] = Puppet.axisCell(p.axis_points[0], Math.min(1, Math.max(0, nx)));
      const [y0, y1, wy] = Puppet.axisCell(p.axis_points[1], Math.min(1, Math.max(0, ny)));
      const w00 = (1 - wx) * (1 - wy), w10 = wx * (1 - wy), w01 = (1 - wx) * wy, w11 = wx * wy;
      for (const b of p.bindings) {
        const n = this.nodes.get(b.node);
        const V = b.values;
        if (b.param_name === 'deform') {
          const a = V[x0][y0], c = V[x1][y0], d = V[x0][y1], e = V[x1][y1];
          if (!n.deform) n.deform = new Float32Array(a.length * 2);
          for (let i = 0; i < a.length; i++) {
            n.deform[2 * i] += w00 * a[i][0] + w10 * c[i][0] + w01 * d[i][0] + w11 * e[i][0];
            n.deform[2 * i + 1] += w00 * a[i][1] + w10 * c[i][1] + w01 * d[i][1] + w11 * e[i][1];
          }
          continue;
        }
        const v = w00 * V[x0][y0] + w10 * V[x1][y0] + w01 * V[x0][y1] + w11 * V[x1][y1];
        switch (b.param_name) {
          case 'transform.t.x': n.off.tx += v; break;
          case 'transform.t.y': n.off.ty += v; break;
          case 'transform.r.z': n.off.rz += v; break;
          case 'transform.s.x': n.off.sx *= v; break;
          case 'transform.s.y': n.off.sy *= v; break;
          case 'zSort': n.off.z += v; break;
        }
      }
    }
    // world matrices (column vectors: [a c e; b d f])
    const mul = (A, B) => [A[0] * B[0] + A[2] * B[1], A[1] * B[0] + A[3] * B[1], A[0] * B[2] + A[2] * B[3],
      A[1] * B[2] + A[3] * B[3], A[0] * B[4] + A[2] * B[5] + A[4], A[1] * B[4] + A[3] * B[5] + A[5]];
    const rec = (n, M, z) => {
      const t = n.transform, o = n.off;
      const r = t.rot[2] + o.rz, sx = t.scale[0] * o.sx, sy = t.scale[1] * o.sy;
      const c = Math.cos(r), s = Math.sin(r);
      n.world = mul(M, [c * sx, s * sx, -s * sy, c * sy, t.trans[0] + o.tx, t.trans[1] + o.ty]);
      n.z = z + n.zsort + o.z;
      for (const k of n.kids) rec(k, n.world, n.z);
    };
    rec(this.root, [1, 0, 0, 1, 0, 0], 0);
  }

  // ---- physics: damped pendulum standing in for Inochi2D's SimplePhysics -----------------
  stepPhysics(dt, drive) {
    for (const ph of this.physics) {
      const k = 38, damp = 5.5;                                  // stiffness / damping
      const acc = -k * (ph.angle - drive) - damp * ph.vel;
      ph.vel += acc * dt;
      ph.angle += ph.vel * dt;
      const v = Math.max(-1, Math.min(1, ph.angle));
      ph.param.value = [v, 0];
    }
  }
}

// ---- WebGL renderer ---------------------------------------------------------------------------
export class Renderer {
  constructor(canvas) {
    const gl = (this.gl = canvas.getContext('webgl2', { premultipliedAlpha: true, alpha: true, antialias: true }));
    if (!gl) throw new Error('WebGL2 not available');
    const vs = `#version 300 es
      in vec2 aPos; in vec2 aUV; uniform vec4 uView; out vec2 vUV;
      void main(){ vUV=aUV; gl_Position=vec4((aPos.x*uView.x+uView.z), -(aPos.y*uView.y+uView.w), 0., 1.); }`;
    const fs = `#version 300 es
      precision mediump float; in vec2 vUV; uniform sampler2D uTex; uniform float uOpacity; out vec4 o;
      void main(){ o = texture(uTex, vUV) * uOpacity; }   // textures are uploaded premultiplied`;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const pr = (this.prog = gl.createProgram());
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr);
    this.loc = { pos: gl.getAttribLocation(pr, 'aPos'), uv: gl.getAttribLocation(pr, 'aUV'),
      view: gl.getUniformLocation(pr, 'uView'), op: gl.getUniformLocation(pr, 'uOpacity') };
    this.posBuf = gl.createBuffer(); this.uvBuf = gl.createBuffer(); this.idxBuf = gl.createBuffer();
  }

  attach(puppet) {
    const gl = this.gl;
    this.puppet = puppet;
    // Premultiply on the CPU before upload so linear/mip filtering happens in premultiplied space.
    // (Filtering straight-alpha textures mixes the black of transparent texels into the edges and
    //  draws a faint dark outline around every part.)
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
    const cv = document.createElement('canvas'), cx = cv.getContext('2d', { willReadFrequently: true });
    this.tex = puppet.textures.map((bmp) => {
      cv.width = bmp.width; cv.height = bmp.height;
      cx.clearRect(0, 0, bmp.width, bmp.height); cx.drawImage(bmp, 0, 0);
      const px = cx.getImageData(0, 0, bmp.width, bmp.height).data;
      for (let i = 0; i < px.length; i += 4) {
        const a = px[i + 3] / 255;
        px[i] = Math.round(px[i] * a); px[i + 1] = Math.round(px[i + 1] * a); px[i + 2] = Math.round(px[i + 2] * a);
      }
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, bmp.width, bmp.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(px.buffer));
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return t;
    });
  }

  draw(view) {            // view: {cx, cy, scale} in puppet px (camera centre and px-per-unit)
    const gl = this.gl, c = gl.canvas, p = this.puppet;
    gl.viewport(0, 0, c.width, c.height);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(this.prog);
    const sx = (2 * view.scale) / c.width, sy = (2 * view.scale) / c.height;
    gl.uniform4f(this.loc.view, sx, sy, -view.cx * sx, -view.cy * sy);
    const order = [...p.parts].filter((n) => n.enabled).sort((a, b) => b.z - a.z);   // back to front
    for (const n of order) {
      const m = n.mesh, M = n.world, nv = m.verts.length / 2;
      const pos = new Float32Array(nv * 2);
      for (let i = 0; i < nv; i++) {
        let x = m.verts[2 * i], y = m.verts[2 * i + 1];
        if (n.deform) { x += n.deform[2 * i]; y += n.deform[2 * i + 1]; }
        pos[2 * i] = M[0] * x + M[2] * y + M[4];
        pos[2 * i + 1] = M[1] * x + M[3] * y + M[5];
      }
      gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuf); gl.bufferData(gl.ARRAY_BUFFER, pos, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(this.loc.pos); gl.vertexAttribPointer(this.loc.pos, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.uvBuf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(m.uvs), gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(this.loc.uv); gl.vertexAttribPointer(this.loc.uv, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.idxBuf);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(m.indices), gl.DYNAMIC_DRAW);
      gl.bindTexture(gl.TEXTURE_2D, this.tex[n.textures[0]]);
      gl.uniform1f(this.loc.op, n.opacity ?? 1);
      gl.drawElements(gl.TRIANGLES, m.indices.length, gl.UNSIGNED_SHORT, 0);
    }
  }
}
