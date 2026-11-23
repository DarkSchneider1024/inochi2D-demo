"""胖大叔說故事 v3・側面走路（chubby_hand_v3_side），V1 的做法（2026-11-23，照 story_tareme/side.py → story_burly/side.py 複製改寫；那兩個檔不動）。
    python -X utf8 inochi2D-demo/tools/story_chubby/side.py [front_id side_id]   -> inochi2D-demo/models/chubby_hand_v3_side.inp（.inx、.joints.json）
改的地方：他的數值（關節、下顎、後腦、短髮）、側面皮鞋、啤酒肚跟軀幹一起轉（軀幹前後厚度加大）、襯衫領／吊帶／褲頭／腰帶跟軀幹轉。
做法說明見 story_burly/side.py 開頭（V1：正面部件轉 3/4 身體掛走路骨架＋九軸正臉約 30 度、臉朝前進方向）。
"""
from copy import deepcopy
from io import BytesIO
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from build_story_trio import Model, binding, set_part_image, walk   # noqa: E402
from build_story_trio import WALK_HIP as WALK_HIP_SHARED            # noqa: E402
import art as A                                                      # noqa: E402
from art import G, path, crescent, f                                 # noqa: E402
import build as B                                                    # noqa: E402
import head9 as H9                                                   # noqa: E402

ROOT = HERE.parents[2]
MODELS = ROOT / 'inochi2D-demo/models'
FRONT, SID = 'chubby_hand_v3', 'chubby_hand_v3_side'
SCALE = 1.25
BODY_YAW = 37.0      # 軀幹外輪廓縮成正面的 cos37°＝0.80（V1 卡洛兒 0.83、V1 卡洛特 0.78）
FRONT_SWING = .45
ARM_IN, ARM_W = .58, .86   # 手臂往身體中線靠、略窄（V1：0.52～0.57、0.80～0.83）
LEG_IN, LEG_W = .47, .90   # 大腿往中線靠、略窄（V1：0.47、0.90）
# (2026-11-16 使用者看《小紅帽》V20：「獵人側面腿太粗 改細一些」) 換裝可再收腿：LEG_THIN 只乘在大腿、小腿網格的寬（關節位置不動），
# BOOT_W 只乘在側面靴的寬（以腳踝那一欄為中心，鞋底高度不動）。預設 1.0＝柏達克原樣；hunter.py --side 設較細的值
LEG_THIN, BOOT_W = 1.0, 1.0
HEAD_YAW = 30.0      # 正面頭九軸轉 30 度（2026-11-14：用 head9 同一套投影，a = H9.SIDE_K）
TURN_AXIS = H9.FX + H9.SIDE_K * H9.S_YAW   # 轉過去的臉中軸（正面平面的位移量），下顎線以它為準
STRIDE_K = 1.0       # (2026-11-14 走路跨步不要太大) 大腿擺幅＝共用 WALK_HIP .30 × 1.15 ≈ 0.345 rad ≈ 19.8 度（規則：前後各約 20 度內）；柏達克腿短身長，步幅量到約 0.22 身高
NECK_EXT = 30.0      # 底圖 px：脖子下半段在側面再往下伸（藏進轉過去的領口、胸口）
NECK_DX, NECK_K = 16.0, 1.19   # 標準脖子在 3/4 時往前進方向挪幾 px（底圖 px）、加寬（要填到轉過去的下巴下面，同 male2_side3）
DEPTH = .55          # 軀幹前後厚度 ÷ 半寬
CX = (A.AXIS - 512) * SCALE
TORSO = ('脖子', '後領', '胸腔', '前領', '腰帶', '褲頭', '背心_R', '背心_L')
HALF = {n: 290.0 for n in ('胸腔', '後領', '前領', '腰帶', '褲頭', '背心_R', '背心_L')}   # 啤酒肚：整個軀幹同一個柱面   # 半寬（模型單位）；沒列的用該層自己的
DROP_PARAMS = ('Head:: Yaw-Pitch', 'Head:: Roll', 'Arm:: Think', 'Arm:: Wave', 'Arm:: Wave:: Sway', 'Arm:: Right:: Greeting', 'Body:: Squat', 'Acc:: Glasses Off')
DROP_PREFIX = ('Arm:: Right::', 'Arm:: Left::', 'Hand::', 'Leg:: Right::', 'Leg:: Left::')
DROP_PARTS = ('揮手', '舉手上臂_', '握手_', '無掌_', '指手', '握拳', '推鏡', '托腮', '思考', '講解臂')
DIM = .8


def wpos(model, node):
    return B.abs_pos(model, node)


def turn_x(x, half):
    """root x of a point on the torso's front surface after the body turns BODY_YAW toward +x"""
    th = math.radians(BODY_YAW)
    X = x - CX
    u = max(-1.0, min(1.0, X / half))
    ex = X - u * half                       # beyond the cylinder's edge: carried along
    Z = DEPTH * half * (1 - u * u)          # a parabola, not a circle: x' stays monotonic, so no layer folds back at the far edge
    return CX + u * half * math.cos(th) + Z * math.sin(th) + ex * math.cos(th)


def set_world(model, node, x, y):
    px, py = wpos(model, model.parents[node['uuid']])
    node['transform']['trans'][0], node['transform']['trans'][1] = x - px, y - py


def reparent(model, node, new_parent):
    x, y = wpos(model, node)
    old = model.parents[node['uuid']]
    old['children'].remove(node)
    new_parent.setdefault('children', []).append(node)
    model.parents[node['uuid']] = new_parent
    set_world(model, node, x, y)


def new_node(model, name, parent, x, y):
    node = dict(uuid=model.uuid, name=name, type='Node', enabled=True, zsort=0.0, lockToRoot=False, children=[],
                transform=dict(trans=[0.0, 0.0, 0.0], rot=[0.0, 0.0, 0.0], scale=[1.0, 1.0]))
    model.uuid += 1
    parent.setdefault('children', []).append(node)
    model.parents[node['uuid']] = parent
    model.parts[name] = node
    set_world(model, node, x, y)
    return node


def tex(model, part):
    return Image.open(BytesIO(model.textures[part['textures'][0]][5:])).convert('RGBA')


def dim(model, part, k=DIM):
    im = tex(model, part)
    a = im.getchannel('A')
    im = ImageEnhance.Brightness(im.convert('RGB')).enhance(k).convert('RGBA')
    im.putalpha(a)
    set_part_image(model, part, im)


BOOT_CUFF = None     # (cuff colour, line) for an outfit whose boots have a plain cuff; None = the fur cuff


def side_boot(far):
    """朝前進方向（畫面右）的圓頭皮鞋，本地座標：鞋口中心在 (0, 0)、往下 y+；高 h（褲管蓋住鞋口）"""
    g = G('side_boot_far' if far else 'side_boot')
    h = 120.0
    fill = g.lin(-70, 0, 170, 0, [(0, A.SHOE_D), (.3, A.SHOE), (.6, A.SHOE_L), (.85, A.SHOE), (1, A.SHOE_D)])
    d = (f'M-62 -6 L52 -6 Q70 30 104 46 Q150 60 168 84 Q178 104 166 {h:.0f} L-64 {h:.0f} Q-76 60 -62 -6Z')
    c = g.clip(d)
    lace = ''.join(f'<path d="M{8 + i * 14} {18 + i * 8} L{30 + i * 14} {26 + i * 8}" fill="none" stroke="{A.SHOE_LINE}" stroke-width="3" stroke-linecap="round"/>' for i in range(3))
    ins = (f'<path d="M-80 {h - 16:.0f} H190 V{h + 10:.0f} H-80Z" fill="{A.SHOE_LINE}"/>'
           f'<ellipse cx="120" cy="66" rx="30" ry="12" fill="{A.SHOE_L}" opacity=".55" filter="{g.blur(5)}"/>'
           f'<path d="M-40 10 Q-50 50 -44 90" fill="none" stroke="{A.SHOE_L}" stroke-width="10" stroke-linecap="round" opacity=".35" filter="{g.blur(5)}"/>'
           + lace)
    g.add(path(d, fill) + f'<g clip-path="{c}">{ins}</g>' + path(d, 'none', A.SHOE_LINE, 2.6))
    return g, h


# 後腦的頭髮（側面共用步驟）：顏色可由換裝腳本覆寫（凱伊換髮色時改這個 dict 再呼叫 build）
BACK_HAIR = dict(top=A.HAIR, bottom=A.HAIR_D, line=A.HAIR_LINE, strand=A.HAIR_D, light=A.HAIR_L)
# 後腦勺的輪廓（底圖座標，頭朝畫面右時在畫面左）：頭頂 → 後腦圓弧 → 後頸短髮束 → 回到耳後
BACK_HAIR_PTS = [(505, 52), (470, 56), (436, 70), (408, 96), (388, 132), (376, 176), (372, 224), (376, 268), (386, 302), (398, 326),
                 (410, 314), (422, 330), (432, 304), (440, 258), (446, 200), (456, 140), (476, 90)]   # 胖大叔短髮：後頸只到 y≈330
# (2026-11-14 後頸髮束補上) 後頸三撮短髮束垂到 y≈236（在脖子後面、耳垂後下方，不碰近側下顎線）


# (2026-11-14 凱伊：戴盔時後腦那層頭髮在頭盔後面鼓出一塊、像綁馬尾) 換裝有帽子／頭盔時，換裝腳本設這個輪廓（底圖座標，
# 只有帽簷以下、貼著後頸的短髮）：戴著（Acc:: Hat Off＝0）顯示這片短髮、整片後腦髮藏起來；摘掉才顯示整片後腦髮。None＝不做。
BACK_HAIR_HAT_PTS = None


def back_hair(model, page):
    """(2026-11-13 使用者：「側面後髮沒有，看起來很扁平」) the head turned 30 deg shows the back of the skull on the side away
    from the face: one hand-drawn layer behind everything of the head -- the round mass of the back of the head and short
    locks on the nape, same hair colours and flow lines -- so the head has depth. It hides with Acc:: Hair Off and sways a
    little with Hair:: Sway. Shared step: outfits built on this side model (other hair colours) set BACK_HAIR first.
    With BACK_HAIR_HAT_PTS (an outfit with a hat) a second, short nape layer 後髮_側_盔 shows while the hat is on and the full
    one only with the hat off (opacity bindings multiply: Hair Off x Hat Off)."""
    full = _back_hair_layer(model, page, BACK_HAIR_PTS, '後髮_側')
    if BACK_HAIR_HAT_PTS and 'Acc:: Hat Off' in model.params:
        short = _back_hair_layer(model, page, BACK_HAIR_HAT_PTS, '後髮_側_盔', zs=.0041)
        hat = model.params['Acc:: Hat Off']['bindings']
        hat.append({'node': full['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear', 'isSet': [[True], [True]], 'values': [[0], [1]]})
        hat.append({'node': short['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear', 'isSet': [[True], [True]], 'values': [[1], [0]]})
    return full


def _back_hair_layer(model, page, pts, name, zs=.004):
    c = BACK_HAIR
    g = G('side_back_hair')
    d = A.curve_d(pts, True, 8)
    fill = g.lin(0, 60, 0, 380, [(0, c['top']), (1, c['bottom'])])
    cl = g.clip(d)
    strands = []
    for k in range(9):                       # the hair flows from the crown down the back of the head to the nape
        t = k / 8
        x0, y0 = 500 - 46 * t, 68 + 22 * t
        x1, y1 = 398 + 50 * t, 300 + 70 * t
        cx, cy = 402 + 34 * t - 20 * (1 - t), 150 + 40 * t
        strands.append(f'M{f(x0)} {f(y0)} Q{f(cx)} {f(cy)} {f(x1)} {f(y1)}')
    band = crescent((420, 110), (404, 150), (402, 200), 7) + ' ' + crescent((440, 90), (424, 130), (420, 180), 6)
    g.add(f'<g transform="scale({SCALE}) translate(-512 -135)">' + path(d, fill)
          + f'<g clip-path="{cl}"><path d="{band}" fill="{c["light"]}" opacity=".45" filter="{g.blur(2)}"/>'
            f'<path d="{" ".join(strands)}" fill="none" stroke="{c["strand"]}" stroke-width="1.1" stroke-linecap="round" opacity=".6"/></g>'
          + path(d, 'none', c['line'], 1.9) + '</g>')
    img, (x0, y0, x1, y1) = render(page, g.out(), pad=300)
    y0, y1 = y0 - 615 * SCALE, y1 - 615 * SCALE          # the drawing sat 615 base px lower so it fits the render window
    head = model.parts['Head']
    src = model.parts['後髮_主']
    part = deepcopy(src)
    part.update(uuid=model.uuid, name=name, masks=[], opacity=1, zsort=src['zsort'] + zs, children=[])
    model.uuid += 1
    head['children'].append(part)
    model.parents[part['uuid']] = head
    model.parts[name] = part
    part['textures'] = [len(model.textures), 4294967295, 4294967295]
    model.textures.append(model.textures[src['textures'][0]])
    hx, hy = wpos(model, head)
    w_, h_ = x1 - x0, y1 - y0
    part['transform'] = dict(trans=[(x0 + x1) / 2 - hx, (y0 + y1) / 2 - hy, 0], rot=[0, 0, 0], scale=[1, 1])
    cols, rows = 5, 6
    uv = [(a / (cols - 1), b / (rows - 1)) for b in range(rows) for a in range(cols)]
    tris = []
    for b in range(rows - 1):
        for a in range(cols - 1):
            q = b * cols + a
            tris += [q, q + cols, q + 1, q + 1, q + cols, q + cols + 1]
    part['mesh'] = dict(origin=[0, 0], indices=tris, uvs=[v for p in uv for v in p], verts=[v for u, t in uv for v in ((u - .5) * w_, (t - .5) * h_)])
    set_part_image(model, part, img)
    for name, prm in model.params.items():
        prm['bindings'] = [b for b in prm['bindings'] if b['node'] != part['uuid']]
    if 'Acc:: Hair Off' in model.params:
        model.params['Acc:: Hair Off']['bindings'].append({'node': part['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                                          'isSet': [[True], [True]], 'values': [[1], [0]]})
    if 'Hair:: Sway' in model.params:        # the nape locks sway a little
        keys = model.params['Hair:: Sway']['axis_points'][0]
        vals = []
        for kk in keys:
            ph = 2 * kk - 1
            vals.append([[[ph * 4.0 * max(0.0, t - .55) / .45 * SCALE, 0.0] for u, t in uv]])
        model.params['Hair:: Sway']['bindings'].append({'node': part['uuid'], 'param_name': 'deform', 'interpolate_mode': 'Linear',
                                                       'isSet': [[True] for _ in keys], 'values': vals})
    return part


# ---- 側面下顎線（側面共用步驟；2026-11-13 使用者：「關鍵是側面下顎線要出來」）----
JAW_TOP, JAW_BOTTOM = 300.0, 370.0     # 底圖 y：耳垂 → 下巴尖
JAW_NEAR, JAW_FAR = 16.0, 9.0           # 近側下顎往下巴尖收幾 px（成一條斜線）；遠側臉頰收窄幾 px（2026-11-14：下巴尖不再另外推，留在兩眼中軸上）
JAW_HALF = 105.0


def jaw_dx(x, y):
    """how far (base px, toward +x) a point of the lower face goes: nothing above the ear lobe, most at the jaw; the near
    side (x < the turned axis) toward the chin, so the near jaw becomes one slanting line from under the ear to the chin's
    tip; the far cheek a little narrower; the chin's tip itself (on the axis) stays"""
    t = max(0.0, min(1.0, (y - JAW_TOP) / (JAW_BOTTOM - JAW_TOP)))
    t = t * t * (3 - 2 * t)
    q = (x - TURN_AXIS) / JAW_HALF
    near = max(0.0, min(1.0, -q))
    far = max(0.0, min(1.0, q))
    return t * (JAW_NEAR * near - JAW_FAR * far)


def jawline(model):
    """the lower face of every head layer except hair and ears (face, beard, nose, mouth shapes, blush, tears) takes
    jaw_dx: the chin's tip points where he walks and the near jaw line runs clear from the ear lobe down to it"""
    head, root = model.parts['Head'], model.parts['Root']
    for name, part in model.parts.items():
        if part.get('type') != 'Part' or name.startswith(('後髮', '頭頂髮', 'Hair Lock ', '耳朵', '脖子影', '前側髮', '呆毛')):
            continue
        p = model.parents[part['uuid']]
        while p not in (head, root):
            p = model.parents[p['uuid']]
        if p is not head:
            continue
        v = part['mesh']['verts']
        for k, (x, y) in enumerate(B.base_xy(model, part)):
            v[2 * k] += jaw_dx(x, y) * SCALE


def jaw_shadow(model, page):
    """the shadow of the jaw on the neck: a soft band just under the near jaw line (under the head, over the neck), so the
    face and the neck read as two planes. With a beard it sits under the beard's lower edge; without one (Kay) it is what
    draws the jaw."""
    face = model.parts['臉']
    lo = [(x, y) for x, y in B.base_xy(model, face) if y > 250]
    # the near jaw line as built: for sample rows, the leftmost face vertex after the warp
    rows = sorted({round(y, 1) for _, y in lo})
    line = []
    for yy in rows:
        xs = [x for x, y in lo if abs(y - yy) < .2]
        if yy >= JAW_TOP + 14:
            line.append((min(xs), yy))
    chin = max(lo, key=lambda q: q[1])
    pts = [(x + 5, y + 1) for x, y in line] + [(chin[0] + 6, chin[1] + 1)]
    low = [(x + 15, y + 15) for x, y in pts[::-1]]
    g = G('side_jaw_shadow')
    d = A.curve_d(pts + low, True, 6)
    g.add(f'<g transform="scale({SCALE}) translate(-512 -135)"><path d="{d}" fill="{A.SKIN_DD}" opacity=".62" filter="{g.blur(2.6)}"/></g>')
    img, (x0, y0, x1, y1) = render(page, g.out(), pad=300)
    y0, y1 = y0 - 615 * SCALE, y1 - 615 * SCALE
    head = model.parts['Head']
    part = deepcopy(face)
    part.update(uuid=model.uuid, name='下顎影', masks=[], opacity=1, zsort=.50, children=[])   # (2026-11-14) behind the fur and cape fronts: the neck mask alone would let it paint over them
    model.uuid += 1
    head['children'].append(part)
    model.parents[part['uuid']] = head
    model.parts['下顎影'] = part
    part['textures'] = [len(model.textures), 4294967295, 4294967295]
    model.textures.append(model.textures[face['textures'][0]])
    hx, hy = wpos(model, head)
    w_, h_ = x1 - x0, y1 - y0
    part['transform'] = dict(trans=[(x0 + x1) / 2 - hx, (y0 + y1) / 2 - hy, 0], rot=[0, 0, 0], scale=[1, 1])
    part['mesh'] = dict(origin=[0, 0], indices=[0, 2, 1, 1, 2, 3], uvs=[0, 0, 1, 0, 0, 1, 1, 1], verts=[-w_ / 2, -h_ / 2, w_ / 2, -h_ / 2, -w_ / 2, h_ / 2, w_ / 2, h_ / 2])
    set_part_image(model, part, img)
    for prm in model.params.values():
        prm['bindings'] = [b for b in prm['bindings'] if b['node'] != part['uuid']]
    part['masks'] = [{'source': model.parts['脖子']['uuid'], 'mode': 'Mask'}]      # (2026-11-14) only on the neck
    return part


def render(page, svg, pad=260):
    ppu = 1.5
    page.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style><svg width="{2 * pad * ppu}" height="{(2 * pad + 200) * ppu}" '
                     f'viewBox="{-pad} {-pad} {2 * pad} {2 * pad + 200}">{svg}</svg>')
    im = Image.open(BytesIO(page.locator('svg').screenshot(omit_background=True))).convert('RGBA')
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > 8)
    x0, y0, x1, y1 = xs.min() - 3, ys.min() - 3, xs.max() + 4, ys.max() + 4
    return im.crop((x0, y0, x1, y1)), (x0 / ppu - pad, y0 / ppu - pad, x1 / ppu - pad, y1 / ppu - pad)


def build(front=FRONT, sid=SID, extra_torso=(), title='胖大叔說故事 v3・側面'):
    """front: the front model to turn (burly_hand_v3 or an outfit built on it, e.g. kay_burlyv3); extra_torso: the outfit's
    own body layers turned with the torso (collars, breastplate); 肩甲_R／肩甲_L, when there, ride the arms like the sleeves"""
    model = Model(front)
    root, body, head = model.parts['Root'], model.parts['Body'], model.parts['Head']
    # --- strip what a walking side model does not use
    for n in [n for n in model.parts if n.startswith(DROP_PARTS)]:
        B.drop(model, n)
    yawp = model.params['Head:: Yaw-Pitch']
    # --- head: (2026-11-14 下巴尖在兩眼中間) the front's nine-axis projection (head9.py) at a = SIDE_K toward +x, baked into
    # every head mesh: eyes, nose, mouth and chin move as one plane, so the chin stays under the eyes' midpoint
    model.parts['耳朵_L']['opacity'] = 0           # the far ear is behind the turned face
    H9.bake_side(model, B)
    ear_r = model.parts['耳朵_R']                   # the near ear stays on the side of the skull, a little further back
    ear_r['transform']['trans'][0] -= 3 * SCALE
    jawline(model)
    for name in list(model.params):
        if name in DROP_PARAMS or name.startswith(DROP_PREFIX):
            model.json['param'].remove(model.params.pop(name))
    # one blink for both eyes (the stage's side convention)
    bl = model.params.pop('Eye:: Left:: Blink')
    br_ = model.params.pop('Eye:: Right:: Blink')
    model.json['param'].remove(bl)
    br_['name'] = 'Eye:: Blink'
    br_['bindings'] += bl['bindings']
    model.params['Eye:: Blink'] = br_
    # --- torso: every layer's mesh turned on its own cylinder
    for name in [n for n in TORSO + tuple(extra_torso) if n in model.parts]:
        part = model.parts[name]
        px, py = wpos(model, part)
        v = part['mesh']['verts']
        half = HALF.get(name) or max(abs(x + px - CX) for x in v[::2])
        for k in range(0, len(v), 2):
            if name in ('毛領_前', '毛領_後'):   # the fur's top edge lowered so the jaw line stays clear of it (the far lobe most:
                u = max(0.0, min(1.0, (v[k] + px - CX) / half))          # turned away it stood up like a horn by the face)
                yref = (300 - 750) * SCALE - py
                if v[k + 1] < yref:
                    v[k + 1] = yref - (yref - v[k + 1]) * (.62 - .25 * u)
            v[k] = turn_x(v[k] + px, half) - px
    nv = model.parts['脖子']['mesh']['verts']
    ncx = (min(nv[::2]) + max(nv[::2])) / 2
    nv[::2] = [ncx + (x - ncx) * NECK_K + NECK_DX * SCALE for x in nv[::2]]
    # the lower half reaches NECK_EXT further down, under the turned collar / chest (kay: the bottom showed through the collar's V)
    y0, y1 = (min(nv[1::2]) + max(nv[1::2])) / 2, max(nv[1::2])
    nv[1::2] = [y + NECK_EXT * SCALE * max(0.0, (y - y0) / (y1 - y0)) for y in nv[1::2]]
    # --- limbs, as the V1 sides (measured on carol_hand → carol_hand_side and mr_carrot_hand → mr_carrot_hand_side):
    # the torso's outline is about 0.8 of the front, the arms' centres come in to about 0.55-0.6 of their front distance from
    # the body's middle and the thighs' to about 0.47, each limb a little narrower (0.83-0.9), all symmetric about the
    # body's middle line -- so the hips' midpoint IS the middle of the torso's lower edge. near = the character's right
    # (image left) in front; far = left, behind and darker.
    J = {}
    for side, tag in (('R', 'F'), ('L', 'B')):
        mx = (lambda p: p) if side == 'R' else (lambda p: (2 * A.AXIS - p[0], p[1]))
        S, E = (B.world(*mx(p)) for p in (B.SHOULDER, B.ELBOW))
        hip = B.world(*mx((400.0, 860.0)))
        knee, ankle = B.world(*mx((400.0, 1190.0))), B.world(*mx((397.0, 1395.0)))
        ax = lambda x: CX + (x - CX) * ARM_IN        # where an arm point's column goes
        lx = lambda x: CX + (x - CX) * LEG_IN
        arm = new_node(model, f'Arm {tag}', body, ax(S[0]), S[1])
        fore = new_node(model, f'Forearm {tag}', arm, ax(S[0]) + (E[0] - S[0]) * ARM_W, E[1])
        thigh = new_node(model, f'Thigh {tag}', body, lx(hip[0]), hip[1])
        shin = new_node(model, f'Shin {tag}', thigh, lx(hip[0]) + (knee[0] - hip[0]) * LEG_W, knee[1])
        foot = new_node(model, f'Foot {tag}', shin, lx(hip[0]) + (ankle[0] - hip[0]) * LEG_W, ankle[1])
        J.update({f'Arm {tag}': arm, f'Forearm {tag}': fore, f'Thigh {tag}': thigh, f'Shin {tag}': shin, f'Foot {tag}': foot})
        for pname, parent, pivot, new_pivot, k in (
                (f'上臂_{side}', arm, S[0], ax(S[0]), ARM_W), (f'下臂_{side}', fore, S[0], ax(S[0]), ARM_W), (f'手掌_{side}', fore, S[0], ax(S[0]), ARM_W),
                (f'大腿_{side}', thigh, hip[0], lx(hip[0]), LEG_W), (f'小腿_{side}', shin, hip[0], lx(hip[0]), LEG_W), (f'鞋_{side}', foot, hip[0], lx(hip[0]), LEG_W),
                *([(f'肩甲_{side}', arm, S[0], ax(S[0]), ARM_W)] if f'肩甲_{side}' in model.parts else []),
                # (2026-11-16) elbow_cap.py 的手肘圓頭（前臂 E 以上那半圓）跟著前臂走，排在上臂後面（袖口蓋住上半）
                *([(f'手肘_{side}', fore, S[0], ax(S[0]), ARM_W)] if f'手肘_{side}' in model.parts else [])):
            part = model.parts[pname]
            x, y = wpos(model, part)
            old = model.parents[part['uuid']]
            old['children'].remove(part)
            parent['children'].append(part)
            model.parents[part['uuid']] = parent
            set_world(model, part, new_pivot + (x - pivot) * k, y)      # the limb narrowed by k about its own joint column
            v = part['mesh']['verts']
            kw = k * (LEG_THIN if pname.startswith(('大腿_', '小腿_')) else 1.0)
            v[::2] = [q * kw for q in v[::2]]
            for prm in model.params.values():          # no deforms or opacity switches from the front rig
                prm['bindings'] = [b for b in prm['bindings'] if b['node'] != part['uuid']]
            part['opacity'] = 1
        if side == 'L':     # far side: arm behind the torso and the near leg, leg behind the hips; a little darker
            # (2026-11-14 T19「手肘的圖層應該放最前面」) far arm: forearm, then hand, then the upper arm behind them
            arm_z = (('上臂_L', .712), ('下臂_L', .70), ('手掌_L', .705), ('手肘_L', .7122))
            if model.json.get('meta', {}).get('storyElbowUnder'):
                # (2026-11-16 獵人手肘方案 A，使用者：「這個腳色破例不用前臂要在袖子前面」) 正面是捲袖口蓋住手肘
                # （elbow_cap under_sleeve）：遠側也是袖子在前，手肘圓頭、前臂、手依序在後
                arm_z = (('上臂_L', .712), ('手肘_L', .7122), ('下臂_L', .7124), ('手掌_L', .7126))
            for n, z in arm_z + (('大腿_L', .75), ('小腿_L', .746), ('鞋_L', .755), ('肩甲_L', .699)):
                if n not in model.parts:
                    continue
                model.parts[n]['zsort'] = z
                if n != '鞋_L':
                    dim(model, model.parts[n])
        else:
            for n, z in (('大腿_R', .615), ('小腿_R', .612), ('鞋_R', .618)):
                model.parts[n]['zsort'] = z
    if '披肩_後' in model.parts:
        model.parts['披肩_後']['zsort'] = .76
    # --- boots that point where he walks
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='msedge')
        page = br.new_page(viewport={'width': 900, 'height': 1200})
        back_hair(model, page)
        jaw_shadow(model, page)
        for side, tag in (('R', 'F'), ('L', 'B')):
            g, h = side_boot(side == 'L')
            img, (x0, y0, x1, y1) = render(page, g.out())
            part = model.parts[f'鞋_{side}']
            jx, jy = wpos(model, J[f'Foot {tag}'])
            sole = max(p[1] for p in A.M['boot'])
            k = ((sole - 750) * SCALE - jy + 22) / h          # scaled so the sole lands where the front boot's does
            w_, h_ = (x1 - x0) * k * BOOT_W, (y1 - y0) * k
            cx, cy = jx + (x0 + x1) / 2 * k * BOOT_W, jy - 22 + (y0 + y1) / 2 * k
            set_world(model, part, cx, cy)
            part['mesh'] = dict(origin=[0, 0], indices=[0, 2, 1, 1, 2, 3], uvs=[0, 0, 1, 0, 0, 1, 1, 1], verts=[-w_ / 2, -h_ / 2, w_ / 2, -h_ / 2, -w_ / 2, h_ / 2, w_ / 2, h_ / 2])
            set_part_image(model, part, img)
            if side == 'L':
                dim(model, part)
        br.close()
    # --- skeleton params as the V1 side models (values from mr_carrot_hand_side), head under the body
    reparent(model, head, body)
    hx, hy = wpos(model, head)
    set_world(model, head, hx, hy)
    for ch in head['children']:                           # the head a little toward where it faces, over the turned neck
        ch['transform']['trans'][0] += 17.0
    tpl = Model('mr_carrot_hand_side')
    names = {p['uuid']: n for n, p in tpl.parts.items()}
    for pname in ('Leg:: Front:: Hip', 'Leg:: Front:: Knee', 'Leg:: Front:: Foot', 'Leg:: Back:: Hip', 'Leg:: Back:: Knee', 'Leg:: Back:: Foot',
                  'Arm:: Front:: Swing', 'Arm:: Front:: Elbow', 'Arm:: Back:: Swing', 'Arm:: Back:: Elbow', 'Head:: Nod', 'Body:: Lean'):
        p = deepcopy(tpl.params[pname])
        p['uuid'] = model.uuid
        model.uuid += 1
        for b in p['bindings']:
            b['node'] = model.parts[names[b['node']]]['uuid']
        model.json['param'].append(p)
        model.params[pname] = p
    for n in list(model.clips):
        if not n.startswith('表情/'):
            model.clips.pop(n)
    uid = {p['uuid'] for p in model.json['param']}
    for clip in model.clips.values():
        clip['lanes'] = [l for l in clip['lanes'] if l['uuid'] in uid]
    walk(model)
    # (2026-11-14 使用者：「側面走路的跨腳太大了」) his thighs turn STRIDE_K of the shared angle; the body's walking dip follows the
    # smaller swing (1 - cos) so the planted foot stays on the ground (as male2_side3)
    if STRIDE_K != 1.0:
        hip = WALK_HIP_SHARED * STRIDE_K
        for pname in ('Leg:: Front:: Hip', 'Leg:: Back:: Hip'):
            for b in model.params[pname]['bindings']:
                b['values'] = [[q * STRIDE_K for q in row] for row in b['values']]
        for b in model.params['Body:: Walk Contact']['bindings']:
            b['values'] = [[q * (1 - math.cos(hip)) / (1 - math.cos(WALK_HIP_SHARED)) for q in row] for row in b['values']]
    # the far arm swings less: at V1's amplitude this wide forearm and hand showed between the legs
    clip = model.clips['動作/走路']
    for lane in clip['lanes']:
        if lane['uuid'] == model.params['Arm:: Back:: Swing']['uuid']:
            for kf in lane['keyframes']:
                kf['value'] = round(kf['value'] * .4, 6)
        # (2026-11-23) the near arm too: his wide rolled sleeve on a round belly flew out over the shoulder at the full V1 swing
        if lane['uuid'] == model.params['Arm:: Front:: Swing']['uuid']:
            for kf in lane['keyframes']:
                kf['value'] = round(kf['value'] * FRONT_SWING, 6)
    B.clean_transparent(model)
    B.gc_textures(model)
    model.json['meta'].update(name=title, artist=f'Claude (story_chubby/side.py on {front})')
    model.json['meta'].pop('storyArms', None)
    model.path = MODELS / f'{sid}.inp'
    model.save()
    joints = {'Body': list(wpos(model, body)), 'Head': list(wpos(model, head))}
    joints.update({n: list(wpos(model, node)) for n, node in J.items()})
    (MODELS / f'{sid}.joints.json').write_text(json.dumps(joints, ensure_ascii=False, indent=1), encoding='utf-8')
    print(model.path)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        build(sys.argv[1], sys.argv[2], title=sys.argv[3] if len(sys.argv) > 3 else '胖大叔說故事 v3・側面')
    else:
        build()
