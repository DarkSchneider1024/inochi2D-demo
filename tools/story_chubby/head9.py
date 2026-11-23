"""胖大叔九軸（2026-11-23，照 story_tareme/head9.py → story_burly/head9.py 複製、數值換成他自己的臉；那兩個檔不動）。
下巴尖在兩眼中點正下方（2026-11-14 規則）。做法見 story_burly/head9.py 的說明；全部 base px，寫進模型時乘 SCALE。
胖大叔臉大：太陽穴處頭半寬約 105 px（光頭臉 x 408..619），兩眼虹膜中心 y 242.5，下巴尖 370.5。
"""
import math

import art as A

FX = float(A.AXIS)                     # 513.5
R = 105.0
FLAT = .50                             # 兩眼虹膜中心 u ≈ ±0.47 在平面上
EYE_Y = 242.5
CHIN_Y = 370.5
SKULL_TOP, SKULL_BLEND = 14.0, 80.0
S_YAW, S_PITCH = 22.0, 16.5
ALPHA, BETA = .40, .40
YAW_DEG, PITCH_DEG = 20.0, 15.0
K_YAW = 1 - math.cos(math.radians(YAW_DEG))
K_PITCH = 1 - math.cos(math.radians(PITCH_DEG))
CY = EYE_Y
BACK_DEPTH = -.3
EAR_FAR, EAR_NEAR = .45, .10
EAR_ROOT = 104.0
NECK_X, NECK_Y = .45, .5
SIDE_K = 1.5
def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def g(x):
    u = abs(x - FX) / R
    if u <= FLAT:
        return 1.0
    if u >= 1.0:
        return 0.0
    return math.cos(math.pi / 2 * (u - FLAT) / (1 - FLAT)) ** 2


def skull(y):
    return smooth01((EYE_Y - SKULL_TOP - y) / SKULL_BLEND)


def face_depth(x, y):
    return g(x) * (1 - skull(y))


def offset(x, y, a, b, depth):
    """base px offset at yaw a, pitch b (-1..1; pitch +1 = looking up)"""
    dx = a * S_YAW * (ALPHA + (1 - ALPHA) * depth) - K_YAW * abs(a) * (x - FX)
    dy = -b * S_PITCH * (BETA + (1 - BETA) * depth) - K_PITCH * abs(b) * (y - CY)
    return dx, dy


def ear(side, x, y, a, b):
    x0 = FX + side * EAR_ROOT
    dep = face_depth(x0, y)
    dx, _ = offset(x0, y, a, b, dep)
    _, dy = offset(x, y, a, b, dep)
    far = a * side > 0
    dx -= (x - x0) * (K_YAW + (EAR_FAR if far else -EAR_NEAR)) * abs(a)
    return dx, dy


def neck_fn(base):
    top = CHIN_Y - 25

    def fn(x, y, a, b):
        cx, cy_ = offset(FX, CHIN_Y, a, b, 1.0)
        w = 1 - smooth01((y - top) / max(1.0, base - top))
        return NECK_X * cx * w, NECK_Y * cy_ * w
    return fn


def point(name, x, y, a, b):
    """offset of one head-layer point"""
    if name.startswith('後髮'):
        return offset(x, y, a, b, BACK_DEPTH)
    if name.startswith('耳朵'):
        return ear(1 if name.endswith('_L') else -1, x, y, a, b)
    return offset(x, y, a, b, face_depth(x, y))


def head_parts(model):
    head, root = model.parts['Head'], model.parts['Root']
    out = []
    for name, part in model.parts.items():
        if part.get('type') != 'Part':
            continue
        p = model.parents[part['uuid']]
        while p not in (head, root):
            p = model.parents[p['uuid']]
        if p is head:
            out.append((name, part))
    return out


def apply(model, B):
    """rewrite every head layer's Head:: Yaw-Pitch deform (3 x 3) with the one projection; the neck's top follows the chin"""
    yaw = model.params['Head:: Yaw-Pitch']
    pa, pb = yaw['axis_points']
    done = []
    todo = [(n, p, lambda x, y, a_, b_, n=n: point(n, x, y, a_, b_)) for n, p in head_parts(model)]
    if '脖子' in model.parts:
        neck = model.parts['脖子']
        todo.append(('脖子', neck, neck_fn(max(q[1] for q in B.base_xy(model, neck)))))
    for name, part, fn in todo:
        pts = B.base_xy(model, part)
        vals = [[[[v * B.SCALE for v in fn(x, y, av * 2 - 1, bv * 2 - 1)] for x, y in pts] for bv in pb] for av in pa]
        B.bind(model, 'Head:: Yaw-Pitch', part, 'deform', vals)
        done.append(name)
    yaw['bindings'] = [b for b in yaw['bindings'] if b['param_name'] != 'opacity']
    return done


def bake_side(model, B, a=SIDE_K):
    """the side model's head: the same projection at yaw a, baked into every head mesh (and the neck's top)"""
    for name, part in head_parts(model):
        v = part['mesh']['verts']
        for k, (x, y) in enumerate(B.base_xy(model, part)):
            dx, dy = point(name, x, y, a, 0.0)
            v[2 * k] += dx * B.SCALE
            v[2 * k + 1] += dy * B.SCALE
    return FX + a * S_YAW        # the turned face axis (the front plane's travel)
