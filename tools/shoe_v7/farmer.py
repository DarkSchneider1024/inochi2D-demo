"""《鞋匠與小矮人》V7 排隊壯漢（農夫）shoe_farmer_burlyv3：柏達克臉模（burly_hand_v3）換裝（2026-11-22）。

    python -X utf8 tools/shoe_v7/farmer.py            -> models/shoe_farmer_burlyv3.inp
    python -X utf8 tools/shoe_v7/farmer.py --side     -> models/shoe_farmer_burlyv3_side.inp（先要有正面）

底圖 carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝/shoe_farmer_burlyv3_底圖_v1.png（柏達克底圖原位換裝，使用者 11-22 確認）：
草帽、紅格子襯衫捲袖、粗布背心、皮帶、工作褲、沾泥長靴；短鬍子、深棕短髮照柏達克。
做法同 story_burly/hunter.py（只匯入 arthur_cast／hunter 的工具，不改它們）：Head 底下的臉、五官、耳、鬍子、頭髮一層都不重畫
（光頭臉和 burly_hand_v3 逐像素相同）；身體各層同輪廓換色＋手繪紋理（格紋、粗布、泥巴），草帽是新的頭部圖層（Acc:: Hat Off）。
拿掉：疤、披肩、毛領、腰包；前臂的皮護腕拿掉（捲袖露出手臂）。
"""
import sys
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'story_burly'))
import arthur_cast as AC                                       # noqa: E402
from arthur_cast import A, B, G, path, shape, hue, tint, palette, BRASSSET, AX  # noqa: E402
import hunter as HU                                            # noqa: E402
from build_story_trio import Model, set_part_image             # noqa: E402

MID = 'shoe_farmer_burlyv3'
TITLE = '農夫（柏達克臉模）'
SHIRT = hue(.07, .30, 1.0)                 # 格子襯衫的米色底（格紋另外疊）
VEST_C = hue(.10, .16, 1.65)               # 粗布背心（灰褐）
PANTS = hue(.12, .20, .95)                 # 卡其褐工作褲
MUD_BOOT = dict(BOOT='#5a412c', BOOT_L='#7a5a3e', BOOT_D='#3c2a1c', BOOT_LINE='#22160d')
STRAW, STRAW_L, STRAW_D, STRAW_LINE = '#d3ad6a', '#ecd096', '#a8803e', '#5e4420'
BAND, BAND_D = '#7a5a3a', '#4e3622'


# ============================================================================================ straw hat (base px, burly canvas)
def straw_hat():
    """草帽：圓頂帽冠、褐色帽帶、寬帽簷（兩側下垂、前緣在額頭上）、草編紋與毛邊"""
    g = G('straw')
    crown = 'M418 96 C414 56 440 24 474 16 C496 10 530 10 552 16 C586 24 612 56 608 96 Z'
    brim = ('M330 152 C338 112 420 86 512 84 C604 86 686 104 692 142 C696 170 672 188 648 182 '
            'C612 166 566 116 512 112 C458 116 414 166 376 188 C350 194 326 178 330 152 Z')
    cfill = g.lin(414, 0, 612, 0, [(0, STRAW_D), (.3, STRAW_L), (.6, STRAW), (1, STRAW_D)])
    bfill = g.lin(0, 84, 0, 190, [(0, STRAW_L), (.5, STRAW), (1, STRAW_D)])
    weave_c = ''.join(f'<path d="M{434 + i * 2} {90 - i * 6} Q512 {80 - i * 7} {593 - i * 2} {90 - i * 6}" fill="none" stroke="{STRAW_D}" '
                      f'stroke-width="1.2" opacity=".55"/>' for i in range(1, 12))
    shape(g, crown, cfill, STRAW_LINE, 2.0,
          weave_c + f'<ellipse cx="470" cy="44" rx="16" ry="20" fill="#fff6dc" opacity=".35" filter="{g.blur(6)}"/>')
    band = 'M422 68 Q512 58 604 68 L607 94 Q512 84 419 94 Z'
    g.add(path(band, g.lin(0, 60, 0, 92, [(0, BAND), (1, BAND_D)]), '#3a2614', 1.6))
    # brim: weave rings following the brim, frayed straw ends on the outer edge
    rings = ''.join(f'<path d="M{340 + i * 9} {150 - i * 2} C{350 + i * 8} {116 + i * 3} {425 + i * 4} {94 + i * 3} 512 {92 + i * 3} '
                    f'C{599 - i * 4} {94 + i * 3} {676 - i * 8} {112 + i * 3} {682 - i * 9} {146 - i * 2}" fill="none" stroke="{STRAW_D}" '
                    f'stroke-width="1.1" opacity=".5"/>' for i in range(1, 7))
    rng = np.random.default_rng(7)
    fray = ''
    for t in np.linspace(0, 1, 30):
        # frayed straw ends along the brim's outer edge at the two sides (the middle is behind the crown)
        if t < .5:
            u = t * 2
            x, y = 330 + 90 * u, 150 - 40 * np.sin(u * np.pi / 2) ** .7
            dx, dy = -rng.uniform(2, 8), -rng.uniform(3, 9)
        else:
            u = (t - .5) * 2
            x, y = 604 + 88 * u, 108 + 34 * u ** 1.3
            dx, dy = rng.uniform(2, 8), -rng.uniform(3, 9)
        fray += f'<path d="M{x:.1f} {y:.1f} l{dx:.1f} {dy:.1f}" stroke="{STRAW_D}" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>'
    for x, y in ((372, 188), (360, 186), (648, 182), (662, 184), (338, 170), (684, 164)):
        fray += f'<path d="M{x} {y} l{rng.uniform(-5, 5):.1f} {rng.uniform(5, 10):.1f}" stroke="{STRAW_D}" stroke-width="1.6" stroke-linecap="round"/>'
    g.add(fray)
    shape(g, brim, bfill, STRAW_LINE, 2.0,
          rings + f'<path d="M400 150 Q450 120 512 116 Q574 120 624 150" fill="none" stroke="{STRAW_D}" stroke-width="5" opacity=".45" filter="{g.blur(3)}"/>')
    return g


# ============================================================================================ forearms without the bracer
def bare_forearm():
    """art.forearm() with the bracer swapped for a few arm-hair strokes (the farmer's sleeves are rolled)"""
    keep = A.bracer_inner
    A.bracer_inner = lambda g, x0=190, x1=306: (
        ''.join(f'<path d="M{x} {y} q-3 7 -1 13" fill="none" stroke="{A.SKIN_LINE}" stroke-width="1" stroke-linecap="round" opacity=".5"/>'
                for x, y in ((222, 690), (236, 710), (250, 690), (230, 740), (256, 730), (244, 760), (264, 756), (220, 770))))
    try:
        return A.forearm().out()
    finally:
        A.bracer_inner = keep


def bare_wave_fore(svg):
    """art.wave_fore() minus its bracer (everything after the palm creases up to the elbow highlight)"""
    a = svg.find('<path d="M-59 -66 Q0 -54 59 -66')
    b = svg.find('<path d="M-30 -12 Q-34 -34 -30 -52"')
    return svg[:a] + svg[b:] if a > 0 and b > a else svg


# ============================================================================================ raster textures on the repainted layers
def _hsv(rgb):
    r, g, b = [rgb[..., k] / 255.0 for k in range(3)]
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0)
    gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
    bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    return np.where(m, (h / 6.0) % 1.0, 0), s, mx


def _tex(model, part):
    from io import BytesIO
    from PIL import Image
    return np.asarray(Image.open(BytesIO(model.textures[part['textures'][0]][5:])).convert('RGBA')).astype(float)


def _put(model, part, arr):
    from PIL import Image
    set_part_image(model, part, Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA'))


def plaid(model, name, period=84):
    """紅格子：只在米色襯衫布上疊紅色寬條（交叉處深酒紅）＋細深線，橫豎各一組"""
    t = _tex(model, name if isinstance(name, dict) else model.parts[name])
    part = name if isinstance(name, dict) else model.parts[name]
    h, s, v = _hsv(t[..., :3])
    red = (h > .04) & (h < .16) & (s > .08) & (s < .42) & (v > .45) & (t[..., 3] > 0)
    if red.sum() < 50:
        return 0
    H, W = red.shape
    yy, xx = np.mgrid[:H, :W]

    def band(c, w, off):
        q = (c + off) % period
        return np.clip((1 - np.abs(q - period / 2) / (w / 2)) * 5, 0, 1)
    wide = np.maximum(band(xx, period * .42, 0), band(yy, period * .42, 0))
    both = band(xx, period * .42, 0) * band(yy, period * .42, 0)
    thin = np.maximum(band(xx, 3.6, period * .5), band(yy, 3.6, period * .5)) * (1 - wide)
    col = t[..., :3].copy()
    lum = (t[..., :3] * [.299, .587, .114]).sum(-1, keepdims=True) / 235.0
    redc = np.array([176, 58, 56], float) * np.clip(lum, .55, 1.08)
    wine = np.array([108, 30, 36], float) * np.clip(lum, .55, 1.08)
    col = col * (1 - .78 * wide[..., None]) + redc * .78 * wide[..., None]
    col = col * (1 - .7 * both[..., None]) + wine * .7 * both[..., None]
    col = col * (1 - .5 * thin[..., None]) + np.array([92, 40, 34], float) * .5 * thin[..., None]
    t[..., :3] = np.where(red[..., None], col, t[..., :3])
    _put(model, part, t)
    return int(red.sum())


def weave(model, name, amt=.10, seed=1):
    """粗布：細的經緯紋＋一點斑駁"""
    part = model.parts[name]
    t = _tex(model, part)
    a = t[..., 3] > 0
    H, W = a.shape
    yy, xx = np.mgrid[:H, :W]
    grid = (np.sin(xx * 1.9) * np.sin(yy * 1.9)) * .5 + .5
    rng = np.random.default_rng(seed)
    blot = ndi.gaussian_filter(rng.standard_normal((H, W)), 6)
    blot = blot / (np.abs(blot).max() + 1e-6)
    k = 1 - amt * grid + .08 * blot
    t[..., :3] = np.where(a[..., None], t[..., :3] * k[..., None], t[..., :3])
    _put(model, part, t)


def mud(model, name, from_y=.0, amt=.65, seed=3):
    """泥巴：從 from_y（貼圖高度比例）以下，越往下越多的斑塊"""
    part = model.parts[name]
    t = _tex(model, part)
    a = t[..., 3] > 0
    H, W = a.shape
    rng = np.random.default_rng(seed)
    n = ndi.gaussian_filter(rng.standard_normal((H, W)), max(2.0, W / 60))
    n = n / (np.abs(n).max() + 1e-6)
    ramp = np.clip((np.arange(H)[:, None] / H - from_y) / max(.05, 1 - from_y), 0, 1)
    m = np.clip((n + .25 * ramp - .18) * 6, 0, 1) * ramp * amt
    speck = (rng.random((H, W)) < .004 * ramp)
    speck = ndi.binary_dilation(speck, iterations=2)
    m = np.maximum(m, speck * .7 * amt)
    mudc = np.array([92, 70, 46], float)
    t[..., :3] = np.where(a[..., None], t[..., :3] * (1 - m[..., None]) + mudc * m[..., None], t[..., :3])
    _put(model, part, t)


# ============================================================================================ outfit
def farmer(model, P):
    AC.remove(model, ('疤', '疤_頰', '披肩_前', '披肩_後', '毛領_前', '毛領_後', '腰包_R'), ('Acc:: Scar Off', 'Acc:: Cape Off', 'Acc:: Fur Off'))
    S = P.scene
    sc = {'upper': tint(S['upper'], SHIRT), 'shirt': tint(S['shirt'], SHIRT), 'shirt_hem': tint(S['shirt_hem'], SHIRT),
          'vest': tint(S['vest'], VEST_C, BRASSSET), 'forearm': bare_forearm(),
          'wave_fore': bare_wave_fore(S['wave_fore'])}
    for gname in ('thigh', 'calf', 'pants_top'):
        sc[gname] = tint(S[gname], PANTS)
    with palette(**MUD_BOOT):
        sc['boot'] = A.boot().out()
    AC.dress(model, P, sc)
    # the sleeve top lowered like the hunter's (no cape over the shoulder any more): hunter.lower_sleeve_cap on the red sleeve
    keep = P.scene['upper']
    P.scene['upper'] = sc['upper']
    try:
        HU.lower_sleeve_cap(model, P)
    finally:
        P.scene['upper'] = keep
    boxes = {}
    cloth = dict(cloth='#e6d3b4', cloth_d='#c6ae88', line='#6e5434')
    trim = AC.Metal('#e6d3b4', '#c6ae88', '#8e7450', '#4e3a20')
    boxes['後領'] = AC.body_layer(model, P, '後領', AC.collar(False, trim=trim, **cloth).out(), .595, (6, 4))
    boxes['前領'] = AC.body_layer(model, P, '前領', AC.collar(True, trim=trim, **cloth).out(), .456, (8, 6))
    boxes['帽子'] = AC.head_layer(model, P, '帽子', straw_hat().out(), .004, (8, 8))
    AC.toggle(model, 'Acc:: Hat Off', ('帽子',))
    # textures: plaid on the red cloth, burlap on the vest, mud on the trousers' lower legs and the boots
    log = {}
    for n in ('上臂_R', '上臂_L', '揮手上臂_R', '揮手上臂_L', '胸腔', '襯衫下擺', '前領', '後領'):
        if n in model.parts:
            log[n] = plaid(model, n, 60 if '領' in n else 84)
    for n in ('背心_R', '背心_L'):
        weave(model, n, .12, seed=11 if n.endswith('R') else 12)
    for n, fy, amt, sd in (('小腿_R', .2, .55, 21), ('小腿_L', .2, .55, 22), ('大腿_R', .55, .35, 23), ('大腿_L', .55, .35, 24),
                           ('鞋_R', .0, .7, 25), ('鞋_L', .0, .7, 26)):
        mud(model, n, fy, amt, sd)
    return boxes, log


def build():
    model = Model(AC.FACE)
    with sync_playwright() as pw:
        P = B.Painter(pw)
        boxes, log = farmer(model, P)
        P.close()
    uid = {p['uuid'] for p in model.json['param']}
    for clip in model.clips.values():
        clip['lanes'] = [l for l in clip['lanes'] if l['uuid'] in uid]
    import head9 as H9
    H9.apply(model, B)
    B.clean_transparent(model)
    B.gc_textures(model)
    model.json['meta'].update(name=TITLE, artist='Claude (story_burly/art.py + shoe_v7/farmer.py, hand-drawn SVG)',
                              rigger='Claude (shoe_v7/farmer.py on burly_hand_v3)')
    model.path = AC.MODELS / f'{MID}.inp'
    import os
    import arm_rigid
    from story_squat70 import add_squat70
    add_squat70(model, log=lambda *a: None)
    arm_rigid.apply(model, log=lambda *a: None)
    old = os.environ.get('STORY_SQUAT70')
    os.environ['STORY_SQUAT70'] = '0'
    try:
        model.save()
    finally:
        if old is None:
            os.environ.pop('STORY_SQUAT70', None)
        else:
            os.environ['STORY_SQUAT70'] = old
    print(model.path, 'plaid', log)


def build_side():
    import side
    # 正面才有的層：講解手勢的指手、講解臂雙胞胎（2026-11-22 T12 起柏達克家族有講解臂_*），側面不用
    side.DROP_PARTS = tuple(dict.fromkeys(side.DROP_PARTS + ('指手_', '講解臂_')))
    side.BACK_HAIR_HAT_PTS = [(412, 108), (402, 124), (399, 146), (402, 166), (409, 182), (416, 194), (422, 188), (428, 198),
                              (435, 190), (442, 194), (449, 184), (455, 160), (459, 108)]    # 同獵人：戴帽只露帽簷下貼後頸的短髮
    side.LEG_THIN, side.BOOT_W = HU.LEG_THIN, HU.BOOT_W
    pal = dict(MUD_BOOT, **{k: PANTS(getattr(A, k)) for k in ('PANTS', 'PANTS_L', 'PANTS_D', 'PANTS_LINE')})
    try:
        with palette(**pal):
            side.build(front=MID, sid=f'{MID}_side', extra_torso=('後領', '前領'), title=TITLE + '・側面')
    finally:
        side.BACK_HAIR_HAT_PTS = None
        side.LEG_THIN, side.BOOT_W = 1.0, 1.0


if __name__ == '__main__':
    if '--side' in sys.argv:
        build_side()
    else:
        build()
