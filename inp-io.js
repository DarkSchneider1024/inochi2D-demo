// inp-io.js -- read and write Inochi2D .inp/.inx files for the layer editor (2026-11-01, user: 手動修改圖層).
// Container: "TRNSRTS\0", u32 BE json length, JSON, "TEX_SECT", u32 BE count, (u32 BE len, u8 enc, bytes)*, then any
// EXT_SECT bytes, kept as they are. Textures nobody edited keep their original PNG bytes. Edited ones go through our
// own PNG codec, not a canvas: a canvas drops the colour under transparent pixels, and that shows as fringes on a mesh.
const enc = new TextEncoder();

export function parseINP(buf) {
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const tag = (o) => String.fromCharCode(...buf.subarray(o, o + 8));
  if (tag(0) !== 'TRNSRTS\0') throw new Error('這不是 Inochi2D 模型檔');
  const jlen = dv.getUint32(8);
  const json = JSON.parse(new TextDecoder('utf-8').decode(buf.subarray(12, 12 + jlen)));
  let o = 12 + jlen;
  if (tag(o) !== 'TEX_SECT') throw new Error('模型檔缺少貼圖區段');
  const count = dv.getUint32(o + 8); o += 12;
  const textures = [];
  for (let i = 0; i < count; i++) {
    const len = dv.getUint32(o);
    textures.push({ enc: buf[o + 4], bytes: buf.subarray(o + 5, o + 5 + len) });
    o += 5 + len;
  }
  return { json, textures, tail: buf.subarray(o) };
}

export function buildINP(json, textures, tail) {
  const js = enc.encode(JSON.stringify(json));
  const size = 12 + js.length + 12 + textures.reduce((s, t) => s + 5 + t.bytes.length, 0) + (tail ? tail.length : 0);
  const out = new Uint8Array(size), dv = new DataView(out.buffer);
  out.set(enc.encode('TRNSRTS\0'), 0); dv.setUint32(8, js.length); out.set(js, 12);
  let o = 12 + js.length;
  out.set(enc.encode('TEX_SECT'), o); dv.setUint32(o + 8, textures.length); o += 12;
  for (const t of textures) {
    dv.setUint32(o, t.bytes.length); out[o + 4] = t.enc; out.set(t.bytes, o + 5);
    o += 5 + t.bytes.length;
  }
  if (tail) out.set(tail, o);
  return out;
}

async function pipe(blob, stream) {
  return new Uint8Array(await new Response(blob.stream().pipeThrough(stream)).arrayBuffer());
}

const paeth = (a, b, c) => {
  const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
};

// 8-bit RGBA, not interlaced (every texture we build). Returns null for anything else: the caller decodes via a canvas.
export async function decodePNG(png) {
  const dv = new DataView(png.buffer, png.byteOffset, png.byteLength);
  const w = dv.getUint32(16), h = dv.getUint32(20);
  if (png[24] !== 8 || png[25] !== 6 || png[28] !== 0) return null;
  const idat = [];
  for (let o = 8; o < png.length;) {
    const len = dv.getUint32(o), t = String.fromCharCode(...png.subarray(o + 4, o + 8));
    if (t === 'IDAT') idat.push(png.subarray(o + 8, o + 8 + len));
    o += 12 + len;
  }
  const raw = await pipe(new Blob(idat), new DecompressionStream('deflate'));
  const st = w * 4, rgba = new Uint8ClampedArray(st * h);
  for (let y = 0, i = 0; y < h; y++) {
    const f = raw[i++], row = y * st;
    for (let x = 0; x < st; x++) {
      const a = x >= 4 ? rgba[row + x - 4] : 0, b = y ? rgba[row + x - st] : 0, c = x >= 4 && y ? rgba[row + x - st - 4] : 0;
      const pred = f === 0 ? 0 : f === 1 ? a : f === 2 ? b : f === 3 ? (a + b) >> 1 : paeth(a, b, c);
      rgba[row + x] = (raw[i++] + pred) & 255;
    }
  }
  return { w, h, rgba };
}

const CRC = new Int32Array(256).map((_, n) => { for (let k = 0; k < 8; k++) n = n & 1 ? 0xedb88320 ^ (n >>> 1) : n >>> 1; return n; });
const crc32 = (b) => { let c = -1; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };

export async function encodePNG(w, h, rgba) {
  const st = w * 4, raw = new Uint8Array((st + 1) * h);
  const cand = [0, 1, 2, 3, 4].map(() => new Uint8Array(st));
  for (let y = 0; y < h; y++) {
    const row = y * st;
    let best = 0, bestSum = Infinity;
    for (let f = 0; f < 5; f++) {
      const l = cand[f];
      let sum = 0;
      for (let x = 0; x < st; x++) {
        const a = x >= 4 ? rgba[row + x - 4] : 0, b = y ? rgba[row + x - st] : 0, c = x >= 4 && y ? rgba[row + x - st - 4] : 0;
        const pred = f === 0 ? 0 : f === 1 ? a : f === 2 ? b : f === 3 ? (a + b) >> 1 : paeth(a, b, c);
        const v = (rgba[row + x] - pred) & 255;
        l[x] = v; sum += v < 128 ? v : 256 - v;
      }
      if (sum < bestSum) { bestSum = sum; best = f; }
    }
    raw[y * (st + 1)] = best;
    raw.set(cand[best], y * (st + 1) + 1);
  }
  const z = await pipe(new Blob([raw]), new CompressionStream('deflate'));
  const ihdr = new Uint8Array(13), dv = new DataView(ihdr.buffer);
  dv.setUint32(0, w); dv.setUint32(4, h); ihdr[8] = 8; ihdr[9] = 6;
  const chunks = [['IHDR', ihdr], ['IDAT', z], ['IEND', new Uint8Array(0)]];
  const out = new Uint8Array(8 + chunks.reduce((s, c) => s + 12 + c[1].length, 0)), odv = new DataView(out.buffer);
  out.set([137, 80, 78, 71, 13, 10, 26, 10], 0);
  let o = 8;
  for (const [t, d] of chunks) {
    odv.setUint32(o, d.length); out.set(enc.encode(t), o + 4); out.set(d, o + 8);
    odv.setUint32(o + 8 + d.length, crc32(out.subarray(o + 4, o + 8 + d.length)));
    o += 12 + d.length;
  }
  return out;
}
