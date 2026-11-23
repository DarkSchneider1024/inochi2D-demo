"""《國王的新衣》V6 騙子裁縫「針先生」needle_nc_m2v3（香皮尼臉模換裝，2026-11-23），含 V1 式側面 needle_nc_m2v3_side。

    python -X utf8 inochi2D-demo/tools/story_male/needle_nc.py            建正面 models/needle_nc_m2v3.inp
    python -X utf8 inochi2D-demo/tools/story_male/needle_nc.py --side     建側面走路 models/needle_nc_m2v3_side.inp

做法照 shoe_m2.py（紳士、麵包師傅）：不改 male2*.py、shoe_m2.py，匯入後只在這支程式的行程裡換掉模組常數，跑香皮尼同一條建模流程；
光頭臉由 shoe_m2.sync_face() 取 male2_hand_v3 的貼圖位元組（male2_check.py needle_nc_m2v3 --except-brows 逐層比）。
形狀量自底圖 carrot-youtube/人物形象/32_國王的新衣V6換裝/needle_nc_m2v3_底圖_v1.png（模型座標＝底圖平移 (-2, -26)），上色全部手繪 SVG。
  白襯衫（開領、領口露膚色 V、長袖白袖口）、黑色合身背心（翻領、五顆釦、兩個口袋蓋、左胸一排針）、黃色捲尺掛脖子兩條垂下
  （獨立一層「捲尺」，尾端跟 Coat:: Sway 小幅擺）、黑長褲、黑皮鞋、黑髮往後梳（香皮尼髮型拿掉瀏海四片、改黑色）、眉毛改黑。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import build_mrc_princes as P                           # noqa: E402
import build_mr_carrot_story_v3 as CV                   # noqa: E402
from build_story_trio import Model, set_part_image      # noqa: E402
import build_story_trio as BT                           # noqa: E402
import male2_art as A                                   # noqa: E402
import male2 as M2                                      # noqa: E402
import male2_side3 as S3                                # noqa: E402
import male2_head9 as H9                                # noqa: E402
import shoe_m2 as SM                                    # noqa: E402

ROOT = HERE.parents[2]
MODELS = ROOT / 'inochi2D-demo/models'
MID = 'needle_nc_m2v3'
NAME = '針先生（國王的新衣・香皮尼臉模）'
BASE = ROOT / 'carrot-youtube/人物形象/32_國王的新衣V6換裝/needle_nc_m2v3_底圖_v1.png'
BX = A.BX

SHIRT = SM.SHIRT
SKIN = SM.SKIN
VEST = dict(dark='#0f1013', mid='#1b1c21', light='#2b2d34', line='#040405')
LAPEL = dict(dark='#16171b', mid='#24262d', light='#383b44')
BLACK = dict(dark='#0f1014', mid='#1b1c22', light='#2c2e36', line='#050507')
TAPE = dict(dark='#b8901c', mid='#e3c13c', light='#f6e27a', line='#6e5410', tick='#3a2e0a')
HAIR_PAL = ('#101116', '#1d1f27', '#2b2e39', '#3c404d', '#6e7588', '#07080b', '#07080b')
HAIR_SWAP = {'#c4cad6': '#262832', '#f7f8fb': '#4a4f5e', '#7d869c': '#0b0c10', '#cfd4de': '#22242d', '#ffffff': '#5d6476'}
BROW_RAMP = ('#050507', '#0a0b0e', '#121318', '#1a1c22', '#24262e', '#30333c', '#40434d')


def shirt_trim(d, w=3.0):
    """the white cuff's edge: a thin seam, no braid"""
    return A.stroke(d, SHIRT['line'], w * .35 + .6, .7)


def shirt_button(art, x, y, r=4.2):
    r *= .75
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f6f8fb" stroke="{SHIRT["line"]}" stroke-width=".9"/>'


# ---------------------------------------------------------------------------------------------- shirt (model base px)
def needle_shirt(art):
    """the white shirt (only its open neck and a strip down the V show between the lapels): skin V to the first button (base y 334)"""
    g = art.lin(360, 0, 668, 0, [(0, SHIRT['dark']), (.25, SHIRT['mid']), (.5, SHIRT['light']), (.75, SHIRT['mid']), (1, SHIRT['dark'])])
    inner = A.soft(art, A.path([(470, 340), (488, 400), (500, 440), (488, 440), (466, 400)]), SHIRT['dark'], .3, 5)
    inner += A.soft(art, A.path([(558, 340), (540, 400), (528, 440), (540, 440), (562, 400)]), SHIRT['dark'], .3, 5)
    out = art.piece(A.path(SM.SHIRT_PTS), g, SHIRT['line'], inner, outline=A.path(SM.SHIRT_R[3:], False) + A.path(A.mir(SM.SHIRT_R, BX)[:-3], False))
    v = A.path([(480, 250, 'c'), (548, 250, 'c'), (514, 334, 'c')])
    sg = art.lin(0, 250, 0, 334, [(0, SKIN['light']), (.6, SKIN['light']), (1, SKIN['mid'])])
    vin = A.soft(art, A.path([(480, 262), (548, 262), (548, 280), (480, 280)]), SKIN['dark'], .3, 5)
    out += art.piece(v, sg, SKIN['line'], vin, lw=1.1, outline=A.path([(486, 270), (514, 334), (542, 270)], False))
    out += A.stroke(A.path([(514, 334), (515, 420), (514, 600)], False), SHIRT['line'], 1.1, .6)
    for y in (380, 412):
        out += f'<circle cx="515" cy="{y}" r="3.2" fill="#f4f6fa" stroke="{SHIRT["line"]}" stroke-width=".9"/>'
    return out


COLLAR_R = [(490, 252, 'c'), (476, 257), (464, 270), (458, 288), (466, 322, 'c'), (480, 314), (492, 302, 'c'), (498, 288), (502, 268, 'c')]


def needle_collar(art):
    """the open collar: two short wings standing beside the neck, tips at (466, 322) and its mirror (base 468, 348)"""
    out = ''
    for pts, left in ((COLLAR_R, False), (A.mir(COLLAR_R, BX), True)):
        x0, x1 = (2 * BX - 458, 2 * BX - 502) if left else (458, 502)
        g = art.lin(x0, 0, x1, 0, [(0, SHIRT['mid']), (.5, SHIRT['light']), (1, '#eef2f8')])
        fold = [(484, 262), (472, 282), (468, 306)]
        inner = A.stroke(A.path(A.mir(fold, BX) if left else fold, False), SHIRT['dark'], 1, .5)
        out += art.piece(A.path(pts), g, SHIRT['line'], inner)
    out += shirt_button(art, 503, 308, 4.0)
    return out


# ---------------------------------------------------------------------------------------------- vest (model base px)
VEST_R = [(494, 380), (478, 330), (468, 292), (462, 266, 'c'), (430, 278), (396, 292, 'c'), (392, 340), (390, 424), (390, 520), (392, 600),
          (396, 644, 'c'), (446, 668), (492, 694, 'c')]
VEST_PTS = [(514, 421, 'c'), *VEST_R, (514, 660, 'c'), *A.mir(VEST_R, BX)]
LAPEL_R = [(462, 266, 'c'), (450, 292), (428, 334, 'c'), (442, 340, 'c'), (470, 372), (500, 416, 'c'), (494, 380), (478, 330), (468, 292)]
BUTTONS = (446, 494, 539, 581, 629)
PINS = (559, 569, 591, 602, 611)


def vest_button(art, x, y, r=4.6):
    g = art.rad(x - r * .3, y - r * .35, r * 1.3, [(0, '#5a5d68'), (.5, '#26282f'), (1, '#0b0c0f')])
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{g}" stroke="#000" stroke-width="1"/>'
            f'<circle cx="{x - r * .3}" cy="{y - r * .35}" r="{r * .25}" fill="#9aa0ad" opacity=".7"/>')


def vest(art):
    """black fitted waistcoat (base: edges 392..632, shoulders at y 318, lapels notched at y 360, the V closes at (516, 446), five
    buttons, welt pockets at y 605, points at (494, 718) / (540, 718) with the notch at (512, 684); model = base - (2, 26)), plus the
    row of pins on the wearer's left chest (base 561..613 x 420..470)"""
    g = art.lin(388, 0, 640, 0, [(0, VEST['dark']), (.22, VEST['mid']), (.42, VEST['light']), (.6, VEST['mid']), (.85, VEST['light']), (1, VEST['dark'])])
    inner = ''
    for pts, op in (([(400, 300), (414, 300), (412, 640), (400, 640)], .45), ([(614, 300), (628, 300), (626, 640), (614, 640)], .35)):
        inner += A.soft(art, A.path(pts), '#4a4e5a', op, 6)
    inner += A.soft(art, A.path([(390, 610), (640, 610), (640, 700), (390, 700)]), '#000', .35, 10)
    inner += A.stroke(A.path([(514, 422), (514, 660)], False), VEST['line'], 1.3, .9)          # the front edge
    for x0, x1 in ((450, 470), (558, 578)):                                                     # darts
        inner += A.stroke(A.path([(x0, 470), (x0 + 4, 560), (x0 + 2, 640)], False), '#000', 1, .45)
    out = art.piece(A.path(VEST_PTS), g, VEST['line'], inner)
    for pts, left in ((LAPEL_R, False), (A.mir(LAPEL_R, BX), True)):
        lg = art.lin(2 * BX - 430 if left else 430, 0, 2 * BX - 500 if left else 500, 0, [(0, LAPEL['dark']), (.5, LAPEL['light']), (1, LAPEL['mid'])])
        out += art.piece(A.path(pts), lg, VEST['line'], A.stroke(A.path(A.mir([(452, 296), (436, 330)], BX) if left else [(452, 296), (436, 330)], False), '#5a5e6a', 1, .5))
    for x, w in ((408, 60), (560, 60)):                                                          # welt pockets
        d = A.path([(x, 574, 'c'), (x + w, 572, 'c'), (x + w, 582, 'c'), (x, 584, 'c')])
        out += art.piece(d, art.lin(0, 572, 0, 584, [(0, LAPEL['light']), (1, LAPEL['dark'])]), VEST['line'], lw=1.2)
    for y in BUTTONS:
        out += vest_button(art, 514, y)
    # the pins: a dark strip with five dressmaker's pins (silver shafts, round heads)
    out += art.piece(A.path([(548, 406, 'c'), (620, 406, 'c'), (620, 420, 'c'), (548, 420, 'c')]),
                     art.lin(0, 406, 0, 420, [(0, '#3a3c44'), (1, '#1a1b20')]), '#000', lw=1)
    for i, x in enumerate(PINS):
        top = 394 + (i % 2) * 3
        sg = art.lin(x - 2, 0, x + 2, 0, [(0, '#6f7480'), (.5, '#f2f4f8'), (1, '#8a8f9b')])
        out += f'<path d="M{x - 1.4} {top + 3} L{x + 1.4} {top + 3} L{x + .5} 446 L{x - .5} 446Z" fill="{sg}" stroke="#2a2c33" stroke-width=".5"/>'
        hg = art.rad(x - 1, top - 1, 4, [(0, '#ffffff'), (.6, '#c9ccd4'), (1, '#7c818e')])
        out += f'<circle cx="{x}" cy="{top}" r="3.2" fill="{hg}" stroke="#30323a" stroke-width=".8"/>'
    return out


# ---------------------------------------------------------------------------------------------- tape measure
TAPE_L = [(472, 250), (456, 276), (448, 310), (445, 380), (443, 480), (442, 600), (441, 724)]
TAPE_R = [(546, 252), (566, 276), (575, 310), (578, 380), (579, 480), (580, 618)]
TAPE_W = 7.0          # half width


def tape_strand(art, centre):
    c = A.spline(centre, 160)
    L, R, N = [], [], []
    for i, (x, y) in enumerate(c):
        a, b = c[max(i - 1, 0)], c[min(i + 1, len(c) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = (tx * tx + ty * ty) ** .5 or 1
        nx, ny = -ty / l, tx / l
        N.append((nx, ny, tx / l, ty / l))
        L.append((x + nx * TAPE_W, y + ny * TAPE_W)); R.append((x - nx * TAPE_W, y - ny * TAPE_W))
    d = A.poly(L + R[::-1]) + 'Z'
    x0, x1 = min(p[0] for p in c) - TAPE_W, max(p[0] for p in c) + TAPE_W
    g = art.lin(x0, 0, x1, 0, [(0, TAPE['dark']), (.35, TAPE['mid']), (.6, TAPE['light']), (1, TAPE['mid'])])
    inner = ''
    acc, k = 0.0, 0
    for i in range(1, len(c)):
        acc += ((c[i][0] - c[i - 1][0]) ** 2 + (c[i][1] - c[i - 1][1]) ** 2) ** .5
        if acc >= 4.5:
            acc, k = 0.0, k + 1
            nx, ny, _, _ = N[i]
            ln = TAPE_W * (.9 if k % 5 == 0 else .45)
            x, y = c[i]
            inner += A.stroke(f'M{x + nx * TAPE_W:.1f} {y + ny * TAPE_W:.1f} L{x + nx * (TAPE_W - ln):.1f} {y + ny * (TAPE_W - ln):.1f}', TAPE['tick'], .8, .8)
            if k % 10 == 0:
                inner += f'<circle cx="{x - nx * 2.5:.1f}" cy="{y - ny * 2.5:.1f}" r="1.3" fill="{TAPE["tick"]}" opacity=".7"/>'
    inner += A.stroke(A.poly([(x - nx * TAPE_W * .55, y - ny * TAPE_W * .55) for (x, y), (nx, ny, _, _) in zip(c, N)]), TAPE['light'], 1.4, .6)
    out = art.piece(d, g, TAPE['line'], inner, lw=1.1)
    # the metal end tip
    x, y = c[-1]
    nx, ny, tx, ty = N[-1]
    tip = [(x + nx * (TAPE_W + .5) - tx * 7, y + ny * (TAPE_W + .5) - ty * 7), (x + nx * (TAPE_W + .5) + tx * 3, y + ny * (TAPE_W + .5) + ty * 3),
           (x - nx * (TAPE_W + .5) + tx * 3, y - ny * (TAPE_W + .5) + ty * 3), (x - nx * (TAPE_W + .5) - tx * 7, y - ny * (TAPE_W + .5) - ty * 7)]
    out += art.piece(A.poly(tip) + 'Z', art.lin(x - TAPE_W, 0, x + TAPE_W, 0, [(0, '#8d929c'), (.5, '#f4f5f7'), (1, '#9da1aa')]), '#3c3f46', lw=1)
    return out


def tape(art):
    return tape_strand(art, TAPE_L) + tape_strand(art, TAPE_R)


# ---------------------------------------------------------------------------------------------- configure
def needle_shin(art):
    """shoe_m2.trouser_shin in black, standing IN FRONT of the thigh and fading in over its top 32 px (base y 1118..1150), so the
    thigh's hem line is covered and the knee shows no step or seam (both use the same gradient across x)"""
    fade = art.lin(0, 1118, 0, 1150, [(0, '#000000'), (1, '#ffffff')])
    art.defs.append(f'<mask id="nd_shin_fade" maskUnits="userSpaceOnUse" x="250" y="1050" width="350" height="500">'
                    f'<rect x="250" y="1050" width="350" height="500" fill="{fade}"/></mask>')
    return f'<g mask="url(#nd_shin_fade)">{SM.trouser_shin(art)}</g>'


def configure():
    SM.WHO = 'needle'
    SM.INFO['needle'] = dict(mid=MID, name=NAME, base=BASE.name)
    M2.MID = MID
    M2.IMG = ROOT / 'psd-create/images' / MID
    M2.BASE_SRC = BASE                       # measure() -> make_base(): same (-2, -26)
    S3.FRONT, S3.SID = MID, MID + '_side'
    A.NAVY.update(SHIRT)                     # sleeves = the white shirt
    A.GREY.update(BLACK)                     # trousers
    SM.CREAM.update(BLACK)                   # trouser_shin and the side view's hem read SM.CREAM
    SM.LEATHER.update(dict(dark='#0d0e11', mid='#1c1d22', light='#3b3d46', line='#050507'))
    A.trim = shirt_trim
    A.button = shirt_button
    A.HAIR_PAL = HAIR_PAL
    A.HAIR.update(deep='#0b0c10', dark='#15161c', mid='#22242d', light='#343846', shine='#5d6476', line='#07080b')
    P.RAMPS.update({'glove': SM.SKIN_RAMP, 'nd_brow': BROW_RAMP})
    M2.NEW.clear()
    M2.NEW.update({
        '後領': ('襯衫領', 'collar_back', (470, 244, 558, 306), .595, (4, 4)),
        '襯衫身': ('背心_R', 'shirt', (352, 250, 676, 660), .585, (6, 9)),
        '背心前片': ('背心_R', 'vest', (384, 258, 644, 700), .575, (8, 12)),
        '捲尺': ('背心_R', 'tape', (428, 240, 596, 736), .560, (5, 14)),
    })
    SM.APRON_SWAY = (('捲尺', 330.0, 730.0, 6.0),)      # the tape's hanging ends swing a little (Coat:: Sway)
    M2.coat_sway = SM.apron_sway
    M2.SHIN_Z = {'小腿_R': .6195, '小腿_L': .6190}      # the shin (faded top) in front of the thigh: no hem line at the knee
    S3.TORSO = ('胸腔', '襯衫領', '後領', '襯衫身', '背心前片', '捲尺', '褲頭')
    S3.side_foot = side_foot
    S3.walk = side_finish
    S3.DROP_PARTS = S3.DROP_PARTS + ('指手_', '握拳_', '推鏡', '思考')
    S3.DROP_PARAMS = S3.DROP_PARAMS + ('Arm:: Think', 'Arm:: Explain', 'Glasses:: Push')


def side_foot(art, far):
    """shoe_m2.baker_side_foot with black leather / black trouser hem, and no light laces"""
    n0 = len(art.defs)
    out = SM.baker_side_foot(art, far)
    swap = {'#c79a70': '#5a5e6a', '#e2cfae': '#2e3038', '#583820': '#17181d', '#7c5634': '#2a2c33',
                 '#bdb39d': '#0d0e12', '#e2dccd': '#24262d'}          # the far foot's own brown / cream too
    for a, b in swap.items():
        out = out.replace(a, b)
        art.defs[n0:] = [d.replace(a, b) for d in art.defs[n0:]]          # gradient stops live in the defs
    return out


def scene():
    art = A.Art()
    g = dict(shirt=needle_shirt(art), collar_back=SM.baker_collar_back(art), collar_front=needle_collar(art), vest=vest(art), tape=tape(art),
             pants_top=A.pants_top(art), thigh=A.thigh(art), boot_shaft=needle_shin(art), boot_foot=A.boot_foot(art),
             upper_arm=A.upper_arm(art), forearm=A.forearm(art))
    return art.defs_svg(), g


def clothes(model, page, defs, G):
    part = CV.fit(model, '襯衫領', (440, 234, 590, 330))
    CV.regrid(part, 6, 4)
    M2.clothes(model, page, defs, G)


# ---------------------------------------------------------------------------------------------- hair (black, combed back)
def hair(model, page):
    """shoe_m2.hair for the gent (male2's hair without the four fringe locks), all black, no hat"""
    real = A.render

    def render_black(page_, defs, body, box, k=2.0, transform=''):
        for a, b in HAIR_SWAP.items():
            defs, body = defs.replace(a, b), body.replace(a, b)
        return real(page_, defs, body, box, k, transform)
    A.render = render_black
    try:
        SM.WHO = 'gent'                      # drop the bangs ...
        real_hat = SM.top_hat
        SM.top_hat = lambda art: ''          # ... and draw no hat
        locks = SM.hair(model, page)
    finally:
        A.render = real
        SM.top_hat = real_hat
        SM.WHO = 'needle'
    # no hat: its (empty) layer and switch go
    part = model.parts.pop('帽子')
    model.parents.pop(part['uuid'])['children'].remove(part)
    for prm in model.json['param']:
        prm['bindings'] = [b for b in prm['bindings'] if b['node'] != part['uuid']]
    prm = model.params.pop('Acc:: Hat Off')
    model.json['param'].remove(prm)
    locks.pop('帽子', None)
    return locks


def black_brows(model):
    for n in ('眉毛_R', '眉毛_L', '故事差分_眉毛_怒', '故事差分_眉毛_哀'):
        if n in model.parts:
            part = model.parts[n]
            img = P.ramp_img(P.tex(model, part), 'nd_brow', tone=(.12, 1, .8))
            set_part_image(model, part, img)      # sync_face() gave each face layer its own texture slot


def build():
    M2.squat_joints()
    model, src = Model(M2.SRC), Model(M2.SRC)
    defs, G = scene()
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='msedge')
        page = br.new_page(device_scale_factor=1)
        M2.face(model, page)
        M2.eyes(model, page)
        M2.mouth(model, page)
        if M2.TRACE:
            M2.expressions(model, page)
        clothes(model, page, defs, G)
        locks = hair(model, page)
        M2.wave(model, src, page, defs, G)
        br.close()
    M2.arm_reproportion(model)
    M2.arm_rig(model)
    M2.head_yaw(model, src)
    done = H9.apply(model, M2.base_xy, SM.SCALE)
    print(f'  九軸（香皮尼投影）：{len(done)} 層')
    M2.jelly(model)
    M2.skin(model)
    done = set()
    for n, part in model.parts.items():
        if part['type'] != 'Part' or part['textures'][0] in done:
            continue
        done.add(part['textures'][0])
        arr = np.asarray(P.tex(model, part)).copy()
        z = arr[..., 3] == 0
        if (arr[..., :3][z] != 0).any():
            arr[..., :3][z] = 0
            set_part_image(model, part, Image.fromarray(arr))
    SM.sync_face(model)
    black_brows(model)
    SM.drop_glasses_arm(model)
    M2.prune(model)
    meta = model.json['meta']
    meta['name'] = NAME
    meta['artist'] = 'Claude (story_male/needle_nc.py on male2.py, hand-drawn SVG)'
    model.path = MODELS / f'{MID}.inp'
    model.save()
    M2.landmarks(model, locks)
    f = M2.IMG / 'landmarks.json'
    L = json.loads(f.read_text(encoding='utf-8'))
    L.update(date='2026-11-23', builder='inochi2D-demo/tools/story_male/needle_nc.py', face_gate=f'psd-create/images/{SM.FACE_MODEL}/bald_face.json',
             note=f'{NAME}＝香皮尼臉模 male2_hand_v3 換裝（needle_nc.py）；base.png＝Gemini 原位換裝底圖平移 (-2, -26)。',
             bald_ref=f'psd-create/images/{SM.FACE_MODEL}/bald_ref/bald_ref_aligned.png',
             bald_ref_note='光頭臉和 male2_hand_v3 逐像素相同（sync_face()；眉毛改黑），T17 用香皮尼的光頭參考。')
    f.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
    M2.measure(model)
    print(model.path)


# ---------------------------------------------------------------------------------------------- side
def side_finish(model):
    SM.REAL_WALK(model)
    save = model.save

    def save_named():
        model.json['meta'].update(name=NAME + '・側面', artist='Claude (story_male/needle_nc.py on male2_side3.py)')
        save()
    model.save = save_named


if __name__ == '__main__':
    configure()
    S3.build() if '--side' in sys.argv else build()
