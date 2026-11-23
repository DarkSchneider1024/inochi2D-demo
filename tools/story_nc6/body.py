"""《國王的新衣》V6 線先生、小朵的體型（2026-11-23 統籌看對照圖後要求）。

    python -X utf8 tools/story_nc6/body.py <id> [--side] [--out path.inp]

在「已建好、還沒套講解／思考」的模型上動手（rebuild.py 的順序），頭、臉、脖子一層都不動（光頭臉仍和臉模逐像素相同）：
  1. story_mix/mix.reshape（身材×眼睛混搭用的同一套）：軀幹寬度曲線、四肢粗細、身體以下巴下的頸點整體等比縮放（頭不縮＝頭變大）。
  2. 腿再縮短：腿的每層（含動作的變形量）以髖為定點垂直壓 k 倍，影子跟著腳往上。側面是腿關節鏈（Thigh F／B 底下）一起壓。
  3. 線先生的圓肚子：軀幹各層再加一個以皮帶高度為中心的高斯鼓起（正面左右鼓；側面只往前鼓），皮帶中間跟著肚子往下彎。
     肚子是軀幹圖層本身的形狀，所以轉頭、走路時跟身體一起動。
小朵：卡洛兒 v3 骨架，身體縮 0.78、腿再 0.86 → 約 4.5 頭身（6～7 歲）；線先生：柏達克骨架，矮胖版（身體 0.93、腿 0.90、肚子）。
數字記在 meta.storyNc6Body（think_draw.py 用它換算思考手臂的肩、肘位置）。重跑同一個模型會被擋（不是冪等，要從頭 rebuild）。
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (TOOLS, TOOLS / 'story_mix'):
    sys.path.insert(0, str(p))
import mix                                    # noqa: E402
from build_story_trio import Model            # noqa: E402

CFG = {
    'duo_nc_carolv3': dict(body=dict(scale=.78, shoulder=.96, chest=.96, waist=.98, hip=1.0, arm=1.08, leg=1.10), leg=.86),
    'thread_nc_burlyv3': dict(body=dict(scale=.94, shoulder=1.10, chest=1.14, waist=1.22, hip=1.14, arm=1.12, leg=1.16), leg=.90,
                              belly=dict(a=.22, y=-110.0, s=170.0), belt_sag=24.0),
}


def leg_parts(m, side):
    if side:
        out = []
        for root in ('Thigh F', 'Thigh B'):
            out += [n for n in mix.subtree(m.parts[root]) if n.get('type') == 'Part']
        return out
    return [m.parts[n] for n, k in mix.classify(m).items() if k != 'torso' and k[0] == 'leg']


def scale_bindings(m, ids, ky, tx=1.0):
    for prm in m.params.values():
        for b in prm['bindings']:
            if b['node'] not in ids:
                continue
            if b['param_name'] == 'deform':
                v = np.asarray(b['values'], float)
                if v.ndim >= 2 and v.shape[-1] == 2:
                    v[..., 1] *= ky
                    v[..., 0] *= tx
                    b['values'] = v.tolist()
            elif b['param_name'] == 'transform.t.y':
                b['values'] = (np.asarray(b['values'], float) * ky).tolist()


def shorten_legs(m, k, side):
    if side:
        yh = mix.world_origin(m, m.parts['Thigh F'])[1]
        nodes = []
        for root in ('Thigh F', 'Thigh B'):
            nodes += mix.subtree(m.parts[root])
        world = {n['uuid']: np.array(mix.world_origin(m, n)) for n in nodes}
        verts = {n['uuid']: mix.wverts(m, n) for n in nodes if n.get('type') == 'Part'}
        f = lambda p: np.stack([p[..., 0], yh + k * (p[..., 1] - yh)], -1)
        mix._set_origins(m, {u: f(w) for u, w in world.items()})
        for n in nodes:
            if n['uuid'] in verts:
                mix.set_wverts(m, n, f(verts[n['uuid']]))
        parts = [n for n in nodes if n.get('type') == 'Part']
    else:
        thigh = mix.wbox(m, m.parts['大腿_R'])
        yh = thigh[1] + .05 * (thigh[3] - thigh[1])
        parts = leg_parts(m, False)
        for p in parts:
            r = mix.wverts(m, p)
            mix.set_wverts(m, p, np.stack([r[:, 0], yh + k * (r[:, 1] - yh)], 1))
    scale_bindings(m, {p['uuid'] for p in parts}, k)
    foot = max(mix.wbox(m, p)[3] for p in parts if p.get('opacity', 1) > 0)
    shadow = m.parts.get('影子')
    if shadow is not None:
        r = mix.wverts(m, shadow)
        old_foot = yh + (foot - yh) / k
        r[:, 1] += foot - old_foot
        mix.set_wverts(m, shadow, r)
    return yh


def belly(m, side, a, y, s, sag=0.0):
    """round belly: torso layers bulge sideways (front) / forwards (side) around the belt line; the belt dips in the middle"""
    head_ids = {n['uuid'] for n in mix.subtree(m.parts['Head'])}
    cx = mix.world_origin(m, m.parts['Head'])[0]
    kinds = mix.classify(m, side)
    torso = [m.parts[n] for n, k in kinds.items() if k == 'torso' and m.parts[n]['uuid'] not in head_ids and n not in ('影子',)]
    fwd = 1 if not side else (1 if m.json['meta'].get('storySideFacing', 'right') == 'right' else -1)

    def bump(p):
        p = np.array(p, float)
        g = a * np.exp(-((p[..., 1] - y) / s) ** 2)
        dx = p[..., 0] - cx
        if side:
            g = np.where(dx * fwd > 0, g * 1.6, g * .25)     # side: mostly forwards, a little behind
        p[..., 0] = cx + dx * (1 + g)
        return p

    for part in torso:
        rest = mix.wverts(m, part)
        mix._apply_part(m, part, rest, bump(rest), lambda r, q: bump(q))
    if sag and '腰帶' in m.parts and not side:
        belt = m.parts['腰帶']
        r = mix.wverts(m, belt)
        x0, x1 = r[:, 0].min(), r[:, 0].max()
        t = np.clip((r[:, 0] - (x0 + x1) / 2) / ((x1 - x0) / 2), -1, 1)
        r[:, 1] += sag * (1 - t ** 2)
        mix.set_wverts(m, belt, r)


def apply(mid, side=False, out=None):
    sid = mid + ('_side' if side else '')
    m = Model(sid)
    if m.json['meta'].get('storyNc6Body'):
        raise SystemExit(f'{sid} 已經套過體型（storyNc6Body），請先重建模型')
    cfg = CFG[mid]
    jpath = m.path.with_name(f'{sid}.joints.json')
    sh = mix.reshape(m, cfg['body'], side)
    yh = shorten_legs(m, cfg['leg'], side)
    if cfg.get('belly'):
        b = cfg['belly']
        belly(m, side, b['a'], b['y'], b['s'], cfg.get('belt_sag', 0.0))
    m.json['meta']['storyNc6Body'] = dict(cfg, neck=[float(v) for v in sh.n], ky=[float(v) for v in sh.ky],
                                          kv=[float(v) for v in sh.kv], hip=float(yh))
    path = mix.save(m, Path(out).stem if out else sid, folder=Path(out).parent if out else None, explain=False)
    if side and jpath.exists() and not out:
        mix.joints_json(m, jpath, jpath)
    print('body', path)
    return path


def body_map(meta):
    """base-model root point -> reshaped root point (torso width curve, then the uniform scale about the neck)"""
    b = meta
    n = np.array(b['neck'])
    s = b['body']['scale']

    def f(x, y):
        k = float(np.interp(y, b['ky'], b['kv']))
        x = n[0] + k * (x - n[0])
        return n[0] + s * (x - n[0]), n[1] + s * (y - n[1])
    return f


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    if out in args:
        args.remove(out)
    apply(args[0], '--side' in sys.argv, out)
