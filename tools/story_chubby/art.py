"""胖大叔 chubby_hand_v3：全部部件的手繪 SVG（乾淨畫法：平滑漸層、等寬線、分層高光與陰影；2026-11-23）。
座標＝工作底圖 px（psd-create/images/chubby_hand_v3/base.png，1024×1536，prep.py）。
輪廓形狀取自 measure.py（measure.json，只量形狀）或照底圖手量的點；臉、眼、眉、鼻、嘴、耳、八字鬍取自 face.py（face_trace.json）；
表情取自 expr.py。顏色、陰影、皺褶、扣子、吊帶、髮絲全部在這裡手畫，不取底圖像素。左右成對的四肢、吊帶只畫角色右側（畫面左），
建模時對 x = AXIS 鏡像。架構照 story_boy/art.py、story_burly/art.py（只讀參考；共用小工具從 story_boy/art.py 匯入，不改它）。

    scene() -> {群組 id: '<g id=...>…</g>'}
    python -X utf8 inochi2D-demo/tools/story_chubby/art.py   -> 角色工坊/輸出/胖大叔/手繪總覽.png、手繪對照.jpg

換裝（麵包師傅 baker.py）用 OUTFIT 換掉身體幾組（襯衫、袖子、褲頭…）的畫法，臉和頭不變。
"""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('boy_art_helpers', HERE.parent / 'story_boy/art.py')
BA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BA)
G, path, curve_d, curve_pts, poly_d, crescent, shape, f = BA.G, BA.path, BA.curve_d, BA.curve_pts, BA.poly_d, BA.crescent, BA.shape, BA.f

M = json.loads((HERE / 'measure.json').read_text(encoding='utf-8'))
M['hair_locks'] = []          # 頭髮兩層＋九軸＋擺動（不另拆髮束圖層）
_TP = HERE / 'face_trace.json'
TRACE = json.loads(_TP.read_text(encoding='utf-8')) if _TP.exists() else None
AXIS = M['_axis']          # 513.5
MIRROR = f'translate({2 * AXIS} 0) scale(-1 1)'


def mir(pts):
    return [(2 * AXIS - x, y) for x, y in pts]


# ---- colours ----
SKIN, SKIN_L, SKIN_D, SKIN_DD, SKIN_LINE = '#fbd8c2', '#fde6d6', '#f0c0a6', '#dc9c84', '#7a4a3a'
SHIRT, SHIRT_L, SHIRT_D, SHIRT_DD, SHIRT_LINE = '#f6f0dc', '#fffbee', '#e3d8bc', '#cdbf9e', '#4a3c30'
PANTS, PANTS_L, PANTS_D, PANTS_LINE = '#8a6848', '#9c7a56', '#6c5034', '#3a2818'
STRAP, STRAP_L, STRAP_D = '#5a463c', '#7a6458', '#3a2c26'
METAL, METAL_L, METAL_D = '#b9b6b0', '#e8e6e2', '#7d7a74'
SHOE, SHOE_L, SHOE_D, SHOE_LINE = '#5a4036', '#7a5a4c', '#3c2a22', '#1e140f'
HAIR, HAIR_L, HAIR_D, HAIR_LINE = '#7a5a46', '#9a785e', '#5a3f30', '#2e1f17'
INK = '#2a1a14'

# =================================================================== joints (base px, character right = image left)
S_ARM, E_ARM, W_ARM = (292.0, 462.0), (222.0, 712.0), (182.0, 876.0)

# =================================================================== arms
UPPER_R = [(372, 380), (345, 392), (318, 407), (290, 425), (265, 450), (245, 480), (230, 515), (216, 555), (200, 590), (182, 612), (168, 628),
           (160, 648), (156, 670), (160, 688), (175, 700), (210, 716), (245, 731), (272, 742), (284, 728), (288, 700), (292, 660), (298, 615),
           (305, 560), (318, 500), (335, 450), (355, 410)]
CUFF_TOP = [(166, 630), (200, 646), (240, 664), (292, 690)]
FORE_R = [(157, 682), (176, 697), (210, 713), (245, 728), (271, 739), (274, 752), (262, 770), (250, 792), (236, 818), (226, 850), (222, 882),
          (140, 886), (141, 850), (146, 810), (150, 770), (153, 730), (155, 700)]
SHOULDER, ELBOW, WRIST = S_ARM, E_ARM, W_ARM


def sleeve(colors=None):
    """捲到手肘的米白袖子：上半是袖管、下半是捲起的袖口（兩層布邊）"""
    c = colors or dict(fill=SHIRT, light=SHIRT_L, dark=SHIRT_D, deep=SHIRT_DD, line=SHIRT_LINE)
    g = G('upper')
    d = curve_d(UPPER_R, True, 6)
    fill = g.lin(156, 0, 372, 0, [(0, c['dark']), (.25, c['fill']), (.6, c['light']), (1, c['fill'])])
    b = g.blur(4)
    cuff = poly_d(curve_pts(CUFF_TOP, False, 6) + [(300, 760), (140, 760)])
    cf = g.lin(150, 0, 300, 0, [(0, c['dark']), (.4, c['light']), (1, c['fill'])])
    ins = (f'<path d="{crescent((250, 470), (226, 540), (196, 600), 10)}" fill="{c["dark"]}" opacity=".55" filter="{b}"/>'
           f'<path d="{crescent((300, 520), (292, 580), (286, 650), -9)}" fill="{c["deep"]}" opacity=".45" filter="{b}"/>'
           f'<path d="M262 486 Q252 530 246 580 M282 520 Q270 560 262 610" fill="none" stroke="{c["deep"]}" stroke-width="3" stroke-linecap="round" opacity=".55" filter="{g.blur(1.2)}"/>'
           f'<path d="{cuff}" fill="{cf}"/>'
           f'<path d="{curve_d([(x, y + 22) for x, y in CUFF_TOP], False, 6)}" fill="none" stroke="{c["deep"]}" stroke-width="2" opacity=".6"/>'
           f'<path d="{crescent((180, 672), (230, 694), (282, 716), 6)}" fill="{c["dark"]}" opacity=".5" filter="{g.blur(2)}"/>'
           f'<path d="{curve_d(CUFF_TOP, False, 6)}" fill="none" stroke="{c["line"]}" stroke-width="2.2"/>')
    shape(g, d, fill, c['line'], 2.4, ins)
    return g


def forearm():
    """袖口露出的肉肉前臂（上端畫長，伸進袖口裡；T19：前臂在上臂前面時袖口邊線由上臂蓋住）"""
    g = G('forearm')
    d = curve_d(FORE_R, True, 6)
    fill = g.lin(138, 0, 278, 0, [(0, SKIN_D), (.3, SKIN), (.62, SKIN_L), (1, SKIN_D)])
    b = g.blur(4)
    ins = (f'<path d="{crescent((170, 730), (156, 800), (148, 870), -7)}" fill="{SKIN_D}" opacity=".6" filter="{b}"/>'
           f'<path d="M180 700 L280 740 L280 760 L170 726Z" fill="{SKIN_DD}" opacity=".45" filter="{b}"/>')
    c = g.clip(d)
    g.add(path(d, fill) + f'<g clip-path="{c}">{ins}</g>')
    g.add(path(d, 'none', SKIN_LINE, 2.2))
    return g


def hand():
    g = G('hand')
    d = curve_d(M['hand'][::2], True, 3)
    fill = g.lin(134, 0, 224, 0, [(0, SKIN_D), (.3, SKIN), (.6, SKIN_L), (1, SKIN_D)])
    b = g.blur(3.5)
    ins = (f'<path d="M136 846 L224 846 L222 876 Q180 886 138 876Z" fill="{SKIN_DD}" opacity=".45" filter="{b}"/>'
           f'<path d="M168 930 Q172 950 168 968 M184 926 Q190 946 186 964" fill="none" stroke="{SKIN_LINE}" stroke-width="1.3" stroke-linecap="round" opacity=".6"/>'
           f'<path d="M204 900 Q212 914 210 930" fill="none" stroke="{SKIN_D}" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>')
    shape(g, d, fill, SKIN_LINE, 2.0, ins)
    return g


# =================================================================== legs
def leg_inner(g, pts=None, colors=None):
    c = colors or dict(fill=PANTS, light=PANTS_L, dark=PANTS_D, line=PANTS_LINE)
    d = curve_d((pts or M['leg'])[::3], True, 4)
    fill = g.lin(286, 0, 514, 0, [(0, c['dark']), (.2, c['fill']), (.5, c['light']), (.8, c['fill']), (1, c['dark'])])
    b = g.blur(5)
    folds = ''.join(f'<path d="{crescent(a, m, e, t)}" fill="{c["dark"]}" opacity="{o}"/>' for a, m, e, t, o in (
        ((496, 960), (460, 1000), (420, 1030), 7, .5), ((330, 1180), (390, 1200), (470, 1180), 8, .6),
        ((336, 1330), (400, 1350), (462, 1330), 8, .6), ((340, 1250), (400, 1262), (466, 1250), 5, .4)))
    ins = (f'<path d="M330 1300 Q400 1360 470 1300 L470 1400 L325 1400Z" fill="{c["dark"]}" opacity=".3" filter="{b}"/>'
           f'<path d="M392 860 Q388 1100 396 1380" fill="none" stroke="{c["line"]}" stroke-width="1.4" opacity=".5"/>'
           f'<path d="M370 900 Q362 1060 370 1220" fill="none" stroke="{c["light"]}" stroke-width="12" stroke-linecap="round" opacity=".35" filter="{b}"/>'
           + folds)
    cl = g.clip(d)
    return f'<path d="{d}" fill="{fill}"/><g clip-path="{cl}">{ins}</g>' + path(d, 'none', c['line'], 2.2)


def leg_window(name, y0, y1, colors=None):
    g = G(name)
    c = g.clip(f'M260 {y0}H530V{y1}H260Z')
    g.add(f'<g clip-path="{c}">{leg_inner(g, colors=colors)}</g>')
    return g


def pants_top(colors=None):
    """褲頭（兩條腿上段＋胯下，蓋住大腿頂端的接縫）"""
    c = colors or dict(fill=PANTS, light=PANTS_L, dark=PANTS_D, line=PANTS_LINE)
    g = G('pants_top')
    cl = g.clip('M270 800H760V960H270Z')
    fill = g.lin(290, 0, 737, 0, [(0, c['dark']), (.2, c['fill']), (.5, c['light']), (.8, c['fill']), (1, c['dark'])])
    g2 = G('pants_top_m')
    left = leg_inner(g, colors=colors)
    right = leg_inner(g2, colors=colors)
    g.defs += g2.defs
    g.add(f'<g clip-path="{cl}"><path d="M292 800H735V900H292Z" fill="{fill}"/>{left}<g transform="{MIRROR}">{right}</g>'
          f'<path d="M{AXIS} 850V960" fill="none" stroke="{c["line"]}" stroke-width="1.6"/>'
          f'<path d="M300 850 Q318 900 326 950 M{2 * AXIS - 300} 850 Q{2 * AXIS - 318} 900 {2 * AXIS - 326} 950" fill="none" stroke="{c["line"]}" stroke-width="1.8"/>'
          f'<path d="M{AXIS - 16} 856 Q{AXIS - 18} 900 {AXIS} 916" fill="none" stroke="{c["dark"]}" stroke-width="1.6"/></g>')
    return g


def boot():
    g = G('boot')
    pts = M['boot']
    d = curve_d(pts[::3], True, 3)
    fill = g.lin(280, 0, 466, 0, [(0, SHOE_D), (.3, SHOE), (.55, SHOE_L), (.8, SHOE), (1, SHOE_D)])
    b = g.blur(4)
    lace = ''
    for i in range(3):
        y = 1404 + i * 13
        lace += f'<path d="M{356 + i * 2} {y} L{404 - i * 2} {y + 9} M{404 - i * 2} {y} L{356 + i * 2} {y + 9}" fill="none" stroke="{SHOE_LINE}" stroke-width="2" stroke-linecap="round"/>'
    ins = (f'<path d="M300 1440 Q290 1470 296 1486" fill="none" stroke="{SHOE_L}" stroke-width="8" stroke-linecap="round" opacity=".55" filter="{b}"/>'
           f'<ellipse cx="318" cy="1452" rx="22" ry="9" fill="{SHOE_L}" opacity=".55" filter="{b}"/>'
           f'<path d="M282 1484 Q380 1498 466 1480 L466 1510 L280 1510Z" fill="{SHOE_LINE}"/>'
           f'<path d="M296 1440 Q340 1430 372 1446" fill="none" stroke="{SHOE_D}" stroke-width="2" opacity=".8"/>'
           + lace)
    shape(g, d, fill, SHOE_LINE, 2.2, ins)
    return g


# =================================================================== torso
CHEST_R = [(AXIS, 452), (497, 428), (478, 402), (458, 376), (440, 358), (418, 352), (395, 362), (372, 378), (345, 392), (322, 410), (306, 450),
           (299, 510), (296, 570), (292, 630), (287, 690), (284, 745), (288, 782), (306, 800), (350, 812), (410, 818), (470, 821), (AXIS, 822)]
BUTTONS = [476, 552, 627, 708, 786]


def chest(colors=None):
    """襯衫軀幹（啤酒肚）：中間門襟、扣子、肚子的圓弧陰影和皺褶；脖子 V 領口挖空（脖子層在後面）"""
    c = colors or dict(fill=SHIRT, light=SHIRT_L, dark=SHIRT_D, deep=SHIRT_DD, line=SHIRT_LINE)
    g = G('shirt')
    pts = CHEST_R + mir(CHEST_R[1:-1])[::-1]
    d = curve_d(pts, True, 5)
    fill = g.lin(284, 0, 743, 0, [(0, c['dark']), (.18, c['fill']), (.45, c['light']), (.7, c['fill']), (1, c['dark'])])
    b = g.blur(9)
    A = AXIS
    belly = (f'<ellipse cx="{A}" cy="660" rx="200" ry="150" fill="{c["light"]}" opacity=".55" filter="{b}"/>'
             f'<path d="M300 700 Q{A} 860 {2 * A - 300} 700 L{2 * A - 280} 830 L280 830Z" fill="{c["dark"]}" opacity=".55" filter="{b}"/>'
             f'<path d="M296 520 Q330 640 300 760 L284 760 L284 520Z" fill="{c["deep"]}" opacity=".5" filter="{b}"/>'
             f'<path d="M{2 * A - 296} 520 Q{2 * A - 330} 640 {2 * A - 300} 760 L{2 * A - 284} 760 L{2 * A - 284} 520Z" fill="{c["deep"]}" opacity=".5" filter="{b}"/>'
             f'<path d="M420 590 Q460 584 500 588 M{2 * A - 420} 590 Q{2 * A - 460} 584 {2 * A - 500} 588" fill="none" stroke="{c["deep"]}" stroke-width="3" stroke-linecap="round" opacity=".55" filter="{g.blur(1.5)}"/>'
             f'<path d="M330 760 Q360 790 400 800 M{2 * A - 330} 760 Q{2 * A - 360} 790 {2 * A - 400} 800" fill="none" stroke="{c["deep"]}" stroke-width="3" stroke-linecap="round" opacity=".5" filter="{g.blur(1.5)}"/>'
             f'<path d="M{A - 11} 450 V818" fill="none" stroke="{c["line"]}" stroke-width="1.6" opacity=".8"/>')
    if not colors or colors.get('buttons', True):
        belly += ''.join(f'<circle cx="{A + 1}" cy="{y}" r="5.4" fill="{c["light"]}" stroke="{c["line"]}" stroke-width="1.8"/>'
                         f'<circle cx="{A + 1}" cy="{y}" r="1.6" fill="{c["line"]}" opacity=".6"/>' for y in BUTTONS)
    shape(g, d, fill, c['line'], 2.4, belly)
    return g


NECK_X0, NECK_X1 = AXIS - 52.0, AXIS + 52.0
NECK_TOP, NECK_DOME, NECK_BOT = 296.0, 330.0, 462.0


def neck():
    """（標準脖子，胖的脖子粗一點）比臉窄的圓柱、平塗膚色、頂端圓頂沒有橫線；上端伸進下巴後面，下端伸進領口"""
    g = G('neck')
    x0, x1 = NECK_X0, NECK_X1
    fill = g.lin(x0, 0, x1, 0, [(0, '#f2c4aa'), (.22, SKIN), (.5, '#fcdcc8'), (.78, SKIN), (1, '#f2c4aa')])
    d = (f'M{f(x0)} {f(NECK_DOME)} C{f(x0)} {f(NECK_TOP - 8)} {f(x1)} {f(NECK_TOP - 8)} {f(x1)} {f(NECK_DOME)} '
         f'L{f(x1 + 4)} {f(NECK_BOT)} L{f(x0 - 4)} {f(NECK_BOT)}Z')
    sides = f'M{f(x0 + .9)} 380 L{f(x0 - 1)} 430 M{f(x1 - .9)} 380 L{f(x1 + 1)} 430'
    g.add(path(d, fill) + path(sides, 'none', SKIN_D, 1.3, .5))
    return g


def neck_shadow():
    """下巴陰影（獨立一層，以脖子當遮罩、跟著頭走）：雙下巴下面的粉色陰影"""
    g = G('neck_shadow')
    chin = TRACE['face']['chin'] if TRACE else 370.0
    d = f'M{AXIS - 62} {chin - 24} Q{AXIS} {chin + 2} {AXIS + 62} {chin - 24} L{AXIS + 62} {chin + 18} Q{AXIS} {chin + 40} {AXIS - 62} {chin + 18}Z'
    g.add(f'<path d="{d}" fill="#d9907e" opacity=".6" filter="{g.blur(5)}"/>')
    return g


COLLAR_R = [(422, 334), (412, 358), (418, 388), (426, 418), (434, 447), (452, 422), (470, 401), (482, 406), (496, 426), (512, 448),
            (500, 418), (486, 398), (468, 382), (450, 366), (436, 350), (430, 334)]


def collar(front, colors=None):
    """襯衫領：後片（脖子後面看得到的領子內側）在脖子下面，前片（兩片尖領）在脖子上面，喉嚨中間透明"""
    c = colors or dict(fill=SHIRT, light=SHIRT_L, dark=SHIRT_D, deep=SHIRT_DD, line=SHIRT_LINE)
    g = G('collar_front' if front else 'collar_back')
    A = AXIS
    if not front:
        d = f'M{A - 92} 360 Q{A - 80} 330 {A - 40} 322 Q{A} 316 {A + 40} 322 Q{A + 80} 330 {A + 92} 360 L{A + 60} 380 L{A - 60} 380Z'
        fill = g.lin(0, 316, 0, 380, [(0, c['dark']), (1, c['deep'])])
        g.add(path(d, fill, c['line'], 1.8))
        return g
    fill = g.lin(0, 330, 0, 450, [(0, c['light']), (.6, c['fill']), (1, c['dark'])])
    one = path(curve_d(COLLAR_R, True, 4), fill, c['line'], 2.2)
    one += f'<path d="M446 392 Q460 410 470 401" fill="none" stroke="{c["deep"]}" stroke-width="3" opacity=".5" filter="{g.blur(1.5)}"/>'
    btn = f'<circle cx="484" cy="420" r="4.6" fill="{c["light"]}" stroke="{c["line"]}" stroke-width="1.8"/>'
    g.add(one + f'<g transform="{MIRROR}">{one}</g>' + (btn if not colors or colors.get('buttons', True) else ''))
    return g


STRAP_TOP, STRAP_BOT = 362.0, 800.0


def strap():
    """吊帶（右片；左片鏡像）：深褐帶子、調整扣、下端金屬夾"""
    g = G('strap')
    d = curve_d(M['strap'][::3], True, 3)
    fill = g.lin(330, 0, 410, 0, [(0, STRAP_D), (.4, STRAP), (.7, STRAP_L), (1, STRAP_D)])
    clipd = f'M336 772 H406 V808 Q370 822 334 808Z'
    ins = (f'<rect x="338" y="498" width="44" height="17" rx="5" fill="{METAL}" stroke="{METAL_D}" stroke-width="1.6"/>'
           f'<path d="M342 503 H378" stroke="{METAL_L}" stroke-width="2" stroke-linecap="round"/>'
           f'<path d="M380 380 Q370 560 362 770" fill="none" stroke="{STRAP_L}" stroke-width="2" opacity=".5"/>')
    shape(g, d, fill, INK, 2.0, ins)
    g.add(f'<path d="{clipd}" fill="{METAL}" stroke="{METAL_D}" stroke-width="1.6"/>'
          f'<path d="M346 780 H396" stroke="{METAL_L}" stroke-width="2" stroke-linecap="round"/>'
          f'<path d="M352 806 Q370 830 388 806 L388 824 Q370 840 352 824Z" fill="{STRAP}" stroke="{INK}" stroke-width="1.6"/>')
    return g


def belt(colors=None):
    """褲頭腰帶（褲子的腰帶環、扣子；被襯衫下襬壓住上緣）"""
    c = colors or dict(fill=PANTS, light=PANTS_L, dark=PANTS_D, line=PANTS_LINE)
    g = G('belt')
    A = AXIS
    fill = g.lin(0, 796, 0, 852, [(0, c['light']), (.5, c['fill']), (1, c['dark'])])
    band = f'M290 798 Q{A} 818 {2 * A - 290} 798 L{2 * A - 292} 840 Q{A} 860 292 840Z'
    s = path(band, fill, c['line'], 2.0)
    for x in (405, 2 * A - 405):
        s += f'<rect x="{x - 8}" y="806" width="16" height="44" rx="3" fill="{c["fill"]}" stroke="{c["line"]}" stroke-width="1.6"/>'
    s += f'<circle cx="{A + 1}" cy="842" r="7" fill="{c["dark"]}" stroke="{c["line"]}" stroke-width="1.8"/>'
    g.add(s)
    return g


# =================================================================== hair
CROWN = (505.0, 96.0)


def _rings_d():
    return ' '.join(poly_d(r) for r in M['hair_front_rings'])


def hair_flows():
    out = []
    pts = np.array(M['hair'], float)
    for x, y in pts[::7]:
        if y < 300:
            tx, ty = float(x), float(y)
            rx, ry = CROWN[0] + (tx - CROWN[0]) * .12, CROWN[1] + (ty - CROWN[1]) * .12
            mx, my = (rx + tx) / 2, (ry + ty) / 2
            nx, ny = -(ty - ry), tx - rx
            L = math.hypot(nx, ny) + 1e-9
            bend = .12 * (1 if tx > CROWN[0] else -1)
            out.append(((rx, ry), (mx + nx / L * bend * L, my + ny / L * bend * L), (tx, ty)))
    return out


def _q(a, c, b, u):
    return tuple((1 - u) ** 2 * a[i] + 2 * (1 - u) * u * c[i] + u * u * b[i] for i in (0, 1))


def hair_paint(g, d, rule=''):
    fill = g.lin(0, 50, 0, 320, [(0, HAIR_L), (.45, HAIR), (1, HAIR_D)])
    c = g.clip(d, evenodd=bool(rule))
    b = g.blur(5)
    main, band, dark = [], [], []
    for (a0, c0, b0) in hair_flows():
        s_, e_ = _q(a0, c0, b0, .25), _q(a0, c0, b0, .96)
        main.append(f'M{f(s_[0])} {f(s_[1])} Q{f(c0[0])} {f(c0[1])} {f(e_[0])} {f(e_[1])}')
        s2, m2, e2 = _q(a0, c0, b0, .35), _q(a0, c0, b0, .5), _q(a0, c0, b0, .66)
        cm = tuple(2 * m2[i] - (s2[i] + e2[i]) / 2 for i in (0, 1))
        band.append(crescent(s2, cm, e2, 4.5))
        s3, m3, e3 = _q(a0, c0, b0, .7), _q(a0, c0, b0, .82), _q(a0, c0, b0, .97)
        cm3 = tuple(2 * m3[i] - (s3[i] + e3[i]) / 2 for i in (0, 1))
        dark.append(crescent(s3, cm3, e3, -5))
    return (f'<path d="{d}" fill="{fill}"{rule}/><g clip-path="{c}">'
            f'<path d="M360 220 Q{AXIS} 300 670 220 L670 330 L360 330Z" fill="{HAIR_D}" opacity=".3" filter="{b}"/>'
            f'<path d="{" ".join(dark)}" fill="{HAIR_D}" opacity=".6" filter="{g.blur(1)}"/>'
            f'<path d="{" ".join(band)}" fill="#c8a88c" opacity=".55" filter="{g.blur(1.4)}"/>'
            f'<path d="{" ".join(main)}" fill="none" stroke="{HAIR_D}" stroke-width="1.1" stroke-linecap="round" opacity=".6"/></g>'
            + path(d, 'none', HAIR_LINE, 2.2, extra=rule))


def hair(front):
    g = G('hair_front' if front else 'hair_back')
    if front:
        g.add(hair_paint(g, _rings_d(), ' fill-rule="evenodd"'))
    else:
        g.add(hair_paint(g, poly_d(M['hair'])))
    return g


# =================================================================== wave forearm (local frame: elbow at 0,0, forearm up)
def wave_fore():
    """舉起的前臂：捲起的米白袖口＋肉肉前臂＋張開的手（手心朝外）。本地 px；建模時放到轉出去的上臂袖口"""
    g = G('wave_fore')
    skin = g.lin(-40, 0, 40, 0, [(0, SKIN_D), (.35, SKIN_L), (.7, SKIN), (1, SKIN_D)])
    cf = g.lin(-56, 0, 56, 0, [(0, SHIRT_D), (.4, SHIRT_L), (1, SHIRT_D)])
    arm = 'M-38 10 Q-44 -60 -36 -140 Q-34 -160 -32 -170 L32 -170 Q36 -150 38 -140 Q44 -60 38 10 Q0 22 -38 10Z'
    cuff = 'M-54 14 Q0 26 54 14 L50 -30 Q0 -20 -50 -30Z'
    palm = 'M-32 -166 Q-38 -206 -28 -226 L28 -226 Q38 -206 32 -166Z'
    fingers = (('M-22 -220 L-28 -254', 13.5), ('M-7 -224 L-9 -264', 14), ('M8 -224 L10 -262', 14), ('M22 -220 L28 -250', 13))
    thumb = ('M30 -184 Q46 -194 54 -212', 14)
    s = path(arm, skin, SKIN_LINE, 2.2)
    s += f'<g fill="none" stroke="{SKIN_LINE}" stroke-linecap="round" stroke-linejoin="round">'
    for d, w in (*fingers, thumb):
        s += f'<path d="{d}" stroke-width="{w + 3.6}"/>'
    s += f'<path d="{palm}" fill="{SKIN_LINE}" stroke-width="3.6"/></g>'
    s += f'<g fill="none" stroke="{skin}" stroke-linecap="round" stroke-linejoin="round">'
    for d, w in (*fingers, thumb):
        s += f'<path d="{d}" stroke-width="{w}"/>'
    s += f'<path d="{palm}" fill="{skin}" stroke="none"/></g>'
    s += f'<path d="M-20 -196 Q0 -204 20 -196" fill="none" stroke="{SKIN_DD}" stroke-width="1.3" stroke-linecap="round" opacity=".8"/>'
    s += path(cuff, cf, SHIRT_LINE, 2.2) + f'<path d="M-50 -8 Q0 4 52 -8" fill="none" stroke="{SHIRT_DD}" stroke-width="2" opacity=".6"/>'
    g.add(s)
    return g


# =================================================================== scene
TRACE_GROUPS = {'face': 'face', 'ear_R': 'ear_R', 'ear_L': 'ear_L', 'nose': 'nose', 'smile': 'smile', 'beard': 'beard',
                'blush_R': 'blush_R', 'blush_L': 'blush_L',
                **{f'{g}_{s}': f'{g}_{s}' for s in 'RL' for g in ('eye', 'iris', 'hilite', 'lash', 'lowlash', 'brow')}}

OUTFIT = {}      # 換裝（baker.py）放「群組 id -> 函式」覆蓋身體的畫法


def scene():
    groups = [sleeve(), forearm(), hand(), leg_window('thigh', 790, 1210), leg_window('calf', 1160, 1402), pants_top(), boot(),
              chest(), neck(), neck_shadow(), collar(True), collar(False), belt(), strap(), hair(True), hair(False), wave_fore()]
    sc = {g.name: g.out() for g in groups}
    for k, fn in OUTFIT.items():
        sc[k] = fn().out()
    sc.update({g: TRACE['groups'][n].replace(f'<g id="{n}">', f'<g id="{g}">', 1) for n, g in TRACE_GROUPS.items() if n in TRACE['groups']})
    import expr
    sc.update(expr.groups())
    return sc


ORDER_PREVIEW = [
    ('hair_back', 0), ('collar_back', 0), ('neck', 0), ('neck_shadow', 0), ('boot', 1), ('calf', 1), ('thigh', 1), ('pants_top', 0), ('belt', 0),
    ('shirt', 0), ('strap', 1), ('collar_front', 0), ('hand', 1), ('upper', 1), ('forearm', 1),
    ('ear_R', 0), ('ear_L', 0), ('face', 0), ('blush_R', 0), ('blush_L', 0), ('nose', 0), ('smile', 0), ('beard', 0),
    ('eye_R', 0), ('eye_L', 0), ('iris_R', 0), ('iris_L', 0), ('hilite_R', 0), ('hilite_L', 0), ('lowlash_R', 0), ('lowlash_L', 0),
    ('lash_R', 0), ('lash_L', 0), ('hair_front', 0), ('brow_R', 0), ('brow_L', 0)]


def preview_svg(sc=None, bg='#808080'):
    sc = sc or scene()
    body = ''
    for name, m in ORDER_PREVIEW:
        body += sc[name]
        if m:
            body += f'<g transform="{MIRROR}">{sc[name]}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1536" viewBox="0 0 1024 1536"><rect width="1024" height="1536" fill="{bg}"/>{body}</svg>'


if __name__ == '__main__':
    import sys
    from playwright.sync_api import sync_playwright
    out = ROOT / '角色工坊/輸出/胖大叔'
    out.mkdir(parents=True, exist_ok=True)
    base = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'psd-create/images/chubby_hand_v3/base.png')
    with sync_playwright() as pw:
        page = pw.chromium.launch(channel='msedge').new_page(viewport={'width': 1024, 'height': 1536}, device_scale_factor=1)
        page.set_content('<style>body{margin:0}svg{display:block}</style>' + preview_svg())
        page.locator('svg').screenshot(path=str(out / '手繪總覽.png'))
    from PIL import Image
    a = Image.open(out / '手繪總覽.png').convert('RGB')
    b = Image.open(base).convert('RGB')
    s = Image.new('RGB', (2048, 1536))
    s.paste(b, (0, 0)); s.paste(a, (1024, 0))
    s.resize((1024, 768)).save(out / '手繪對照.jpg', quality=88)
    print(out / '手繪對照.jpg')
