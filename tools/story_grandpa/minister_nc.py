"""《國王的新衣》V6 老大臣（minister_nc_gpv3）：老爺爺新基底 grandpa_hand_v3 的換裝（2026-11-23）。
    python -X utf8 inochi2D-demo/tools/story_grandpa/minister_nc.py        -> inochi2D-demo/models/minister_nc_gpv3.inp（.inx）
    之後：story_explain.py minister_nc_gpv3 → story_think.py minister_nc_gpv3 → minister_nc_side.py
底圖：carrot-youtube/人物形象/32_國王的新衣V6換裝/minister_nc_gpv3_底圖_v1.png（Gemini 原位換裝，和老爺爺底圖同畫布、同位置）。

做法照老國王 king.py／老鞋匠 story_v7shoe/shoemaker.py：同骨架換部件；臉、五官、鬍子、頭髮一律不動（光頭臉 Acc:: Hair Off 和
grandpa_hand_v3 逐像素相同），只換服裝與配件，形狀量自底圖，乾淨手繪（平滑漸層＋等寬線，不拿底圖色階化當部件）。
  - 換圖（同一層、同一個網格與綁定）：袖子（上臂、下臂、揮手上臂、揮手前臂）→ 深紫官袍袖＋金繡肩片、金繡寬袖口；
    胸腔 → 深紫袍身（兩條金直條紋）；前領／後領 → 紫袍領口（金邊）；腰帶 → 紫（藏在袍身後）；褲子 → 深紫黑；鞋 → 黑棕。
  - 拿掉：背心兩片（Acc:: Vest Off 一起拿掉）。
  - 新增換裝層：袍領（金繡 V 形披領＋金官鍊、圓章；Acc:: Chain Off 只關官鍊不行，整層一起）、袍襬（腰下到腳踝的長袍，
    Robe:: Sway 擺動＋物理）、紫小帽（Acc:: Hat Off；Acc:: Hair Off 也一起拿掉）、圓框眼鏡（Acc:: Glasses Off）、
    白長鬍延長（長鬍，接在原本鬍子下面到胸口；Acc:: Beard Off、Acc:: Hair Off 一起拿掉，光頭臉不變）。
    頭上的新層（帽子、眼鏡、長鬍）Head:: Yaw-Pitch 用 head9.point 同一套投影，只綁新層，其他頭部層不重算。
"""
from contextlib import contextmanager
from copy import deepcopy
import math
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'story_v7shoe'))
from build_story_trio import Model, set_part_image   # noqa: E402
import art                                          # noqa: E402
from svgkit import G, crescent, curve_d, curve_pts, path, poly_d, shape, f   # noqa: E402
import build as B                                   # noqa: E402
import head9 as H9                                  # noqa: E402

MID, FRONT = 'minister_nc_gpv3', 'grandpa_hand_v3'
TITLE = '老大臣（國王的新衣，老爺爺新基底換裝）'
# 底圖量色：深紫官袍、金繡
PUR, PUR_L, PUR_D, PUR_DD, PUR_LINE = '#4a2a46', '#5f3b5a', '#3a1f37', '#2a1428', '#180a16'
GOLD, GOLD_L, GOLD_D, GOLD_LINE = '#cf9f45', '#efcf84', '#9a742e', '#55400f'
SLEEVE = dict(CREAM=PUR, CREAM_L=PUR_L, CREAM_D=PUR_D, CREAM_LINE=PUR_LINE)
PANTS = dict(PANTS='#33203a', PANTS_L='#44304c', PANTS_D='#24152a', PANTS_LINE='#120914')
SHOES = dict(SHOE='#3a2c2c', SHOE_L='#5a4646', SHOE_D='#241a1a', SHOE_LINE='#0e0808')
A = art.AXIS


@contextmanager
def colours(**kw):
    old = {k: getattr(art, k) for k in kw}
    for k, v in kw.items():
        setattr(art, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(art, k, v)


def mir(pts):
    return [(2 * A - x, y) for x, y in pts]


# ------------------------------------------------------------------ gold embroidery
def scroll(x, y, s=1.0, flip=1, rot=0.0):
    """一朵金繡捲草（本地 0,0 起筆）：一條 S 形莖、兩個捲鬚、兩片小葉；回傳 path d（描邊用）與葉片 d（填色用）"""
    k = flip
    stem = f'M0 0 C{6 * k} -10 {16 * k} -12 {20 * k} -4 C{24 * k} 4 {18 * k} 12 {10 * k} 10'
    curl = f'M{20 * k} -4 C{28 * k} -14 {38 * k} -10 {36 * k} -2 C{34 * k} 4 {28 * k} 2 {30 * k} -2'
    curl2 = f'M0 0 C{-6 * k} 8 {-2 * k} 18 {8 * k} 18'
    leaf = f'M{10 * k} -9 Q{12 * k} -20 {20 * k} -22 Q{18 * k} -12 {10 * k} -9Z M{4 * k} 12 Q{-2 * k} 20 {2 * k} 26 Q{8 * k} 20 {4 * k} 12Z'
    T = f'translate({f(x)} {f(y)}) rotate({rot:.1f}) scale({s:.3f})'
    return T, stem + ' ' + curl + ' ' + curl2, leaf


def embroidery(spots, w=2.2):
    """spots: [(x, y, s, flip, rot)] → 金繡（深金描邊、亮金芯、葉片）"""
    out = ''
    for x, y, s, k, r in spots:
        T, d, leaf = scroll(x, y, s, k, r)
        out += (f'<g transform="{T}">'
                f'<path d="{d}" fill="none" stroke="{GOLD_LINE}" stroke-width="{w + 1.6:.1f}" stroke-linecap="round" opacity=".55"/>'
                f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
                f'<path d="{leaf}" fill="{GOLD}" stroke="{GOLD_LINE}" stroke-width=".8"/>'
                f'<path d="{d}" fill="none" stroke="{GOLD_L}" stroke-width="{w * .35:.2f}" stroke-linecap="round" opacity=".8"/></g>')
    return out


def gold_line(d, w=4.0):
    return path(d, 'none', GOLD_LINE, w + 2) + path(d, 'none', GOLD, w) + path(d, 'none', GOLD_L, w * .3, .8)


# ------------------------------------------------------------------ sleeves
CUFF_TOP = 'M224 708 Q284 728 344 706'


def arm_paint(g, key='arm'):
    """老爺爺袖子的同一個外形換成深紫官袍袖：上段肩頭一片金繡肩片（底圖 x 305..360、y 340..450），袖口一圈金繡寬袖口
    （底圖 y 712..800，上下金邊）"""
    d = poly_d(art.M[key])
    fill = g.lin(262, 560, 358, 584, [(0, PUR_D), (.14, PUR), (.45, PUR_L), (.82, PUR), (1, PUR_D)])
    folds = ''.join(f'<path d="{crescent(a, c, e, t)}" fill="{PUR_DD}" opacity="{o}"/>' for a, c, e, t, o in (
        ((268, 566), (288, 590), (318, 600), 6, .7), ((276, 548), (300, 566), (330, 570), 4, .5),
        ((330, 470), (318, 520), (322, 560), -5, .45), ((300, 610), (290, 650), (298, 690), -4, .45),
        ((340, 470), (352, 520), (350, 560), 4, .3)))
    sheen = f'<path d="M300 460 Q282 560 266 690" fill="none" stroke="{PUR_L}" stroke-width="11" opacity=".35" filter="{g.blur(5)}"/>'
    # 肩片：金邊框住的深紫金繡（跟著上臂轉）
    pad = 'M300 340 Q332 330 368 332 L362 452 Q330 452 296 444Z'
    pad_in = (path(pad, g.lin(300, 0, 368, 0, [(0, PUR_DD), (.5, PUR_D), (1, PUR_DD)]))
              + f'<g clip-path="{g.clip(pad)}">' + embroidery([(312, 372, .62, 1, 70), (330, 420, .6, 1, 100), (346, 360, .5, -1, 60)], 2.0) + '</g>'
              + gold_line('M296 444 Q330 452 362 452', 3.2) + gold_line('M362 452 L368 332', 3.2) + gold_line('M300 340 L296 444', 3.2))
    # 寬袖口：深紫底金繡、上緣金邊、袖口下緣金邊
    cuff = CUFF_TOP + ' L344 830 L224 830Z'
    cuff_in = (path(cuff, g.lin(224, 0, 344, 0, [(0, PUR_DD), (.3, PUR_D), (.65, PUR), (1, PUR_DD)]))
               + f'<g clip-path="{g.clip(cuff)}">' + embroidery([(244, 752, .62, 1, -10), (276, 760, .66, 1, 5), (300, 750, .6, -1, -5), (258, 782, .5, -1, 10),
                                                                  (290, 786, .5, 1, -10)], 2.0) + '</g>'
               + gold_line(CUFF_TOP, 4.2) + gold_line('M238 790 Q272 798 310 801', 3.4))
    c = g.clip(d)
    return path(d, fill) + f'<g clip-path="{c}">{folds}{sheen}{pad_in}{cuff_in}</g>' + path(d, 'none', PUR_LINE, 2.0)


def wave_fore():
    """舉起揮手的前臂：老爺爺的揮手前臂（art.wave_fore）上紫色，袖口一圈金繡寬袖口（本地：手肘 0,0、前臂朝上）"""
    with colours(**SLEEVE):
        wf = art.wave_fore()
    band = 'M-48 -128 Q0 -112 48 -128 L48 -206 L-48 -206Z'
    sleeve = 'M-44 22 Q-50 -20 -47 -90 Q-46 -160 -40 -184 Q-20 -198 0 -198 Q20 -198 40 -184 Q46 -160 47 -90 Q50 -20 44 22 Q0 40 -44 22Z'
    clip = wf.clip(sleeve)
    wf.add(f'<g clip-path="{clip}">' + path(band, wf.lin(-48, 0, 48, 0, [(0, PUR_DD), (.35, PUR_D), (.7, PUR), (1, PUR_DD)]))
           + embroidery([(-30, -160, .6, 1, -80), (0, -150, .6, 1, -95), (24, -172, .55, -1, -85)], 2.0) + '</g>'
           + gold_line('M-46 -128 Q0 -112 46 -128', 4.0) + gold_line('M-40 -184 Q-20 -197 0 -197 Q20 -197 40 -184', 3.4))
    return wf.out()


# ------------------------------------------------------------------ robe body
def robe_fill(g):
    """袍身與袍襬共用同一個橫向漸層（同一組座標），接縫處顏色一樣"""
    return g.lin(300, 0, 2 * A - 300, 0, [(0, PUR_DD), (.12, PUR_D), (.3, PUR), (.45, PUR_L), (.55, PUR), (.72, PUR_L), (.88, PUR_D), (1, PUR_DD)])


def robe_streaks(g, y0, y1):
    """袍身、袍襬共用的兩道直向柔光（同一組座標，接縫看不出來）"""
    b = g.blur(10)
    return ''.join(f'<path d="M{x} {y0} L{x + (x - A) * .12 * (y1 - y0) / 870:.1f} {y1}" fill="none" stroke="{PUR_L}" stroke-width="26" opacity=".28" filter="{b}"/>'
                   for x in (418, 606))


def chest():
    """袍身上段（取代襯衫；同一個外形）：深紫、兩條金直條紋（底圖 x 462／562）、中縫；下緣不描線（袍襬在它前面、上緣淡入，接縫看不出來）"""
    g = G('robe_chest')
    R = art.SHIRT_R
    pts = R + mir(R[1:-1])[::-1]
    d = poly_d(pts)
    fill = robe_fill(g)
    b = g.blur(9)
    ins = (f'<ellipse cx="{A}" cy="330" rx="80" ry="40" fill="{PUR_DD}" opacity=".5" filter="{b}"/>' + robe_streaks(g, 420, 760)
           + ''.join(f'<path d="{crescent(a, c, e, t)}" fill="{PUR_DD}" opacity="{o}"/>' for a, c, e, t, o in (
               ((392, 480), (388, 600), (392, 700), 6, .45), ((632, 480), (636, 600), (632, 700), -6, .45),
               ((498, 470), (496, 600), (498, 700), 4, .35), ((526, 470), (528, 600), (526, 700), -4, .35)))
           + path(f'M{A} 420 V760', 'none', PUR_LINE, 1.3, .7)
           + gold_line('M462 420 L460 760', 4.2) + gold_line('M562 420 L564 760', 4.2))
    sides = poly_d(R[4:-1], False) + ' ' + poly_d(mir(R[4:-1]), False)
    g.add(path(d, fill) + f'<g clip-path="{g.clip(d)}">{ins}</g>' + path(sides, 'none', PUR_LINE, 2.0))
    return g.out()


YOKE_R = [(A, 268), (470, 276), (448, 286), (420, 298), (384, 314), (348, 330), (318, 346), (322, 358), (352, 382), (392, 408), (432, 432), (474, 452), (A, 466)]


def yoke():
    """金繡 V 形披領（肩膀到胸口 V 尖，底圖量：外緣肩點 318,346 → V 尖 512,466）＋金官鍊（一圈圓章與環）＋胸前圓章"""
    g = G('yoke')
    pts = YOKE_R + mir(YOKE_R[1:-1])[::-1]
    d = curve_d(pts, True, 6)
    fill = g.lin(0, 270, 0, 466, [(0, PUR_D), (.6, PUR_DD), (1, PUR_D)])
    spots = []
    for side in (1, -1):
        for x, y, s, r in ((356, 352, .7, 20), (392, 372, .75, 30), (430, 392, .75, 35), (468, 420, .7, 40), (404, 336, .55, 10), (446, 360, .6, 20),
                           (482, 392, .55, 50)):
            spots.append((x if side > 0 else 2 * A - x, y, s, side, r * side))
    ins = (embroidery(spots, 2.2)
           + f'<path d="M{A - 60} 270 Q{A} 300 {A + 60} 270 L{A + 60} 330 Q{A} 350 {A - 60} 330Z" fill="{PUR_DD}" opacity=".5" filter="{g.blur(6)}"/>')
    edge = curve_d(YOKE_R[6:], False, 6)
    shoulder = curve_d(YOKE_R[2:7], False, 6)
    trims = ''.join(gold_line(e, 4.6) for e in (edge, shoulder)) + f'<g transform="{art.MIRROR}">' + ''.join(gold_line(e, 4.6) for e in (edge, shoulder)) + '</g>'
    inner_edge = curve_d([(330, 352), (360, 374), (400, 400), (440, 424), (478, 444), (A, 456)], False, 6)
    trims += path(inner_edge, 'none', GOLD_D, 1.6, .8) + f'<g transform="{art.MIRROR}">{path(inner_edge, "none", GOLD_D, 1.6, .8)}</g>'
    g.add(path(d, fill) + f'<g clip-path="{g.clip(d)}">{ins}</g>' + path(d, 'none', PUR_LINE, 1.8) + trims)
    # 官鍊：肩上往下沿披領繞到胸前，圓章和橢圓環交替
    chain = curve_pts([(378, 320), (384, 370), (404, 420), (436, 462), (474, 490), (A, 500)], False, 30)
    acc, last, beads = 0.0, chain[0], []
    for p in chain[1:]:
        acc += math.hypot(p[0] - last[0], p[1] - last[1])
        last = p
        if acc >= 19:
            beads.append(p)
            acc = 0.0
    s = ''
    for k, (x, y) in enumerate(beads[:-1]):
        nx, ny = beads[k + 1]
        ang = math.degrees(math.atan2(ny - y, nx - x))
        for X in (x, 2 * A - x):
            a = ang if X == x else 180 - ang
            if k % 2 == 0:
                s += (f'<circle cx="{f(X)}" cy="{f(y)}" r="8.2" fill="{GOLD}" stroke="{GOLD_LINE}" stroke-width="1.6"/>'
                      f'<circle cx="{f(X)}" cy="{f(y)}" r="4.4" fill="none" stroke="{GOLD_D}" stroke-width="1.3"/>'
                      f'<circle cx="{f(X - 2.4)}" cy="{f(y - 2.6)}" r="1.8" fill="{GOLD_L}"/>')
            else:
                s += (f'<ellipse cx="{f(X)}" cy="{f(y)}" rx="9" ry="5.4" transform="rotate({a:.1f} {f(X)} {f(y)})" fill="none" stroke="{GOLD_LINE}" stroke-width="5.2"/>'
                      f'<ellipse cx="{f(X)}" cy="{f(y)}" rx="9" ry="5.4" transform="rotate({a:.1f} {f(X)} {f(y)})" fill="none" stroke="{GOLD}" stroke-width="3"/>')
    # 中央環、吊環、圓章（浮雕小皇冠）
    s += (f'<circle cx="{A}" cy="501" r="10" fill="{GOLD}" stroke="{GOLD_LINE}" stroke-width="1.6"/><circle cx="{A - 3}" cy="498" r="2.4" fill="{GOLD_L}"/>'
          f'<ellipse cx="{A}" cy="518" rx="5" ry="8" fill="none" stroke="{GOLD_LINE}" stroke-width="5"/><ellipse cx="{A}" cy="518" rx="5" ry="8" fill="none" stroke="{GOLD}" stroke-width="3"/>')
    med = g.rad(A - 6, 540, 28, [(0, GOLD_L), (.55, GOLD), (1, GOLD_D)])
    s += (f'<circle cx="{A}" cy="548" r="23" fill="{med}" stroke="{GOLD_LINE}" stroke-width="2"/>'
          f'<circle cx="{A}" cy="548" r="17" fill="none" stroke="{GOLD_D}" stroke-width="1.6"/>'
          f'<path d="M{A - 10} 556 L{A - 11} 541 L{A - 5} 547 L{A} 538 L{A + 5} 547 L{A + 11} 541 L{A + 10} 556Z" fill="{GOLD_D}" stroke="{GOLD_LINE}" stroke-width="1.1" stroke-linejoin="round"/>'
          f'<path d="M{A - 14} 534 Q{A - 6} 528 {A + 2} 530" fill="none" stroke="#fff6d8" stroke-width="2.4" stroke-linecap="round" opacity=".7"/>')
    g.add(s)
    return g.out()


SKIRT_R = [(A, 600), (360, 600), (350, 680), (347, 760), (340, 860), (326, 980), (308, 1120), (290, 1260), (274, 1380), (264, 1452), (300, 1460),
           (360, 1466), (420, 1470), (470, 1468), (A, 1472)]
WAIST_Y, HEM_Y = 690.0, 1470.0


def skirt():
    """腰下到腳踝的長袍（在袍身前面，上緣 y 612→700 淡入接上袍身）：深紫、往下微微張開、兩條金直條紋延續到下襬、柔和的直褶"""
    g = G('robe_skirt')
    pts = SKIRT_R + mir(SKIRT_R[1:-1])[::-1]
    d = curve_d(pts, True, 6)
    fill = robe_fill(g)
    folds = ''
    for x0, x1, o in ((392, 330, .5), (430, 390, .45), (488, 474, .35), (536, 550, .35), (594, 634, .45), (632, 694, .5)):
        folds += f'<path d="M{x0} 720 Q{(x0 + x1) / 2 + (6 if x0 < A else -6):.0f} 1100 {x1} 1468" fill="none" stroke="{PUR_DD}" stroke-width="10" opacity="{o}" filter="{g.blur(4)}"/>'
    for x0, x1 in ((410, 360), (458 - 18, 430), (584, 614), (624, 664)):
        folds += f'<path d="M{x0} 760 Q{(x0 + x1) / 2:.0f} 1100 {x1} 1460" fill="none" stroke="{PUR_L}" stroke-width="6" opacity=".3" filter="{g.blur(4)}"/>'
    hem = curve_d([(264, 1452), (360, 1466), (A, 1472), (2 * A - 360, 1466), (2 * A - 264, 1452)], False, 8)
    ins = (folds
           + f'<path d="M250 1420 Q{A} 1446 {2 * A - 250} 1420 L{2 * A - 250} 1490 L250 1490Z" fill="{PUR_DD}" opacity=".45" filter="{g.blur(5)}"/>'
           + robe_streaks(g, 600, 1470)
           + path(f'M{A} 640 V1472', 'none', PUR_LINE, 1.3, .7)
           + gold_line('M460 600 L458 1472', 4.2) + gold_line('M564 600 L566 1472', 4.2))
    sides = curve_d(SKIRT_R[2:10], False, 6) + ' ' + curve_d(mir(SKIRT_R[2:10]), False, 6)
    fade = g.lin(0, 612, 0, 700, [(0, '#000000'), (1, '#ffffff')])
    mk = g.uid('m')
    g.defs.append(f'<mask id="{mk}" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1600"><rect x="0" y="0" width="1024" height="1600" fill="{fade}"/></mask>')
    g.add(f'<g mask="url(#{mk})">' + path(d, fill) + f'<g clip-path="{g.clip(d)}">{ins}</g>' + path(sides + ' ' + hem, 'none', PUR_LINE, 2.0) + '</g>')
    return g.out()


def collar(front):
    """袍子的領口：後片在脖子後面（深紫內側），前片＝脖子兩側往下收成 V 的兩條紫領邊（金邊）"""
    g = G('robe_collar_front' if front else 'robe_collar_back')
    if not front:
        d = f'M447 280 Q{A} 262 {2 * A - 447} 280 L{2 * A - 452} 312 Q{A} 296 452 312Z'
        g.add(path(d, g.lin(0, 266, 0, 312, [(0, PUR_D), (1, PUR_DD)]), PUR_LINE, 1.8))
        return g.out()
    one = 'M446 279 Q452 276 458 281 Q466 312 486 338 Q500 362 512 396 L512 404 Q496 388 478 362 Q452 330 444 296Z'
    fill = g.lin(444, 280, 500, 380, [(0, PUR_L), (.6, PUR), (1, PUR_D)])
    edge = 'M458 281 Q466 312 486 338 Q500 362 512 396'
    one_s = path(one, fill, PUR_LINE, 1.7) + gold_line(edge, 2.6)
    g.add(one_s + f'<g transform="{art.MIRROR}">{one_s}</g>')
    return g.out()


# ------------------------------------------------------------------ head pieces
def cap():
    """紫色小圓帽（底圖：帽頂 y≈40、帽緣 418..606、反摺帽圈 y 96..140）：圓頂兩道縫線、柔和高光，帽圈略深"""
    g = G('cap')
    dome = f'M412 112 Q412 50 {A} 39 Q612 50 612 112Z'
    band = f'M412 100 Q{A} 86 612 100 L610 140 Q{A} 128 414 140Z'
    s = path(dome, g.rad(470, 52, 150, [(0, PUR_L), (.55, PUR), (1, PUR_D)]), PUR_LINE, 2.0)
    s += (f'<path d="M{A} 41 Q{A - 4} 70 {A - 6} 98 M{A} 41 Q{A - 52} 56 {A - 80} 100 M{A} 41 Q{A + 52} 56 {A + 80} 100" fill="none" stroke="{PUR_DD}" stroke-width="1.6" opacity=".7"/>'
          f'<path d="M448 70 Q470 46 506 40" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity=".25" filter="{g.blur(2)}"/>'
          f'<circle cx="{A}" cy="42" r="4.5" fill="{PUR_D}" stroke="{PUR_LINE}" stroke-width="1.2"/>')
    s += path(band, g.lin(412, 0, 612, 0, [(0, PUR_DD), (.3, PUR_D), (.55, PUR), (.8, PUR_D), (1, PUR_DD)]), PUR_LINE, 2.0)
    s += f'<path d="M416 104 Q{A} 91 608 104" fill="none" stroke="{PUR_L}" stroke-width="2" opacity=".6"/>'
    s += f'<path d="M416 134 Q{A} 122 608 134" fill="none" stroke="{PUR_DD}" stroke-width="3" opacity=".6"/>'
    g.add(s)
    return g.out()


def long_beard():
    """白長鬍：接在老爺爺原本的鬍子下面（原本的鬍子蓋在上面），兩側順著臉頰往下收，鬍尖在胸口（底圖 512,414）；
    寬度不超出臉頰（x 436..588），一束一束往鬍尖收的長毛、鬍尖幾撮毛尖"""
    g = G('long_beard')
    R = [(A, 270), (480, 262), (446, 228), (436, 252), (438, 292), (446, 330), (460, 364), (478, 390), (496, 406), (A, 414)]
    pts = R + mir(R[1:-1])[::-1]
    d = curve_d(pts, True, 6)
    fill = g.lin(0, 230, 0, 414, [(0, '#e3e1dc'), (.3, art.BEARD), (.75, art.BEARD_L), (1, '#e8e6e1')])
    strands = ''
    for k in range(9):
        u = k / 8
        x0 = 444 + u * 68
        y0 = 250 + abs(u - .5) * 10
        tx = A + (x0 - A) * .22
        ty = 398 + (1 - abs(u - .5) * 2) * 12
        cx = x0 + (A - x0) * .1
        strands += f'M{f(x0)} {f(y0)} Q{f(cx)} {f((y0 + ty) / 2 + 10)} {f(tx)} {f(ty)} '
    strands_m = f'<g transform="{art.MIRROR}"><path d="{strands}" fill="none" stroke="{art.BEARD_LINE}" stroke-width="1" opacity=".2"/></g>'
    shade = (f'<path d="M436 250 Q440 320 470 380 Q490 404 {A} 412" fill="none" stroke="{art.BEARD_D}" stroke-width="10" opacity=".55" filter="{g.blur(4)}"/>'
             f'<g transform="{art.MIRROR}"><path d="M436 250 Q440 320 470 380 Q490 404 {A} 412" fill="none" stroke="{art.BEARD_D}" stroke-width="10" opacity=".55" filter="{g.blur(4)}"/></g>'
             f'<ellipse cx="{A}" cy="340" rx="30" ry="50" fill="#ffffff" opacity=".55" filter="{g.blur(8)}"/>')
    tips = ''
    for x, y, dx in ((496, 404, -3), (504, 410, -1), (520, 410, 1), (528, 404, 3), (474, 386, -5), (550, 386, 5)):
        tips += f'M{x - 4} {y - 6} Q{x + dx} {y + 2} {x + dx * 1.6:.1f} {y + 9} Q{x + 4 + dx * .4:.1f} {y} {x + 4} {y - 6}Z '
    g.add(path(d, fill) + f'<g clip-path="{g.clip(d)}">{shade}<path d="{strands}" fill="none" stroke="{art.BEARD_LINE}" stroke-width="1" opacity=".2"/>{strands_m}</g>'
          + f'<path d="{tips}" fill="{art.BEARD}" opacity=".95"/>'
          + path(curve_d(R[2:], False, 6), 'none', art.BEARD_LINE, 1.1, .6) + path(curve_d(mir(R[2:]), False, 6), 'none', art.BEARD_LINE, 1.1, .6))
    return g.out()


def glasses():
    """圓框眼鏡（照老鞋匠的鏡框：head9 投影跟臉走），鏡框改金棕"""
    import shoemaker as SM
    SM.GLASS, SM.GLASS_L = '#8a6424', '#d8b268'
    return SM.glasses()


# ------------------------------------------------------------------ build helpers
def repaint(model, P, name, group, mirror, svg, wrap=None):
    box = P.box(group, bool(mirror), wrap)
    set_part_image(model, model.parts[name], P.paint(svg, box, bool(mirror), wrap))


def add_layer(model, P, name, svg, template, z, grid, keep_from=None):
    part = B.new_part(model, name, template)
    for prm in model.params.values():
        prm['bindings'] = [x for x in prm['bindings'] if x['node'] != part['uuid']]
    box = P.box(svg)
    B.place(model, name, box, P.paint(svg, box), grid)
    part['zsort'] = z
    if keep_from:      # 呼吸起伏 transform.t.y（和原本的背心一樣），其他不綁
        src = model.parts[keep_from]['uuid']
        for prm in model.params.values():
            prm['bindings'] += [dict(deepcopy(b), node=part['uuid']) for b in prm['bindings'] if b['node'] == src and b['param_name'] == 'transform.t.y']
    return part, box


def toggle(model, pname, layers):
    old = model.params.pop(pname, None)
    if old:
        model.json['param'].remove(old)
    model.param(pname, [0, 1], [{'node': model.parts[n]['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                 'isSet': [[True], [True]], 'values': [[1], [0]]} for n in layers])


def also_off(model, pname, layers):
    prm = model.params[pname]
    for n in layers:
        prm['bindings'].append({'node': model.parts[n]['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                'isSet': [[True], [True]], 'values': [[1], [0]]})


def head_follow(model, name):
    """新加的頭部層：Head:: Yaw-Pitch 用和其他頭部層同一個投影（head9.point），其他頭部層不動（光頭臉逐像素不變）"""
    part = model.parts[name]
    yaw = model.params['Head:: Yaw-Pitch']
    pa, pb = yaw['axis_points']
    pts = B.base_xy(model, part)
    vals = [[[[v * B.SCALE for v in H9.point(name, x, y, av * 2 - 1, bv * 2 - 1)] for x, y in pts] for bv in pb] for av in pa]
    B.bind(model, 'Head:: Yaw-Pitch', part, 'deform', vals)


def beard_talk(model, name):
    """長鬍跟著下顎往下（和臉、鬍子的 Mouth:: Open 同一個量：嘴線 y 255 以下漸漸到 JAW_DROP）"""
    part = model.parts[name]
    keys = model.params['Mouth:: Open']['axis_points'][0]
    pts = B.base_xy(model, part)
    sm = lambda u: (lambda q: q * q * (3 - 2 * q))(max(0.0, min(1.0, u)))
    B.bind(model, 'Mouth:: Open', part, 'deform', [[[0.0, B.JAW_DROP * k * sm((y - 255) / 26) * B.SCALE] for x, y in pts] for k in keys])


ROBE_SWAY = 'Robe:: Sway'


def robe_sway(model):
    """袍襬擺動：Robe:: Sway（-1..1）腰下漸增、下襬最大，掛自己的擺錘物理（照香皮尼外套 Coat:: Sway 的做法）"""
    part = model.parts['袍襬']
    pts = B.base_xy(model, part)

    def swing(x, y, ph):
        w = max(0.0, min(1.0, (y - WAIST_Y) / (HEM_Y - WAIST_Y))) ** 1.5
        return [ph * w * 14.0 * B.SCALE, -abs(ph) * w * 2.5 * B.SCALE]
    binding = {'node': part['uuid'], 'param_name': 'deform', 'interpolate_mode': 'Linear', 'isSet': [[True], [True], [True]],
               'values': [[[swing(x, y, ph) for x, y in pts]] for ph in (-1, 0, 1)]}
    prm = model.param(ROBE_SWAY, [0, .5, 1], [binding], low=-1)
    prm['min'], prm['max'], prm['defaults'] = [-1.0, -1.0], [1.0, 1.0], [0.0, 0.0]
    node = deepcopy(model.parts['Hair Physics'])
    node.update(uuid=model.uuid, name='Robe Physics', param=prm['uuid'], length=180.0, frequency=.8, children=[])
    model.uuid += 1
    body = model.parts['Body']
    node['transform'] = dict(trans=[0.0, (WAIST_Y - 750) * B.SCALE - body['transform']['trans'][1], 0.0], rot=[0, 0, 0], scale=[1, 1])
    body['children'].append(node)
    model.parents[node['uuid']] = body
    model.parts['Robe Physics'] = node


def build():
    model = Model(FRONT)
    with sync_playwright() as pw:
        P = B.Painter(pw)
        orig = art._arm_paint
        art._arm_paint = arm_paint
        try:
            up, fore = art.arm(True).out(), art.arm(False).out()
            for s, m in (('R', 0), ('L', 1)):
                repaint(model, P, f'上臂_{s}', 'upper', m, up)
                repaint(model, P, f'下臂_{s}', 'forearm', m, fore)
            sx, sy = B.SHOULDER
            ew = B.rotate(*B.ELBOW, B.SHOULDER, math.radians(B.WAVE_TURN))
            up_wrap, fore_wrap = f'rotate({B.WAVE_TURN} {sx} {sy})', f'translate({ew[0]:.2f} {ew[1]:.2f}) rotate({B.WAVE_LEAN})'
            wf = wave_fore()
            for s, m in (('R', 0), ('L', 1)):
                right = P.box('upper', wrap=up_wrap)
                box = right if s == 'R' else (2 * A - right[2], right[1], 2 * A - right[0], right[3])
                set_part_image(model, model.parts[f'揮手上臂_{s}'], P.paint(up, box, bool(m), up_wrap))
                right = P.box('wave_fore', wrap=fore_wrap)
                box = right if s == 'R' else (2 * A - right[2], right[1], 2 * A - right[0], right[3])
                set_part_image(model, model.parts[f'揮手前臂_{s}'], P.paint(wf, box, bool(m), fore_wrap))
        finally:
            art._arm_paint = orig
        repaint(model, P, '胸腔', 'shirt', 0, chest())
        repaint(model, P, '前領', 'collar_front', 0, collar(True))
        repaint(model, P, '後領', 'collar_back', 0, collar(False))
        with colours(**PANTS):
            repaint(model, P, '褲頭', 'pants_top', 0, art.pants_top().out())
            for s, m in (('R', 0), ('L', 1)):
                repaint(model, P, f'大腿_{s}', 'thigh', m, art.leg_window('thigh', 690, 1106).out())
                repaint(model, P, f'小腿_{s}', 'calf', m, art.leg_window('calf', 1052, 1440).out())
            belt_svg = art.belt().out()
        for k, v in {'#40332a': PUR, '#5c4b3f': PUR_L, '#2c221b': PUR_D, '#1d1611': PUR_LINE}.items():
            belt_svg = belt_svg.replace(k, v)
        repaint(model, P, '腰帶', 'belt', 0, belt_svg)
        with colours(**SHOES):
            for s, m in (('R', 0), ('L', 1)):
                repaint(model, P, f'鞋_{s}', 'boot', m, art.shoe().out())
        add_layer(model, P, '袍襬', skirt(), '背心_R', .578, (8, 14), keep_from='背心_R')
        add_layer(model, P, '袍領', yoke(), '背心_R', .548, (8, 6), keep_from='背心_R')
        add_layer(model, P, '帽子', cap(), '頭頂髮', .02, (6, 4))
        add_layer(model, P, '眼鏡', glasses(), '鼻子', .05, (8, 3))
        add_layer(model, P, '長鬍', long_beard(), '鬍子', .3883, (6, 8))
        P.close()
    model.parts['腰帶']['zsort'] = .592          # 藏在袍身、袍襬後面
    for n in ('背心_R', '背心_L'):
        B.drop(model, n)
    vo = model.params.pop('Acc:: Vest Off', None)
    if vo:
        model.json['param'].remove(vo)
    for n in ('帽子', '眼鏡', '長鬍'):
        head_follow(model, n)
    beard_talk(model, '長鬍')
    robe_sway(model)
    toggle(model, 'Acc:: Hat Off', ('帽子',))
    toggle(model, 'Acc:: Glasses Off', ('眼鏡',))
    toggle(model, 'Acc:: Robe Collar Off', ('袍領',))
    also_off(model, 'Acc:: Hair Off', ('帽子', '長鬍'))
    also_off(model, 'Acc:: Beard Off', ('長鬍',))
    B.clean_transparent(model)
    B.gc_textures(model)
    model.json['meta'].update(name=TITLE, artist='Claude (story_grandpa/minister_nc.py on grandpa_hand_v3, hand-drawn SVG)')
    model.path = B.MODELS / f'{MID}.inp'
    model.save()
    print(model.path)


if __name__ == '__main__':
    build()
