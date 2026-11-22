"""《鞋匠與小矮人》V7 小弟弟 shoe_kid_boyv3：少年亞瑟小孩模 arthur_boy_v3 的換裝（2026-11-22）。

    python -X utf8 tools/shoe_v7/kid.py            -> inochi2D-demo/models/shoe_kid_boyv3.inp
    python -X utf8 tools/story_think.py shoe_kid_boyv3   # 重建後要再套思考（kid.py 存檔只自動補講解）
    python -X utf8 tools/shoe_v7/kid_side.py

底圖 carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝/shoe_kid_boyv3_底圖_v1.png（淡紫亂髮、紅鼻子、米色粗布短袖、吊帶、
補丁深灰七分褲、赤腳）。讀 arthur_boy_v3，每層照原網格換貼圖、綁定不動；臉、眼、眉、頭髮一層都不動（光頭臉和小孩模相同）。
上色一律程式手繪（平滑圓柱漸層＋同色系等寬輪廓線），不拿底圖色階當部件：
  - 王冠、石中劍、握劍手／指、Arm:: Right:: Hold 拿掉；綠色長外套（背心_R／_L）拿掉。
  - 胸腔：米色粗布短袖上衣（開襟 V 領露膚色）＋兩條深棕吊帶與金屬扣；前領＝米色破領片；後領米色。
  - 袖子（上臂、揮手上臂、舉手上臂）：上半截米色短袖、毛邊袖口，下半截露出手臂；下臂、揮手前臂改成光手臂。
  - 褲頭、腰帶、大腿、小腿：深灰七分褲，褲腰扣子、膝蓋補丁、褲口毛邊。
  - 鞋：赤腳（小腿＋腳掌＋五根腳趾）。
  - 紅鼻子：獨立一層「紅鼻」，跟著鼻子動（換裝部件，不改素臉的鼻子）。
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (TOOLS, TOOLS / 'story_mix'):
    sys.path.insert(0, str(p))
import mix                                   # noqa: E402
from build_story_trio import set_part_image  # noqa: E402

MID, SRC = 'shoe_kid_boyv3', 'arthur_boy_v3'


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def ramp(stops, t):
    t = np.clip(t, 0, 1)
    xs = [s[0] for s in stops]
    cols = np.array([hexrgb(s[1]) for s in stops])
    return np.stack([np.interp(t, xs, cols[:, i]) for i in range(3)], -1)


SHIRT = [(0, '#8f8268'), (.35, '#b8ab8e'), (.7, '#d8ccb0'), (1, '#e8dfc8')]
SHIRT_LINE = '#5e523e'
PANTS = [(0, '#26261f'), (.35, '#36362c'), (.7, '#4a4a3d'), (1, '#5a5a4b')]
PANTS_LINE = '#15150f'
PATCH = [(0, '#2a2a30'), (.5, '#3c3b44'), (1, '#4c4b55')]
STRAP = [(0, '#2e241c'), (.5, '#4a3b2e'), (1, '#5e4c3c')]
SKIN_LINE = '#a4675a'


def arr_of(M, name):
    return np.asarray(mix._tex(M, M.parts[name]).convert('RGBA')).astype(float)


def put(M, name, rgb, alpha):
    img = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
    set_part_image(M, M.parts[name], Image.fromarray(img, 'RGBA'))


def soft(mask, s=.7):
    return np.clip(ndi.gaussian_filter(mask.astype(float), s) * 1.8 - .4, 0, 1)


def outline(rgb, mask, line, wpx, open_top=False, open_bottom=False):
    """line inside the mask edge; open ends (hidden joins) get no line"""
    pad = 40
    mm = np.pad(mask, ((pad, pad), (0, 0)))
    if open_top:
        mm[:pad] = mm[pad]
    if open_bottom:
        mm[-pad:] = mm[-pad - 1]
    d = ndi.distance_transform_edt(mm)[pad:-pad]
    ol = np.clip(1 - (d - .5) / wpx, 0, 1) * .9 * mask
    return rgb * (1 - ol[..., None]) + hexrgb(line) * ol[..., None]


def frame(mask):
    """principal axis of a limb mask: (mean, d along, n across); d points down the image"""
    ys, xs = np.nonzero(mask)
    P = np.stack([xs, ys], 1).astype(float)
    m = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - m).T))
    d = v[:, np.argmax(w)]
    if d[1] < 0:
        d = -d
    return m, d, np.array([-d[1], d[0]])


def tube(mask, k_of_t, lo=0.0, hi=1.0, smooth=15, hw=None):
    """a clean tube along the mask's axis: per position t the centre of the old mask, half width × k(t).
    returns (new mask, t in 0..1 along, u in 0..1 across)"""
    H, W = mask.shape
    m, d, n = frame(mask)
    yy, xx = np.mgrid[0:H, 0:W]
    T = (xx - m[0]) * d[0] + (yy - m[1]) * d[1]
    S = (xx - m[0]) * n[0] + (yy - m[1]) * n[1]
    tv, sv = T[mask], S[mask]
    t0, t1 = tv.min(), tv.max()
    nb = max(8, int(t1 - t0))
    bins = np.clip(((tv - t0) / (t1 - t0 + 1e-6) * nb).astype(int), 0, nb - 1)
    smin = np.full(nb, np.nan)
    smax = np.full(nb, np.nan)
    for b in range(nb):
        q = sv[bins == b]
        if len(q):
            smin[b], smax[b] = q.min(), q.max()
    ok = ~np.isnan(smin)
    idx = np.arange(nb)
    smin = np.interp(idx, idx[ok], smin[ok])
    smax = np.interp(idx, idx[ok], smax[ok])
    c = ndi.uniform_filter1d((smin + smax) / 2, smooth, mode='nearest')
    h = ndi.uniform_filter1d((smax - smin) / 2, smooth, mode='nearest')
    tt = (T - t0) / (t1 - t0 + 1e-6)
    bi = np.clip((tt * nb).astype(int), 0, nb - 1)
    kk = k_of_t(np.clip(tt, 0, 1))
    hh = h[bi] * kk if hw is None else hw(np.clip(tt, 0, 1)) * kk   # hw: absolute half width (texture px) along t
    new = (np.abs(S - c[bi]) <= hh) & (tt >= lo) & (tt <= hi)
    u = (S - c[bi] + hh) / np.maximum(1, 2 * hh)
    if n[0] < 0:
        u = 1 - u
    return new, tt, np.clip(u, 0, 1)


def cyl(u, stops, peak=.32):
    return ramp(stops, .25 + .7 * np.exp(-((u - peak) / .3) ** 2))


def skin_stops(M):
    a = arr_of(M, '手掌_R')
    on = a[..., 3] > 200
    c = np.median(a[..., :3][on], 0)
    dk, lt = c * .8, np.minimum(255, c * 1.06 + 6)
    f = lambda v: '#%02x%02x%02x' % tuple(int(x) for x in v)
    return [(0, f(c * .7)), (.4, f(dk)), (.75, f(c)), (1, f(lt))]


def fray(s, period=9.0, amp=3.0):
    """zig-zag offset along the cut line"""
    ph = (s / period) % 1
    return amp * (np.abs(ph - .5) * 2 - .5) + amp * .35 * np.sin(s * .9)


# ============================================================================================ arms
# 2026-11-22 統籌：「小弟弟手臂太細太長像竹竿、手肘關節明顯……手腕不可比前臂粗」→ 寬度照底圖量（底圖 px，垂直於手臂量）：
# 袖口下的上臂約 56、手肘約 48、前臂上段約 46、手腕約 38（換裝底圖的軀幹比小孩模寬約 1.4 倍，所以寫進模型時依軀幹比例放大）；前臂上端不畫線、和上臂下端同寬，手肘看不出接縫；手掌上緣收到手腕寬。
UP_HW = (38.0, 33.0)     # 上臂露出段：袖口下 → 手肘（半寬，模型底圖 px；小孩模軀幹比換裝底圖窄，手臂和軀幹的比例照底圖放大）
FORE_HW = (33.0, 25.0)   # 前臂：手肘 → 手腕


def ppb(M, name, H):
    """texture px per base px (arms hang roughly vertically at rest)"""
    b = mix.wbox(M, M.parts[name])
    return H / ((b[3] - b[1]) / 1.3)


def edge_line(rgb, region, long_region, line, wpx):
    """outline of `region` drawn only along the edges of `long_region` (the limb extended past its joint ends): no line
    across the joint ends, so elbow and wrist joins show no seam"""
    d = ndi.distance_transform_edt(long_region)
    ol = np.clip(1 - (d - .5) / wpx, 0, 1) * .9 * region
    return rgb * (1 - ol[..., None]) + hexrgb(line) * ol[..., None]


def sleeve_arm(M, name, cut=.5):
    """upper arm: beige short sleeve (a little wider than the arm) down to `cut` (frayed hem), bare arm below"""
    a = arr_of(M, name)
    mask = a[..., 3] > 100
    H, W = mask.shape
    k = ppb(M, name, H)
    sl, tt, u = tube(mask, lambda t: np.ones_like(t), hw=lambda t: k * UP_HW[0] * 1.22 + 0 * t)
    sl &= ndi.binary_dilation(mask, iterations=int(k * 14))
    hw = lambda t: k * (UP_HW[0] + (UP_HW[1] - UP_HW[0]) * np.clip((t - cut) / (1 - cut), 0, 1))
    ar, tt2, u2 = tube(mask, lambda t: np.ones_like(t), hi=.9, hw=hw, smooth=61)     # the old sleeve's flared cuff at the bottom is not followed
    along, _, _ = tube(mask, lambda t: np.ones_like(t), lo=-1, hi=3, hw=hw, smooth=61)
    scale = W / 120
    m, d, n = frame(mask)
    yy, xx = np.mgrid[0:H, 0:W]
    S = (xx - m[0]) * n[0] + (yy - m[1]) * n[1]
    hem = tt < cut + fray(S, 9 * scale, 2.6 * scale) / max(1, H)
    sleeve = sl & hem
    arm = ar & ~sleeve & (tt > cut - .06)
    rgb = np.zeros((H, W, 3))
    rgb[arm] = cyl(u2, SKIN)[arm]
    rgb = edge_line(rgb, arm, along, SKIN_LINE, 1.6 * scale)
    srgb = outline(cyl(u, SHIRT), sleeve, SHIRT_LINE, 1.8 * scale)
    rgb[sleeve] = srgb[sleeve]
    alpha = np.maximum(soft(arm), soft(sleeve))
    put(M, name, rgb, alpha)


def bare_forearm(M, name, cap=.06, fade=.12):
    a = arr_of(M, name)
    mask = a[..., 3] > 100
    H, W = mask.shape
    k = ppb(M, name, H)
    hw = lambda t: k * (FORE_HW[0] + (FORE_HW[1] - FORE_HW[0]) * np.clip(t, 0, 1))
    ar, tt, u = tube(mask, lambda t: np.sqrt(np.clip(1 - ((cap - np.minimum(t, cap)) / cap) ** 2, .35, 1)), hw=hw)
    along, _, _ = tube(mask, lambda t: np.ones_like(t), lo=-1, hi=3, hw=hw)
    rgb = edge_line(cyl(u, SKIN), ar, along, SKIN_LINE, 1.6 * W / 120)
    alpha = soft(ar) * np.clip((1 - tt) / fade, 0, 1)        # the wrist end fades into the hand underneath (same skin)
    put(M, name, rgb, alpha)


def trim_hand(M, name, top=.22, full=.5):
    """the hand's top edge narrowed to the wrist (the old cuff hid a wide top): never wider than the forearm's end"""
    a = arr_of(M, name)
    mask = a[..., 3] > 30
    H, W = mask.shape
    k = ppb(M, name, H)
    rows = np.where(mask.any(1))[0]
    r0, r1 = rows[0], rows[-1]
    yy, xx = np.mgrid[0:H, 0:W]
    lim = np.full(H, 1e9)
    for r in range(r0, r1 + 1):
        c = np.where(mask[r])[0]
        f = (r - r0) / max(1, r1 - r0)
        if f < full:
            g = np.clip((f - top) / (full - top), 0, 1)
            lim[r] = k * FORE_HW[1] * 1.0 + g * 60 * k
    cen = np.array([np.where(mask[r])[0].mean() if mask[r].any() else W / 2 for r in range(H)])
    cen = ndi.uniform_filter1d(cen, 15)
    keep = np.abs(xx - cen[:, None]) <= lim[:, None]
    alpha = a[..., 3] / 255 * np.clip(lim[:, None] + 1 - np.abs(xx - cen[:, None]), 0, 1)
    put(M, name, a[..., :3], alpha)


def wave_fore(M, name):
    """揮手前臂: the drawn hand stays, the green cuff + sleeve become a bare forearm"""
    a = arr_of(M, name)
    rgb0, al = a[..., :3], a[..., 3] > 100
    r, g, b = rgb0[..., 0], rgb0[..., 1], rgb0[..., 2]
    green = al & (g > r + 8)
    dark = al & (rgb0.sum(-1) < 200) & ~green
    green = ndi.binary_closing(green | (dark & ndi.binary_dilation(green, iterations=3)), iterations=2)
    hand = al & ~green & (r > 140) & (r >= g) & (g >= b - 10) & (r - b < 120)
    hand = ndi.binary_closing(hand, iterations=1) & al & ~green
    hand = ndi.binary_opening(hand, iterations=1) & ~((r > 180) & (g > 120) & (b < 110))   # no cuff button
    H, W = al.shape
    k = ppb(M, name, H) * .5
    ar, tt, u = tube(green, lambda t: np.ones_like(t), hw=lambda t: k * (FORE_HW[0] + (FORE_HW[1] - FORE_HW[0]) * t) * 2)
    ar &= ~hand
    rgb = outline(cyl(u, SKIN), ar, SKIN_LINE, 1.6 * W / 120, open_bottom=True)
    rgb[hand] = rgb0[hand]
    put(M, name, rgb, np.maximum(soft(ar), hand * (a[..., 3] / 255)))


# ============================================================================================ torso
def shirt(M):
    a = arr_of(M, '胸腔')
    mask = a[..., 3] > 100
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    u = xx
    rgb = ramp(SHIRT, .3 + .65 * np.exp(-((u - .42) / .42) ** 2))
    # soft vertical folds
    rgb *= (1 - .06 * np.exp(-((u - .3) / .02) ** 2) * (yy > .35) - .06 * np.exp(-((u - .66) / .02) ** 2) * (yy > .4))[..., None]
    # V neck (skin) + placket line
    vneck = (np.abs(u - .5) < .11 * (1 - yy / .3)) & (yy < .3)
    rgb[vneck] = ramp(SKIN, .55 + .3 * (1 - yy[vneck] / .3))
    rgb = outline(rgb, ~vneck & mask, SHIRT_LINE, 1.6)
    line = (np.abs(u - .5) < .004) & (yy > .29) & (yy < .55)
    rgb[line] = hexrgb(SHIRT_LINE)
    # suspenders
    for cx in (.25, .75):
        st = (np.abs(u - cx) < .045) & mask
        srgb = ramp(STRAP, .3 + .7 * np.exp(-((u - cx + .015) / .03) ** 2))
        rgb[st] = srgb[st]
        edge = (np.abs(np.abs(u - cx) - .045) < .006) & mask
        rgb[edge] = (18, 14, 10)
        # buckle
        bk = (np.abs(u - cx) < .03) & (np.abs(yy - .62) < .02)
        rgb[bk] = (150, 150, 140)
        bk2 = (np.abs(u - cx) < .017) & (np.abs(yy - .62) < .009)
        rgb[bk2] = hexrgb(STRAP[1][1])
    rgb = outline(rgb, mask, SHIRT_LINE, 2.0)
    put(M, '胸腔', rgb, soft(mask))


def collar_front(M):
    a = arr_of(M, '前領')
    H, W = a.shape[:2]
    S = 4
    im = Image.new('L', (W * S, H * S), 0)
    dr = ImageDraw.Draw(im)
    w, h = W * S, H * S
    # two ragged collar flaps either side of the V
    for sgn in (-1, 1):
        cx = w / 2
        pts = [(cx + sgn * w * .06, 0), (cx + sgn * w * .44, 0), (cx + sgn * w * .40, h * .30), (cx + sgn * w * .30, h * .38),
               (cx + sgn * w * .26, h * .31), (cx + sgn * w * .16, h * .42), (cx + sgn * w * .04, h * .30)]
        dr.polygon(pts, fill=255)
    m = np.asarray(im.resize((W, H), Image.LANCZOS)) / 255.0
    mask = m > .5
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    rgb = ramp(SHIRT, .55 + .4 * (1 - yy) - .25 * np.abs(xx - .5))
    rgb = outline(rgb, mask, SHIRT_LINE, 1.8)
    put(M, '前領', rgb, m)


def collar_back(M):
    a = arr_of(M, '後領')
    mask = a[..., 3] > 100
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    rgb = outline(ramp(SHIRT, .2 + .3 * yy), mask, SHIRT_LINE, 1.8)
    put(M, '後領', rgb, soft(mask))


# ============================================================================================ pants
def pants_tex(mask, u, extra=None, scale=1.0, top=True, bottom=True):
    rgb = cyl(u, PANTS, .38)
    rng = np.random.default_rng(7)
    noise = ndi.gaussian_filter(rng.normal(0, 1, mask.shape), 1.2) * 4
    rgb = rgb + noise[..., None]
    return outline(rgb, mask, PANTS_LINE, 1.8 * scale, open_top=top, open_bottom=bottom)


def stitch_patch(rgb, H, W, box, scale):
    x0, y0, x1, y1 = (box[0] * W, box[1] * H, box[2] * W, box[3] * H)
    yy, xx = np.mgrid[0:H, 0:W]
    pm = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    rgb[pm] = ramp(PATCH, .5 + .4 * (xx[pm] - x0) / max(1, x1 - x0))
    bd = pm & ~((xx >= x0 + 2 * scale) & (xx <= x1 - 2 * scale) & (yy >= y0 + 2 * scale) & (yy <= y1 - 2 * scale))
    rgb[bd] = (20, 20, 22)
    # cross stitches across the edges
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    st = 9 * scale
    for x in np.arange(x0 + st / 2, x1, st):
        for y in (y0, y1):
            dr.line([(x, y - 3.5 * scale), (x, y + 3.5 * scale)], fill=(18, 18, 16), width=max(1, int(1.3 * scale)))
    for y in np.arange(y0 + st / 2, y1, st):
        for x in (x0, x1):
            dr.line([(x - 3.5 * scale, y), (x + 3.5 * scale, y)], fill=(18, 18, 16), width=max(1, int(1.3 * scale)))
    return np.asarray(im).astype(float)


def pants_part(M, name, patch=None, hem=False):
    a = arr_of(M, name)
    mask = a[..., 3] > 100
    H, W = mask.shape
    scale = W / 160
    yy, xx = np.mgrid[0:H, 0:W]
    cols = np.where(mask.any(0))[0]
    u = np.clip((xx - cols[0]) / max(1, cols[-1] - cols[0]), 0, 1)
    if hem:
        rows = np.where(mask.any(1))[0]
        cut = rows[-1] - 5 * scale + fray(xx.astype(float), 11 * scale, 4 * scale)
        mask = mask & (yy < cut)
    rgb = pants_tex(mask, u, scale=scale, bottom=not hem)
    if patch:
        rgb = stitch_patch(rgb, H, W, patch, scale)
        rgb = outline(rgb, mask, PANTS_LINE, 1.8 * scale, open_top=True, open_bottom=not hem)
    put(M, name, rgb, soft(mask))


def waistband(M):
    a = arr_of(M, '腰帶')
    mask0 = a[..., 3] > 100
    H, W = mask0.shape
    cols = np.where(mask0.any(0))[0]
    full = mask0[:, cols[0] + 2:cols[-1] - 1].all(1)          # rows the band crosses end to end (no buckle / loop tabs)
    rows = np.where(full)[0]
    mid, half = (rows[0] + rows[-1]) / 2, (rows[-1] - rows[0]) / 2 * .8
    yy0 = np.arange(H)[:, None]
    mask = mask0 & (np.abs(yy0 - mid) <= half) & np.ones((1, W), bool)
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    rgb = ramp(PANTS, .45 + .35 * np.exp(-((xx - .45) / .4) ** 2) - .15 * yy)
    for cx in (.25, .75):                  # suspender clips
        lp = (np.abs(xx - cx) < .012) & mask
        rgb[lp] = (20, 20, 16)
    btn = ((xx - .5) * W) ** 2 + ((yy - mid / H) * H) ** 2 < (half * .55) ** 2
    rgb[btn] = (78, 76, 66)
    rgb = outline(rgb, mask, PANTS_LINE, 1.6)
    put(M, '腰帶', rgb, soft(mask))


def pants_top(M):
    a = arr_of(M, '褲頭')
    mask = a[..., 3] > 100
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    u = xx / W
    rgb = pants_tex(mask, u, scale=W / 300, top=False)
    fly = (np.abs(u - .5) < .003 + 0 * yy) & (yy < H * .55)
    rgb[fly] = hexrgb(PANTS_LINE)
    put(M, '褲頭', rgb, soft(mask))


def drop_band(M):
    """the old belt sat on the coat's waist; the shirt hangs lower, so the waistband moves down to the shirt's hem"""
    sb = mix.wbox(M, M.parts['胸腔'])
    bb = mix.wbox(M, M.parts['腰帶'])
    dy = (sb[3] - (bb[3] - bb[1]) * .35) - (bb[1] + bb[3]) / 2
    M.parts['腰帶']['transform']['trans'][1] += dy
    print('waistband dy', round(dy, 1))


# ============================================================================================ feet
def bare_foot(M, name, mirror):
    a = arr_of(M, name)
    H, W = a.shape[:2]
    S = 4
    w, h = W * S, H * S
    im = Image.new('L', (w, h), 0)
    dr = ImageDraw.Draw(im)
    sg = -1 if mirror else 1
    cx = w * (.47 if not mirror else .53)
    sh = w * .21                                         # shin half width
    # shin, widening into the ankle and foot (front view, toes towards the camera)
    dr.polygon([(cx - sh, 0), (cx + sh, 0), (cx + sh * .92, h * .55), (cx + sh * 1.15, h * .70),
                (cx - sh * 1.05, h * .70), (cx - sh * .95, h * .55)], fill=255)
    fx = cx - sg * w * .06                               # the foot points a little outwards
    dr.ellipse([fx - w * .27, h * .66, fx + w * .27, h * .965], fill=255)
    m = np.asarray(im.resize((W, H), Image.LANCZOS)) / 255.0
    mask = m > .5
    yy, xx = np.mgrid[0:H, 0:W]
    u = np.clip((xx - (cx - sh * 1.4) / S) / (sh * 2.8 / S), 0, 1)
    rgb = cyl(u, SKIN, .4)
    # ankle bones
    for ox in (-.8, .8):
        ab = ((xx - (cx + ox * sh) / S) ** 2 + (yy - H * .63) ** 2) < (W * .035) ** 2
        rgb[ab] *= .94
    rgb = outline(rgb, mask, SKIN_LINE, 1.8 * W / 160)
    # toes: five rounded bumps along the front edge, big toe on the inner side
    im2 = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    d2 = ImageDraw.Draw(im2)
    toes = [(.0, .085), (.115, .068), (.215, .06), (.305, .054), (.385, .048)]
    toe_y = H * .905
    inner = fx / S + sg * W * .21                        # big toe sits towards the body's centre line
    toe_masks = []
    for off, r in toes:
        tx = inner - sg * off * W
        rr = r * W
        d2.ellipse([tx - rr, toe_y - rr * 1.1, tx + rr, toe_y + rr * .9], fill=tuple(int(v) for v in ramp(SKIN, np.array(.8))),
                   outline=tuple(int(v) for v in hexrgb(SKIN_LINE)), width=max(1, int(W / 110)))
        d2.ellipse([tx - rr * .45, toe_y - rr * .2, tx + rr * .45, toe_y + rr * .55], fill=(236, 196, 186))
        tm = Image.new('L', (W, H), 0)
        ImageDraw.Draw(tm).ellipse([tx - rr, toe_y - rr * 1.1, tx + rr, toe_y + rr * .9], fill=255)
        toe_masks.append(np.asarray(tm) > 127)
    rgb = np.asarray(im2).astype(float)
    full = mask.copy()
    for t in toe_masks:
        full |= t
    put(M, name, rgb, np.maximum(m, soft(full)))


# ============================================================================================ nose
def red_nose(M):
    src = M.parts['鼻子']
    part = deepcopy(src)
    part.update(uuid=M.uuid, name='紅鼻', masks=[], opacity=1, children=[])
    M.uuid += 1
    parent = M.parents[src['uuid']]
    parent['children'].append(part)
    M.parents[part['uuid']] = parent
    M.parts['紅鼻'] = part
    for prm in M.params.values():
        prm['bindings'] += [dict(deepcopy(b), node=part['uuid']) for b in prm['bindings'] if b['node'] == src['uuid']]
    a = arr_of(M, '鼻子')
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    al = a[..., 3] > 60
    ys, xs = np.nonzero(al)
    cx, cy = xs.mean(), ys.max() - H * .12
    r = min(W, H) * .42
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.1) ** 2) / r
    alpha = np.clip(1.3 - d, 0, 1) ** .7 * .95
    rgb = np.zeros((H, W, 3))
    rgb[:] = hexrgb('#e2737a')
    hl = np.exp(-(((xx - cx + r * .3) ** 2 + (yy - cy + r * .35) ** 2) / (r * .22) ** 2))
    rgb = rgb * (1 - hl[..., None] * .6) + 255 * hl[..., None] * .6
    put(M, '紅鼻', rgb, alpha)
    part['zsort'] = src['zsort'] + .002          # behind the nose line, in front of the face


def build():
    global SKIN
    M = mix.load(SRC)
    SKIN = skin_stops(M)
    for n in ('王冠', '石中劍', '握劍手_R', '握劍指_R', '背心_R', '背心_L'):
        if n in M.parts:
            mix.drop_node(M, n)
    if 'Arm:: Right:: Hold' in M.params:
        mix.drop_param(M, 'Arm:: Right:: Hold')
    M.json['meta'].pop('heldProps', None)
    for s in 'RL':
        sleeve_arm(M, f'上臂_{s}', .48)
        sleeve_arm(M, f'揮手上臂_{s}', .48)
        if f'舉手上臂_上臂_{s}' in M.parts:
            sleeve_arm(M, f'舉手上臂_上臂_{s}', .48)
        bare_forearm(M, f'下臂_{s}')
        wave_fore(M, f'揮手前臂_{s}')
        trim_hand(M, f'手掌_{s}')
        bare_foot(M, f'鞋_{s}', s == 'L')
    shirt(M)
    collar_front(M)
    collar_back(M)
    waistband(M)
    pants_top(M)
    pants_part(M, '大腿_R', patch=(.12, .62, .62, .86))
    pants_part(M, '大腿_L', patch=(.55, .30, .92, .52))
    pants_part(M, '小腿_R', hem=True)
    pants_part(M, '小腿_L', hem=True)
    drop_band(M)
    red_nose(M)
    M.json['meta'].update(name='小弟弟（鞋匠與小矮人 V7，少年亞瑟小孩模換裝）', shoeV7=dict(base=SRC, date='2026-11-22'))
    print(mix.save(M, MID))
    return M


if __name__ == '__main__':
    build()
