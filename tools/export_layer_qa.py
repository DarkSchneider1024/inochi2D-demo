# -*- coding: utf-8 -*-
"""拆圖整合圖 + 單圖層疑點檢查 (2026-10-25, user: 輸出拆圖整合圖放到 demo 網頁，讓我直接作圖層確認，並實作單圖層疑點檢查).

Reads a built puppet (inochi2D-demo/models/<id>.inp), puts every Part at its REST place (the node chain's
translations + its mesh box; the texture spans the mesh, uv 0..1), and writes for the demo page layers.html:
    inochi2D-demo/layers/<id>/index.json      canvas size, every layer (back -> front): box, depth, hidden-at-rest,
                                              group, and its 疑點 (suspect boxes)
    inochi2D-demo/layers/<id>/<n>.webp         the layer's own pixels (RGBA, its box only)
    inochi2D-demo/layers/<id>/composite.webp   the rest pose of the layers

疑點 per layer (what moves in the rig and was missed by the rest-pose 99 % check):
    碎塊    a piece apart from the layer's body (it floats when the layer moves)
    藏線    dark line work this layer holds UNDER the layers above it at rest -- the classic ghost line that shows as
            soon as the upper layer (a lock, the glasses, the face) moves
    破洞    see-through pixels inside the layer's own body (what is under shows through)
    灰邊    rim pixels still carrying the flat #808080 background of the source drawing
Expression / pose layers (hidden at rest: their opacity at the parameters' defaults is ~0) are listed and checked on
their own, never as covering anything.

    python src/inochi2d/export_layer_qa.py mr_carrot_v3 mr_carrot_gold_mage carol_v2 bobo
"""
import io, json, math, os, struct, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.abspath(os.path.join(HERE, '..'))

MULTI = ('眼鏡', '閉眼', '眼線', '眉', '嘴', '眼白', '眼球')   # drawn in several strokes on purpose
PRIVATE_IDS = {'blue_senpai', 'fox_yuzuno', 'nikke_tia', 'carrot_bikini', 'carrot_bunny', 'carrot_bunny_v2'}
NAMES = {'blue_senpai': '冰藍學姊', 'fox_yuzuno': '狐姬柚乃', 'nikke_tia': '蒂亞・海岸甜心', 'mr_carrot': '卡洛特先生（初版）', 'mr_carrot_v2': '卡洛特先生（V2）', 'mr_carrot_v3': '卡洛特先生', 'mr_carrot_gold_mage': '金髮魔法師卡洛特', 'carol_v3': '卡洛兒姐姐', 'carol_v2': '卡洛兒姐姐（V2）', 'bobo': '兔子波波'}


REFINED_IDS = {'mr_carrot', 'mr_carrot_v2', 'mr_carrot_v3', 'mr_carrot_gold_mage',
               'mr_carrot_v2_gold', 'gold_mage_gpt_v1', 'carol_v2', 'carol_v3', 'bobo',
               'girl_v4', 'girl_dress', 'mr_carrot_chibi'}

def category_of(mid):
    if mid in PRIVATE_IDS:
        return 'private'
    if mid in {'carol_lab', 'mr_carrot_lab', 'mr_carrot_lab_gold', 'bobo_lab'}:
        return 'lab'
    return 'refined' if mid in REFINED_IDS else 'story'


def read_inp(path):
    b = open(path, 'rb').read()
    n = struct.unpack('>I', b[8:12])[0]
    j = json.loads(b[12:12 + n].decode('utf-8'))
    o = 12 + n
    assert b[o:o + 8] == b'TEX_SECT'
    cnt = struct.unpack('>I', b[o + 8:o + 12])[0]
    o += 12
    texs = []
    for _ in range(cnt):
        L = struct.unpack('>I', b[o:o + 4])[0]
        texs.append(b[o + 5:o + 5 + L])
        o += 5 + L
    return j, texs


def rest_value(param, ax_vals, values):
    """a 1-D binding's value at the parameter's default (linear between its keys)"""
    d = param['defaults'][0]
    span = param['max'][0] - param['min'][0]
    t = (d - param['min'][0]) / span if span else 0.0
    xs = ax_vals
    vs = [v[0] if isinstance(v, list) else v for v in values]
    if t <= xs[0]:
        return vs[0]
    for i in range(len(xs) - 1):
        if xs[i] <= t <= xs[i + 1]:
            k = (t - xs[i]) / max(1e-9, xs[i + 1] - xs[i])
            return vs[i] + (vs[i + 1] - vs[i]) * k
    return vs[-1]


def layout(j):
    """every Part: world box at rest, absolute depth (back = larger), group path, rest opacity"""
    op_rest = {}
    for p in j['param']:
        for b in p['bindings']:
            if b['param_name'] == 'opacity' and not p.get('is_vec2'):
                v = rest_value(p, p['axis_points'][0], [row[0] for row in b['values']])
                op_rest[b['node']] = min(op_rest.get(b['node'], 1.0), v)
    parts = []

    def walk(nd, wx, wy, z, path):
        t = nd.get('transform', {}).get('trans', [0, 0, 0])
        wx, wy, z = wx + t[0], wy + t[1], z + nd.get('zsort', 0.0)
        if nd['type'] == 'Part':
            vs = nd['mesh']['verts']
            xs, ys = [wx + v for v in vs[0::2]], [wy + v for v in vs[1::2]]
            op = nd.get('opacity', 1.0) * op_rest.get(nd['uuid'], 1.0)
            parts.append(dict(name=nd['name'], uuid=nd['uuid'], tex=nd['textures'][0], z=z, group='/'.join(path),
                              x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys), hidden=op < 0.05))
        for c in nd.get('children', []):
            walk(c, wx, wy, z, path + ([nd['name']] if nd['type'] == 'Node' and nd['name'] != 'Root' else []))
    walk(j['nodes'], 0.0, 0.0, 0.0, [])
    parts.sort(key=lambda p: -p['z'])                      # back -> front (the builders give the back the larger zsort)
    return parts


def components(m):
    n, lab, st, _c = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    return n, lab, st


def boxes_of(m, min_area=6, pad=4, limit=12):
    """bounding boxes of the mask's clusters (merged by a small dilation), biggest first"""
    if not m.any():
        return []
    g = cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8))
    n, lab, st = components(g)
    out = []
    for i in range(1, n):
        cnt = int((m & (lab == i)).sum())
        if cnt < min_area:
            continue
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        out.append([int(x - pad), int(y - pad), int(w + 2 * pad), int(h + 2 * pad), cnt])
    out.sort(key=lambda b: -b[4])
    return out[:limit]


def export(mid):
    j, texs = read_inp(os.path.join(DEMO, 'models', f'{mid}.inp'))
    parts = layout(j)
    X0 = math.floor(min(p['x0'] for p in parts)) - 4
    Y0 = math.floor(min(p['y0'] for p in parts)) - 4
    W = math.ceil(max(p['x1'] for p in parts)) - X0 + 4
    H = math.ceil(max(p['y1'] for p in parts)) - Y0 + 4
    out_dir = os.path.join(DEMO, 'layers', mid)
    os.makedirs(out_dir, exist_ok=True)
    # Keep the previous export available until each replacement is written.
    layers = []
    for i, p in enumerate(parts):
        im = Image.open(io.BytesIO(texs[p['tex']])).convert('RGBA')
        x, y = int(round(p['x0'] - X0)), int(round(p['y0'] - Y0))
        w, h = max(1, int(round(p['x1'] - p['x0']))), max(1, int(round(p['y1'] - p['y0'])))
        if im.size != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
        a = np.zeros((H, W, 4), np.float32)
        x1, y1 = min(W, x + w), min(H, y + h)
        a[y:y1, x:x1] = np.asarray(im, np.float32)[:y1 - y, :x1 - x] / 255.0
        layers.append(dict(p, i=i, x=x, y=y, w=w, h=h, img=im, full=a))
    # the rest composite and, per pixel, how much of each layer is covered by the layers above it
    comp = np.zeros((H, W, 4), np.float32)
    live = [L for L in layers if not L['hidden']]
    for L in live:
        a = L['full'][..., 3:4]
        comp[..., :3] = comp[..., :3] * (1 - a) + L['full'][..., :3] * a
        comp[..., 3:4] = comp[..., 3:4] * (1 - a) + a
    # per layer: the composite of the layers ABOVE it (front ones), its coverage and its colour
    above = np.zeros((H, W), np.float32)
    above_rgb = np.zeros((H, W, 3), np.float32)
    for L in reversed(live):
        L['above'], L['above_rgb'] = above.copy(), above_rgb.copy()
        a = L['full'][..., 3:4]
        above_rgb = above_rgb + (1 - above[..., None]) * a * L['full'][..., :3]     # (front-to-back: the front keeps its colour)
        above = 1 - (1 - above) * (1 - L['full'][..., 3])
    comp_a = comp[..., 3]
    index = []
    for L in layers:
        # Analyze only this layer's rectangle, avoiding full-canvas work for tiny facial parts.
        ox, oy = max(0, L['x'] - 8), max(0, L['y'] - 8)
        region = np.s_[oy:min(H, L['y'] + L['h'] + 8), ox:min(W, L['x'] + L['w'] + 8)]
        F = L['full'][region]
        front = L.get('above')
        if front is not None:
            front = front[region]
        al, rgb = F[..., 3], F[..., :3] * 255
        body = al > 0.5
        lum = rgb @ np.float32([0.3, 0.59, 0.11])
        sus = []
        # 碎塊: pieces apart from the layer's main body (> 3 px gap), not tiny noise
        n, lab, st = components(al > 0.1)
        if n > 2:
            multi = any(k in L['name'] for k in MULTI)
            big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            area_big = st[big, cv2.CC_STAT_AREA]
            far = cv2.distanceTransform((lab != big).astype(np.uint8), cv2.DIST_L2, 3)
            for k in range(1, n):
                if k == big:
                    continue
                ar = st[k, cv2.CC_STAT_AREA]
                if 8 <= ar < (30 if multi else max(400, 0.02 * area_big)) and far[lab == k].min() > 3:
                    x, y, w, h = st[k, :4]
                    sus.append(dict(type='碎塊', box=[int(x - 4), int(y - 4), int(w + 8), int(h + 8)], n=int(ar)))
        # 藏線: dark line work held under the layers above (only for layers seen at rest)
        backing = (not L['hidden']) and bool(body.any()) and float((front[body] > 0.9).mean()) > 0.9
        if not L['hidden'] and not backing:      # (a backing layer, hidden on purpose -- AKA's Back Side Hair -- is skipped)
            # (only line work the layers in front ALSO draw at the same place: the original's line copied into both. A
            # hidden drawing of the layer's own -- the waistcoat under the coat -- is exactly what it should hold)
            hid = body & (front > 0.9) & (lum < 95)
            alum = (L['above_rgb'][region] * 255) @ np.float32([0.3, 0.59, 0.11]) / np.maximum(front, 1e-3)
            front_ink = cv2.dilate(((alum < 95) & (front > 0.9)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            dup = hid & front_ink
            thin = dup & ~cv2.erode(dup.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)   # lines, not dark areas
            for bx in boxes_of(thin, min_area=40):
                sus.append(dict(type='藏線', box=bx[:4], n=bx[4]))
        # 破洞: see-through pixels inside the layer's own filled body
        filled = body.copy()
        nn, lab2, st2 = components(~body)
        edge = set(lab2[0]) | set(lab2[-1]) | set(lab2[:, 0]) | set(lab2[:, -1])
        inner = ~body & ~np.isin(lab2, list(edge))
        holes = inner & (al < 0.35) & (comp_a[region] > 0.9)          # (a gap the original itself shows through is no hole)
        for bx in boxes_of(holes, min_area=12):
            sus.append(dict(type='破洞', box=bx[:4], n=bx[4]))
        # 灰邊: rim pixels still the flat source grey (un-mixing failed)
        rim = (al > 0.3) & ~cv2.erode(body.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        grey = rim & (np.abs(rgb - 128).max(-1) < 10)
        for bx in boxes_of(grey, min_area=25):
            sus.append(dict(type='灰邊', box=bx[:4], n=bx[4]))
        for candidate in sus:
            candidate['box'][0] += ox
            candidate['box'][1] += oy
        fn = f"{L['i']:02d}.webp"
        L['img'].save(os.path.join(out_dir, fn), 'WEBP', lossless=True)
        index.append(dict(name=L['name'], file=fn, x=L['x'], y=L['y'], w=L['w'], h=L['h'], group=L['group'],
                          hidden=L['hidden'], backing=backing, z=round(L['z'], 4), suspects=sus))
    Image.fromarray((comp * 255).clip(0, 255).astype(np.uint8), 'RGBA').save(os.path.join(out_dir, 'composite.webp'), 'WEBP', quality=92)
    meta = dict(id=mid, private=mid in PRIVATE_IDS, name=NAMES.get(mid, mid), W=W, H=H, build=j['meta'].get('version', ''), layers=index)
    json.dump(meta, open(os.path.join(out_dir, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    tot = {}
    for L in index:
        for s_ in L['suspects']:
            tot[s_['type']] = tot.get(s_['type'], 0) + 1
    print(f'{mid}: {len(index)} layers, {W}x{H}, suspects {tot}')
    return meta


if __name__ == '__main__':
    catalog = json.load(open(os.path.join(DEMO, 'models.json'), encoding='utf-8-sig'))
    NAMES.update({m['id']: m['name'] for m in catalog})
    ids = sorted(f[:-4] for f in os.listdir(os.path.join(DEMO, 'models')) if f.endswith('.inp')) if '--all' in sys.argv else ([arg for arg in sys.argv[1:] if not arg.startswith('--')] or list(NAMES))
    allm = []
    for mid in ids:
        cached = os.path.join(DEMO, 'layers', mid, 'index.json')
        if '--missing' in sys.argv and os.path.exists(cached):
            allm.append(json.load(open(cached, encoding='utf-8')))
        else:
            allm.append(export(mid))
    lst = os.path.join(DEMO, 'layers', 'models.json')
    previous = json.load(open(lst, encoding='utf-8')) if os.path.exists(lst) else []
    merged = {m['id']: m for m in previous}
    merged.update({m['id']: dict(id=m['id'], name=m['name'], build=m['build'], private=m['id'] in PRIVATE_IDS, category=merged.get(m['id'], {}).get('category', category_of(m['id']))) for m in allm})
    json.dump(list(merged.values()), open(lst, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
