"""《鞋匠與小矮人》V7 買鞋太太 shoe_lady_aubv3：茄子小姐 v3 換裝（2026-11-22）。

    python -X utf8 tools/shoe_v7/lady.py            -> inochi2D-demo/models/shoe_lady_aubv3.inp

底圖 carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝/shoe_lady_aubv3_底圖_v1.png（茄子小姐底圖原位換裝，使用者 11-22 確認）。
做法照 guinevere_aub/front.py：讀 mom_aubv3（茄子小姐 v4 臉＋長裙骨架，光頭素臉和 aubergine_hand_v3 逐像素相同），
每層照原網格換貼圖、綁定不動；形狀量自底圖（底圖 px，根座標 = (px-512, py-750)×1.3），上色一律 SVG 手繪：
  - 頭髮：深紫捲盤髮。長捲髮（馬尾_*、髮片_*）清空；後髮_短、瀏海_R／_L、鬢角_R／_L 依底圖重畫並換成新框網格，
    九軸、物理、Hair Off 的綁定從同一層舊網格內插（IDW）過來。瀏海_中、碎髮不用。
  - 胸腔：玫瑰紅高腰洋裝上身＋白蕾絲 V 領＋V 領露出的膚色；兩側原本給長髮墊底的髮色改透明。
  - 裙_中：玫瑰紅長裙、高腰下的碎褶，裙襬比媽媽短一點（露出鞋面）。
  - 袖子（上臂、下臂、揮手、舉手、講解、思考差分）：藍色與白袖口依亮度換玫瑰紅色階（泡泡袖＋同色收口袖口）。
  - 鞋：深色平底鞋。
  - 眉毛：茄子小姐原本的深紫眉，和髮色同系，不改；臉、五官一層都不動。
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (TOOLS, TOOLS / 'story_mix', TOOLS / 'guinevere_aub'):
    sys.path.insert(0, str(p))
import mix                                   # noqa: E402
import front as GF                           # noqa: E402  guinevere_aub/front.py（SVG、ramp、tex、put 小工具）
from build_story_trio import set_part_image  # noqa: E402

MID, SRC = 'shoe_lady_aubv3', 'mom_aubv3'
K = 1.3


def r2b(x, y):
    return x / K + 512, y / K + 750


def b2r(x, y):
    return (x - 512) * K, (y - 750) * K


# ============================================================================================ palette
ROSE = [(0, '#5e1422'), (.3, '#8e2a3a'), (.6, '#b94656'), (.85, '#d4636f'), (1, '#e98d93')]
ROSE_LINE = '#3e0c16'
HAIR = dict(dark='#1e1028', base='#33203f', mid='#4c3260', light='#6d4d86', hi='#a184b8', line='#120818')
SKIN = (231, 182, 176)


def render_base(P, inner, rbox, W, H):
    """inner svg drawn in BASE px, rendered over the root box rbox"""
    x0, y0 = r2b(rbox[0], rbox[1])
    x1, y1 = r2b(rbox[2], rbox[3])
    return P.render(inner, (x0, y0, x1, y1), W, H)


# ============================================================================================ hair
def hair_defs():
    return ('<defs>'
            + GF.grad('hb', [(0, HAIR['mid']), (.5, HAIR['base']), (1, HAIR['dark'])], 0, 0, 0, 1)
            + GF.grad('hf', [(0, HAIR['light']), (.45, HAIR['mid']), (1, HAIR['base'])], 0, 0, 0, 1)
            + GF.grad('hc', [(0, HAIR['mid']), (1, HAIR['dark'])], 0, 0, 1, 1)
            + '</defs>')


def _stroke(d, col, w, op=1.0):
    return f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>'


BACK = ('M512 4 C466 2 428 22 412 54 C398 82 396 116 402 140 C392 160 398 182 410 198 C404 214 410 236 428 242 '
        'C440 246 448 238 450 230 Q512 226 574 230 C576 238 584 246 596 242 C614 236 620 214 616 198 C628 180 632 158 622 138 C628 112 626 80 612 54 C596 22 558 2 512 4 Z')


def lobes(shapes, fill, w=2.4):
    """union of round curl lobes with one outline: every shape stroked first, then every shape filled on top"""
    out = ''.join(f'<path d="{d}" fill="none" stroke="{HAIR["line"]}" stroke-width="{2 * w}" stroke-linejoin="round"/>' for d in shapes)
    out += ''.join(f'<path d="{d}" fill="{fill}"/>' for d in shapes)
    return out


def circ(cx, cy, rx, ry=None):
    ry = ry or rx
    return f'M{cx - rx} {cy} a{rx} {ry} 0 1 0 {2 * rx} 0 a{rx} {ry} 0 1 0 {-2 * rx} 0 Z'


def swirl(cx, cy, r, sg=1):
    """a wave's soft highlight arc and one dark strand line"""
    return (_stroke(f'M{cx - sg * r * .55} {cy + r * .35} C{cx - sg * r * .7} {cy - r * .3} {cx - sg * r * .1} {cy - r * .75} {cx + sg * r * .45} {cy - r * .55}',
                    HAIR['light'], 3.2, .5)
            + _stroke(f'M{cx + sg * r * .2} {cy + r * .7} C{cx + sg * r * .7} {cy + r * .4} {cx + sg * r * .8} {cy - r * .1} {cx + sg * r * .6} {cy - r * .45}',
                      HAIR['dark'], 1.8, .55))


SIDE_LOBES = [(418, 84, 30), (410, 136, 28), (420, 186, 26)]
TOP_LOBES = [(484, 12, 34), (544, 12, 34)]


def back_svg():
    s = hair_defs()
    shapes = [BACK] + [circ(x, y, r) for x, y, r in SIDE_LOBES] + [circ(1024 - x, y, r) for x, y, r in SIDE_LOBES]         + [circ(x, y, r, r * .7) for x, y, r in TOP_LOBES]
    s += lobes(shapes, 'url(#hb)')
    for x, y, r in SIDE_LOBES:
        s += swirl(x, y, r, -1) + swirl(1024 - x, y, r, 1)
    return s


FRINGE_R = ('M516 8 C474 6 436 24 418 54 C402 80 398 114 404 140 C408 152 414 160 424 164 C428 150 432 140 440 132 '
            'C446 140 452 146 462 148 C470 130 482 108 498 88 C508 74 516 60 518 46 Z')
FRINGE_L = ('M514 8 C558 6 596 26 612 56 C626 84 628 116 620 140 C616 152 608 160 598 164 C596 148 590 132 584 118 '
            'C574 100 560 88 540 80 C528 76 520 66 518 46 Z')


def fringe_svg(side):
    s = hair_defs()
    if side == 'R':
        s += f'<path d="{FRINGE_R}" fill="url(#hf)" stroke="{HAIR["line"]}" stroke-width="2.4" stroke-linejoin="round"/>'
        # strands sweeping from the part down-left, roll at the temple
        for d, w, c, op in (('M512 40 C492 60 470 90 456 140', 2.2, HAIR['dark'], .7),
                            ('M500 14 C470 30 446 80 438 128', 2.0, HAIR['dark'], .6),
                            ('M480 12 C448 26 424 70 414 120', 2.0, HAIR['dark'], .55),
                            ('M496 50 C478 70 462 96 452 126', 4.5, HAIR['hi'], .55),
                            ('M470 22 C446 40 428 80 422 112', 3.5, HAIR['light'], .6),
                            ):
            s += _stroke(d, c, w, op)
    else:
        s += f'<path d="{FRINGE_L}" fill="url(#hf)" stroke="{HAIR["line"]}" stroke-width="2.4" stroke-linejoin="round"/>'
        for d, w, c, op in (('M520 44 C546 58 572 80 590 128', 2.2, HAIR['dark'], .7),
                            ('M530 14 C566 28 596 72 606 122', 2.0, HAIR['dark'], .6),
                            ('M532 50 C556 62 578 86 592 112', 4.5, HAIR['hi'], .5),
                            ('M556 20 C586 38 604 78 610 108', 3.5, HAIR['light'], .55),
                            ):
            s += _stroke(d, c, w, op)
    return s


LOCK = [(432, 128, 13), (444, 162, 13), (438, 194, 13), (450, 224, 12), (442, 250, 6)]   # (x, y, half width): S-wave lock along the cheek edge


def ribbon(pts, n=40):
    """closed outline of a lock: Catmull-Rom centreline with per-point half widths"""
    P = np.array(pts, float)
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    c, w = [], []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            q = .5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            c.append(q[:2])
            w.append(q[2])
    c.append(P[-2][:2])
    w.append(P[-2][2])
    c, w = np.array(c), np.array(w)
    d = np.gradient(c, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1) / np.maximum(1e-6, np.linalg.norm(d, axis=1))[:, None]
    L, R = c + nrm * w[:, None], c - nrm * w[:, None]
    pts = np.vstack([L, R[::-1]])
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + ' Z', c


def lock_svg(side):
    sg = -1 if side == 'R' else 1
    pts = [(x if sg < 0 else 1024 - x, y, w) for x, y, w in LOCK]
    d, c = ribbon(pts)
    s = hair_defs()
    s += f'<path d="{d}" fill="url(#hf)" stroke="{HAIR["line"]}" stroke-width="2.2" stroke-linejoin="round"/>'
    mid = 'M' + ' L'.join(f'{x - sg * 2:.1f} {y:.1f}' for x, y in c[8:-12:2])
    s += _stroke(mid, HAIR['hi'], 2.4, .5)
    return s


# ---------------------------------------------------------------- 2026-11-22 第二版頭髮：蓬鬆捲盤髮（hair_locks 規則手繪髮束）
# 統籌看對照圖：「頭髮像一頂紫色安全帽（瀏海平貼、整塊輪廓）」→ 照底圖量（底圖 px）：側分（分線約 (518,74)），
# 左半往畫面左上捲起、右半往後梳，額頭露出（髮際線 (455,138)→(518,76)→(585,135)）；後面是蓬鬆的盤髮外形；
# 兩側捲髮從耳前垂到下巴高度。髮束一律 hair_locks.Hair.lock（中心線＋葉形寬度、根深尖亮、一道高光、等寬外框）。
sys.path.insert(0, str(TOOLS / 'aubergine_story_v4'))
import hair_locks as HL                     # noqa: E402

HPAL = ('#1c0f26', '#2f1c3b', '#46305a', '#664a80', '#9c7fb4', HAIR['line'], HAIR['line'])
HAIRLINE = [(452, 150), (458, 136), (472, 116), (490, 99), (505, 86), (518, 76), (534, 78), (550, 86), (562, 100), (573, 118), (586, 136), (592, 150)]


def _H():
    return HL.Hair(HPAL)


def _defs(h):
    return '<defs>' + ''.join(h.defs) + '</defs>'


def _wave_outline(pts, amp=5.0, n=7):
    """a closed silhouette with soft scallops (big curls), not circles: every edge bulges outwards a little"""
    P = np.array(pts, float)
    c = P.mean(0)
    out = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        out.append(tuple(a))
        m = (a + b) / 2
        v = m - c
        out.append(tuple(m + v / (np.linalg.norm(v) + 1e-6) * amp))
    return HL.smooth(out)


def back_svg():
    h = _H()
    sil = [(512, 4), (556, 8), (592, 24), (614, 52), (624, 88), (620, 122), (610, 150), (602, 190), (596, 218), (578, 212),
           (566, 170), (512, 150), (458, 170), (446, 212), (428, 218), (422, 190), (412, 150), (404, 122), (406, 86), (418, 50),
           (440, 22), (474, 8)]
    d = _wave_outline(sil, 6)
    h.defs.append('<linearGradient id="bk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset=".55" stop-color="%s"/>'
                  '<stop offset="1" stop-color="%s"/></linearGradient>' % (HPAL[2], HPAL[1], HPAL[0]))
    cl = h.clip('bkc', d)
    body = f'<path d="{d}" fill="url(#bk)"/><g {cl}>'
    for r, c, t, w in (((512, 10), (462, 18), (420, 80), 34), ((512, 10), (562, 18), (608, 80), 34),
                       ((470, 30), (420, 70), (414, 150), 30), ((554, 30), (606, 70), (612, 150), 30),
                       ((444, 100), (414, 150), (436, 210), 24), ((584, 100), (614, 150), (592, 210), 24)):
        body += h.lock(HL.centre_quad(r, c, t), w, tone=1, shine=False)[0]
    body += '</g>' + f'<path d="{d}" fill="none" stroke="{HPAL[6]}" stroke-width="2.4" stroke-linejoin="round"/>'
    return _defs(h) + body


def fringe_svg(side):
    """the front hair over the scalp, from the skull's top down to the hairline, with the swept locks on it"""
    h = _H()
    if side == 'R':
        sil = [(522, -2), (486, 2), (452, 14), (424, 40), (408, 76), (404, 110), (410, 142), (426, 162), (444, 160)] + \
              [p for p in HAIRLINE if p[0] <= 518][::-1][:-1] + [(518, 76), (522, 60)]
        sil = [(522, -2), (486, 2), (452, 14), (424, 40), (408, 76), (404, 110), (410, 142), (426, 162), (446, 160),
               (452, 150), (458, 136), (472, 116), (490, 99), (505, 86), (518, 76), (522, 60)]
        locks = [((518, 74), (470, 36), (418, 92), 34, 1), ((520, 8), (466, 8), (424, 62), 30, 1), ((506, 86), (452, 72), (414, 134), 28, 0),
                 ((494, 98), (458, 104), (430, 156), 22, 0), ((478, 112), (452, 126), (446, 156), 16, 2)]
    else:
        sil = [(506, -2), (546, 2), (580, 14), (606, 40), (620, 76), (624, 110), (620, 142), (612, 160), (604, 156),
               (596, 136), (580, 116), (562, 100), (550, 86), (534, 78), (518, 76), (508, 60)]
        locks = [((518, 74), (562, 36), (610, 90), 32, 1), ((508, 8), (566, 8), (606, 60), 30, 1), ((536, 80), (584, 76), (614, 128), 26, 0),
                 ((552, 90), (590, 102), (612, 152), 20, 0), ((568, 104), (592, 120), (600, 150), 14, 2)]
    d = HL.smooth(sil)
    h.defs.append('<linearGradient id="fr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
                  '</linearGradient>' % (HPAL[1], HPAL[2]))
    cl = h.clip('frc', d)
    body = f'<path d="{d}" fill="url(#fr)"/><g {cl}>'
    for r, c, t, w, tone in locks:
        body += h.lock(HL.centre_quad(r, c, t), w, tone=tone)[0]
    body += '</g>' + f'<path d="{d}" fill="none" stroke="{HPAL[6]}" stroke-width="2.2" stroke-linejoin="round"/>'
    return _defs(h) + body


def lock_svg(side):
    """curly tendrils from in front of the ear down to the jaw (two wavy locks)"""
    h = _H()
    m = (lambda p: p) if side == 'R' else (lambda p: (1028 - p[0], p[1]))
    sg = 1 if side == 'R' else -1
    body = ''
    for r, c, t, w, amp, cyc, ph in (((438, 142), (414, 190), (450, 244), 16, 7, 1.4, 0.0), ((446, 152), (436, 200), (462, 238), 11, 5, 1.8, 1.2)):
        body += h.lock(HL.centre_quad(m(r), m(c), m(t), amp * sg, cyc, ph), w, tone=0)[0]
    return _defs(h) + body


HAIR_LAYERS = {   # name: (root box, svg fn, grid)
    '後髮_短': (b2r(374, -16) + b2r(650, 248), back_svg, (7, 7)),
    '瀏海_R': (b2r(394, 0) + b2r(522, 170), lambda: fringe_svg('R'), (6, 6)),
    '瀏海_L': (b2r(510, 0) + b2r(632, 170), lambda: fringe_svg('L'), (6, 6)),
    '鬢角_R': (b2r(396, 120) + b2r(470, 266), lambda: lock_svg('R'), (4, 6)),
    '鬢角_L': (b2r(558, 120) + b2r(632, 266), lambda: lock_svg('L'), (4, 6)),
}
CLEAR = ('馬尾_R', '馬尾_L', '瀏海_中', '馬尾梢_R', '馬尾梢_L', '髮片_L0', '髮片_L1', '髮片_R0', '髮片_R1', '髮片_R2', '碎髮_R', '碎髮_L')


def regrid(M, part, box, nx, ny):
    """new rectangular grid over box; every deform binding resampled (IDW) from the old mesh, other bindings kept"""
    P0 = mix.wverts(M, part)
    GF.grid(M, part, box, nx, ny)
    Q = mix.wverts(M, part)
    for prm in M.params.values():
        for b in prm['bindings']:
            if b['node'] != part['uuid'] or b['param_name'] != 'deform':
                continue
            out = mix._idw(P0, np.asarray(b['values'], float), Q)
            b['values'] = out.round(3).tolist()
            b['isSet'] = [[True] * out.shape[1] for _ in range(out.shape[0])]


def paint_hair(M, P):
    blank = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
    for n in CLEAR:
        if n in M.parts:
            set_part_image(M, M.parts[n], blank)
    for n, (box, fn, (nx, ny)) in HAIR_LAYERS.items():
        part = M.parts[n]
        regrid(M, part, box, nx, ny)
        W, H = int((box[2] - box[0]) * 2.4), int((box[3] - box[1]) * 2.4)
        set_part_image(M, part, render_base(P, fn(), box, W, H))
        part['opacity'] = 1


# ============================================================================================ torso
NECK = [(408, 290), (440, 274), (466, 262), (478, 258), (546, 258), (558, 262), (584, 274), (616, 290)]   # dress top edge
V = [(476, 258), (512, 336), (550, 258)]


def lace_outer():
    """scalloped outer edge of the V lace collar, base px"""
    pts = []
    L = [(414, 284), (424, 300), (446, 318), (470, 336), (494, 356), (512, 372)]
    R = [(1026 - x, y) for x, y in L[::-1]][1:]
    return L + R


def torso_svg():
    d = ('<defs>' + GF.grad('rose', [(0, '#7a2232'), (.25, '#a93a4a'), (.5, '#c24e5c'), (.75, '#a93a4a'), (1, '#6e1c2c')])
         + GF.grad('skin', [(0, '#e7b6b0'), (1, '#eec2ba')], 0, 0, 0, 1)
         + GF.grad('lace', [(0, '#f8efe6'), (1, '#e6d4c6')], 0, 0, 0, 1) + '</defs>')
    s = d + '<rect x="380" y="200" width="270" height="440" fill="url(#rose)"/>'
    # bust shading, princess seams, high waist seam (base y ~480) and the skirt's gathers under it
    s += _stroke('M470 400 Q490 430 512 432 Q534 430 554 400', '#7a2232', 3, .45)
    s += _stroke('M462 330 Q470 400 466 478 M562 330 Q554 400 558 478', '#7a2232', 2.2, .4)
    s += _stroke('M440 476 Q512 490 584 476', ROSE_LINE, 2.6, .8)
    s += _stroke('M440 480 Q512 494 584 480', '#d96a76', 2, .5)
    for x in range(452, 580, 18):
        s += _stroke(f'M{x} 488 Q{x + (x - 512) * .05} 560 {x + (x - 512) * .12} 640', '#6e1c2c', 1.6, .3)
    s += '<path d="M470 300 Q474 380 478 470" stroke="#e98d93" stroke-width="6" fill="none" opacity=".25" stroke-linecap="round"/>'
    # V neck skin
    s += f'<path d="M{V[0][0]} {V[0][1]} L{V[1][0]} {V[1][1]} L{V[2][0]} {V[2][1]} Z" fill="url(#skin)"/>'
    s += _stroke('M500 300 Q512 306 524 300', '#c98d86', 1.6, .6)
    s += _stroke('M488 284 Q498 290 506 290 M518 290 Q526 290 536 284', '#d09a92', 1.4, .5)
    # lace collar: from the dress top edge to the scalloped outer edge, V opening inside
    out = lace_outer()
    poly = 'M' + ' L'.join(f'{x} {y}' for x, y in NECK[:3]) + f' L{V[0][0]} {V[0][1]} L{V[1][0]} {V[1][1]} L{V[2][0]} {V[2][1]} ' \
        + ' L'.join(f'{x} {y}' for x, y in NECK[-3:])
    sc = ''
    for (x0, y0), (x1, y1) in zip(out[::-1][:-1], out[::-1][1:]):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        nx, ny = (y1 - y0), -(x1 - x0)
        L_ = max(1e-3, (nx * nx + ny * ny) ** .5)
        sc += f' Q{mx - nx / L_ * 9:.1f} {my - ny / L_ * 9:.1f} {x1} {y1}'
    lace = poly + f' L{out[-1][0]} {out[-1][1]}' + sc + ' Z'
    s += f'<path d="{lace}" fill="url(#lace)" stroke="#a88a7c" stroke-width="1.8" stroke-linejoin="round"/>'
    # lace pattern: rows of little rings and flowers
    for t in np.linspace(.12, .9, 7):
        for sgn in (-1, 1):
            x = 512 + sgn * (40 + 60 * (1 - t))
            y = 280 + 70 * t
            s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="none" stroke="#c4a698" stroke-width="1.3"/>'
            s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4" fill="#c4a698"/>'
    for t in np.linspace(.05, .95, 9):
        for sgn in (-1, 1):
            x = 512 + sgn * (18 + 80 * (1 - t))
            y = 300 + 62 * t
            s += f'<path d="M{x - 3:.1f} {y:.1f} q3 -4 6 0 q-3 4 -6 0" fill="none" stroke="#cdb3a6" stroke-width="1"/>'
    s += _stroke(f'M{V[0][0]} {V[0][1]} L{V[1][0]} {V[1][1]} L{V[2][0]} {V[2][1]}', '#8a6a5c', 1.6, .8)
    return s


def paint_torso(M, P):
    n = '胸腔'
    t = GF.tex(M, n).astype(float)
    H, W = t.shape[:2]
    box = mix.wbox(M, M.parts[n])
    a = t[..., 3] > 128
    flat = (np.abs(t[..., :3] - [74, 38, 22]).max(-1) <= 3) & a          # long-hair underlay: no long hair any more
    g = a & ~flat
    lab, k = ndi.label(g)
    g = lab == (1 + np.argmax(ndi.sum(g, lab, range(1, k + 1))))
    g = ndi.binary_fill_holes(g)
    # dress top edge (neckline / shoulders): nothing above it
    ppu = W / (box[2] - box[0])
    top = Image.new('L', (W, H), 0)
    poly = [b2r(x, y) for x, y in NECK] + [b2r(640, 572), b2r(384, 572)]
    ImageDraw.Draw(top).polygon([((x - box[0]) * ppu, (y - box[1]) * ppu) for x, y in poly], fill=255)
    below = np.asarray(top) > 128
    # the shoulders between the yoke and the sleeves: fill out to the upper arms' inner edge (no hair there now)
    shoulder = Image.new('L', (W, H), 0)
    sp = [b2r(x, y) for x, y in ((408, 290), (440, 274), (466, 262), (558, 262), (584, 274), (616, 290), (612, 400), (414, 400))]
    ImageDraw.Draw(shoulder).polygon([((x - box[0]) * ppu, (y - box[1]) * ppu) for x, y in sp], fill=255)
    # the bodice silhouette drawn from the base (shoulders, armpits, high waist, the skirt's gathered top)
    bod = Image.new('L', (W, H), 0)
    bp = [b2r(x, y) for x, y in ((406, 292), (440, 274), (466, 262), (558, 262), (584, 274), (618, 292), (616, 330),
                                 (596, 372), (584, 430), (574, 480), (598, 572), (426, 572), (450, 480), (440, 430),
                                 (428, 372), (408, 330))]
    ImageDraw.Draw(bod).polygon([((x - box[0]) * ppu, (y - box[1]) * ppu) for x, y in bp], fill=255)
    g = (np.asarray(bod) > 128) & below
    soft = ndi.gaussian_filter(g.astype(float), .7)
    art = np.asarray(render_base(P, torso_svg(), box, W, H)).astype(float)
    dist = ndi.distance_transform_edt(g)
    ol = np.clip(1 - (dist - .5) / 2.2, 0, 1) * .8
    bx = box[0] + (np.arange(W)[None, :] + .5) / ppu
    by = box[1] + (np.arange(H)[:, None] + .5) / ppu
    nx0, ny0 = b2r(468, 300)
    nx1, _ = b2r(556, 0)
    neck = (bx > nx0) & (bx < nx1) & (by < ny0)
    ol = np.where(neck, 0, ol)
    col = art[..., :3] * (1 - ol[..., None]) + np.array(GF.hexrgb(ROSE_LINE)) * ol[..., None]
    out = np.zeros_like(t)
    out[..., :3] = col
    out[..., 3] = soft * 255
    GF.put(M, n, out)


# ============================================================================================ skirt
HEM_Y = b2r(0, 1440)[1]        # 只用來算明暗的裙長（裙襬形狀沿用 mom_aubv3；改短會露出鞋層上方的方塊）


def paint_skirt(M):
    n = '裙_中'
    t = GF.tex(M, n).astype(float)
    H, W = t.shape[:2]
    on = t[..., 3] > 128
    box = mix.wbox(M, M.parts[n])
    ppu = W / (box[2] - box[0])
    yy = box[1] + (np.arange(H)[:, None] + .5) / ppu
    L = np.full(H, np.nan)
    R = np.full(H, np.nan)
    for r in range(H):
        c = np.where(on[r])[0]
        if len(c):
            L[r], R[r] = c[0], c[-1]
    rows = np.arange(H)
    ok = ~np.isnan(L)
    L = np.interp(rows, rows[ok], L[ok])
    R = np.interp(rows, rows[ok], R[ok])
    u = np.clip((np.arange(W)[None, :] - L[:, None]) / np.maximum(1, (R - L)[:, None]), 0, 1)
    xs = box[0] + (np.arange(W) + .5) / ppu
    hem = HEM_Y + 10 * np.cos(np.pi * xs / 360) ** 2 - 8 + 5 * np.sin(2 * np.pi * xs / 120)
    keep = ndi.binary_fill_holes(on)
    down = np.clip((yy - box[1]) / (HEM_Y - box[1]), 0, 1)
    light = .40 + .45 * np.exp(-((u - .42) / .32) ** 2)
    folds = np.sin(2 * np.pi * (u * 7.0 + .1)) * (.06 + .10 * down)
    light = np.clip(light + folds - .2 * np.clip(1 - (yy - box[1]) / 90, 0, 1), 0, 1)
    col = GF.ramp(ROSE, light)
    for uc in np.linspace(.08, .92, 12):
        lw = np.exp(-((u - uc) * (R - L)[:, None] / 1.6) ** 2) * np.clip((yy - box[1]) / 300, .15, 1) * .3
        col = col * (1 - lw[..., None]) + GF.hexrgb('#5e1422') * lw[..., None]
    dist = ndi.distance_transform_edt(keep)
    ol = np.clip(1 - (dist - 1) / 2.4, 0, 1) * .85
    col = col * (1 - ol[..., None]) + GF.hexrgb(ROSE_LINE) * ol[..., None]
    out = t.copy()
    out[..., :3] = col
    filled = ndi.binary_fill_holes(on)
    out[..., 3] = np.where(ndi.binary_erosion(filled, iterations=3), 255, out[..., 3])   # pin-holes left at the old apron's tip
    GF.put(M, n, out)


# ============================================================================================ sleeves, shoes
def recolor_sleeve(arr):
    rgb = arr[..., :3].astype(float)
    h, s, v = GF.hsv_of(rgb)
    al = arr[..., 3] > 0
    blue = (h > .5) & (h < .78) & (s > .1) & al
    white = (s < .12) & (v > .78) & al                     # the white cuff
    brown = (h < .12) & (s > .35) & (v < .5) & al          # long-hair specks along the sleeve
    skin = (h < .065) & (s > .12) & (s < .45) & (v > .7) & al
    white &= ~skin
    cream = (h > .07) & (h < .2) & (s < .35) & (v > .55) & al & ~skin
    white |= cream
    out = arr.astype(float).copy()
    lum = (rgb * [.299, .587, .114]).sum(-1) / 255
    if blue.sum() > 30:
        lo, hi = np.percentile(lum[blue], 2), np.percentile(lum[blue], 98)
        out[..., :3][blue] = GF.ramp(ROSE, np.clip((lum - lo) / max(1e-3, hi - lo) * .9 + .05, 0, 1))[blue]
    if white.sum() > 10:
        out[..., :3][white] = GF.ramp(ROSE, np.clip((lum - .6) / .4 * .55 + .15, 0, 1))[white]
    out[..., 3][brown] = 0
    # the spiky edge (long-hair tips drawn into the sleeve): opening with a disc, cloth only (hands untouched)
    near_skin = ndi.binary_dilation(skin, iterations=4)
    cloth = (out[..., 3] > 0) & ~near_skin
    yy, xx = np.mgrid[-7:8, -7:8]
    disc = xx * xx + yy * yy <= 49
    opened = ndi.binary_opening(out[..., 3] > 100, structure=disc, iterations=1)
    opened = ndi.binary_dilation(opened, iterations=1)
    cut = cloth & ~opened
    out[..., 3][cut] = 0
    keep = out[..., 3] > 0
    lab, k = ndi.label(keep)
    if k > 1:
        sz = ndi.sum(keep, lab, range(1, k + 1))
        out[..., 3][np.isin(lab, 1 + np.where(sz < 300)[0])] = 0
    return out, int(blue.sum() + white.sum())


def smooth_outer(arr, outer, repaint=True):
    """(上臂) the outer edge's bumps (long-hair tips drawn into the sleeve) trimmed: per row, the outer edge is pushed to a
    running 75th percentile of the edge positions (bumps stick out for a few rows only)"""
    a = arr[..., 3] > 100
    H, W = a.shape
    e = np.full(H, np.nan)
    for r in range(H):
        c = np.where(a[r])[0]
        if len(c):
            e[r] = c[0] if outer < 0 else W - 1 - c[-1]
    ok = ~np.isnan(e)
    if ok.sum() < 20:
        return arr
    rows = np.arange(H)
    e = np.interp(rows, rows[ok], e[ok])
    s = ndi.percentile_filter(e, 80, size=31)
    s = ndi.uniform_filter1d(s, 9)
    cols = np.arange(W)[None, :]
    lim = (cols - s[:, None] + .5) if outer < 0 else ((W - 1 - cols) - s[:, None] + .5)
    h, sat, v = GF.hsv_of(arr[..., :3].astype(float))
    skin = (h < .065) & (sat > .12) & (sat < .5) & (v > .65) & a
    m = a & (lim > 0) & ~skin
    m = ndi.binary_opening(m, iterations=2)
    lab, k = ndi.label(m)
    if k > 1:
        m = lab == (1 + np.argmax(ndi.sum(m, lab, range(1, k + 1))))
    m = ndi.binary_fill_holes(m)
    soft = np.clip(ndi.gaussian_filter(m.astype(float), .8) * 1.6 - .3, 0, 1)
    # repaint: per row, light across the sleeve (cylinder), outline inside the edge
    Lr, Rr = np.zeros(H), np.zeros(H)
    for r in range(H):
        c = np.where(m[r])[0]
        Lr[r], Rr[r] = (c[0], c[-1]) if len(c) else (0, 1)
    u = np.clip((cols - Lr[:, None]) / np.maximum(1, (Rr - Lr)[:, None]), 0, 1)
    if outer > 0:
        u = 1 - u
    light = np.clip(.3 + .55 * np.exp(-((u - .32) / .28) ** 2), 0, 1)
    col = GF.ramp(ROSE, light)
    dist = ndi.distance_transform_edt(m)
    ol = np.clip(1 - (dist - .5) / 2.2, 0, 1) * .85
    col = col * (1 - ol[..., None]) + np.array(GF.hexrgb(ROSE_LINE)) * ol[..., None]
    out = arr.astype(float).copy()
    if repaint:
        out[..., :3] = np.where(m[..., None], col, out[..., :3])
        out[..., 3] = np.where(skin, out[..., 3], soft * 255)
    else:
        out[..., 3] = np.where(skin, out[..., 3], np.minimum(out[..., 3], soft * 255))
    return out


def paint_sleeves(M):
    log = {}
    for n, p in M.parts.items():
        if p.get('type') != 'Part' or n in ('胸腔', '裙_中') or M.parents[p['uuid']]['name'] != 'Body':
            continue
        if n.startswith(('鞋_', '大腿', '小腿', '影子')):
            continue
        out, k = recolor_sleeve(GF.tex(M, n))
        if k and (n.startswith(('上臂_', '舉手上臂_上臂_', '揮手上臂_')) or n == '故事差分_揮手袖_R'):
            out = smooth_outer(out, -1 if n.endswith('_R') else 1)
        elif k and n.startswith('下臂_'):
            out = smooth_outer(out, -1 if n.endswith('_R') else 1, repaint=False)
        if k:
            GF.put(M, n, out)
            log[n] = k
    return log


def paint_shoes(M):
    for n in ('鞋_R', '鞋_L'):
        t = GF.tex(M, n).astype(float)
        al = t[..., 3] > 0
        lum = (t[..., :3] * [.299, .587, .114]).sum(-1) / 255
        lo, hi = np.percentile(lum[al], 2), np.percentile(lum[al], 99)
        tt = np.clip((lum - lo) / max(1e-3, hi - lo), 0, 1)
        new = GF.ramp([(0, '#120c10'), (.5, '#2c2228'), (.85, '#4a3c44'), (1, '#8a7c84')], tt)
        t[..., :3][al] = new[al]
        GF.put(M, n, t)


# ============================================================================================ main
def build():
    M = mix.load(SRC)
    with GF.SVG() as P:
        paint_hair(M, P)
        paint_torso(M, P)
        paint_skirt(M)
        sl = paint_sleeves(M)
        paint_shoes(M)
    sys.path.insert(0, str(TOOLS / 'story_carol_side'))
    import side as CS
    CS.dome_top(M, M.parts['脖子'])
    meta = M.json['meta']
    meta['name'] = '買鞋太太（茄子小姐 v3）'
    meta['artist'] = 'Claude (tools/shoe_v7/lady.py on mom_aubv3)'
    meta['shoeV7'] = {'date': '2026-11-22', 'src': SRC, 'base': 'carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝/shoe_lady_aubv3_底圖_v1.png'}
    path = mix.save(M, MID)
    print(path, 'sleeves', len(sl))
    return path


if __name__ == '__main__':
    build()
