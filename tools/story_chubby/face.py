"""胖大叔光頭臉（2026-11-23，照 story_tareme/face.py 複製改寫；垂眼姐姐的檔不動）：從參考圖（底圖露出的眼、鼻、嘴＋Gemini 光頭參考的頭殼、眉、耳）量出臉型、耳朵、雙眼、眉、鼻、嘴的形狀，
寫成每個圖層的乾淨手繪 SVG。

    python -X utf8 inochi2D-demo/tools/story_chubby/face.py      -> story_chubby/face_trace.json（art.py／build.py 讀這個檔）

做法同卡洛兒 carol_face_trace.py、柏達克 face_trace.py（skill story-handpaint-alignment「乾淨畫法」）：
  - 只取「形狀」：參考圖用 verify_tareme_bald_match.features 的同一套規則量出遮罩，外輪廓沿線平滑成向量路徑；
  - 上色一律手繪：平滑漸層（虹膜放射漸層＋上方陰影＋瞳孔＋兩顆高光；臉的柔和明暗）、等寬圓頭的線，不貼像素、不色階化；
  - 兩眼各自量，不鏡像（雙眼取自底圖本身）；左右耳、左右眉也各自量；眼睛畫全：上眼線、下眼瞼線、眼白、虹膜、瞳孔、高光；
  - 脖子不量（標準脖子在 art.py）；臉的下緣＝光頭參考逐欄量到的下顎線。
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_chubby_bald_match as V   # noqa: E402

K, F = V.K, V.FRAME
OUT = HERE / 'face_trace.json'
AXIS = 513.5

SKIN, SKIN_L, SKIN_D, SKIN_DD = '#fbd8c2', '#fde6d6', '#f0c0a6', '#dc9c84'
LINE = '#3b2620'
LASH, LASH_D = '#2a1a14', '#1a0f0a'
BROW = '#6e4d36'
OUTLINE_W = 6.4
SHADE_PX = 0.8
MUST, MUST_L, MUST_D = '#7a5a46', '#93725b', '#4d3528'


def to_base(c):
    return F[0] + (c[0] + .5) / K, F[1] + (c[1] + .5) / K


def fnum(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def bez(pts, closed=True):
    """Catmull-Rom through pts as cubic beziers"""
    P = [np.asarray(p, float) for p in pts]
    n = len(P)
    if n < 3:
        return ''
    g = (lambda i: P[i % n]) if closed else (lambda i: P[min(n - 1, max(0, i))])
    out = [f'M{fnum(P[0][0])} {fnum(P[0][1])}']
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        out.append(f'C{fnum(c1[0])} {fnum(c1[1])} {fnum(c2[0])} {fnum(c2[1])} {fnum(p2[0])} {fnum(p2[1])}')
    return ' '.join(out) + ('Z' if closed else '')


def contour_pts(mask, sigma=1.2, step=3, min_area=20):
    """outer contours of a K-scale mask, smoothed along their length, base px"""
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < min_area * K * K / 16:
            continue
        c = c[:, 0, :].astype(float)
        k = max(1, int(sigma * K * 3))
        w = np.exp(-.5 * (np.arange(-k, k + 1) / (sigma * K)) ** 2)
        w /= w.sum()
        ext = np.vstack([c[-k:], c, c[:k]])
        sm = np.stack([np.convolve(ext[:, i], w, 'valid') for i in (0, 1)], 1)
        out.append([to_base(p) for p in sm[::step]])
    return out


def mask_d(mask, sigma=1.2, step=3, min_area=20):
    return ' '.join(bez(p) for p in contour_pts(mask, sigma, step, min_area))


def ring_d(mask, sigma=1.2, step=2, min_area=12):
    """a line mask with holes (closed rings) as one evenodd path: every contour (outer and inner), smoothed"""
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if abs(cv2.contourArea(c)) < min_area * K * K / 16 or len(c) < 8:
            continue
        c = c[:, 0, :].astype(float)
        k = max(1, int(sigma * K * 3))
        w = np.exp(-.5 * (np.arange(-k, k + 1) / (sigma * K)) ** 2)
        w /= w.sum()
        ext = np.vstack([c[-k:], c, c[:k]])
        sm = np.stack([np.convolve(ext[:, i], w, 'valid') for i in (0, 1)], 1)
        out.append(bez([to_base(p) for p in sm[::step]]))
    return ' '.join(out)


def region(M, b):
    z = np.zeros(M['rf']['ink'].shape, bool)
    z[V.box(b)] = True
    return z


def line_mask(M, region, open_it=1, min_px=40):
    """the reference's dark line pixels in a region (K scale), cleaned: small specks dropped"""
    ink = M['rf']['ink'] & region
    ink = ndi.binary_opening(ink, iterations=open_it)
    lab, n = ndi.label(ink)
    if n:
        sizes = ndi.sum(ink, lab, range(1, n + 1))
        ink = np.isin(lab, 1 + np.nonzero(sizes > min_px * K * K / 16)[0])
    return ink


def centreline(mask, min_len=4):
    """thin a K-scale line mask into ordered base-px polylines"""
    sk = skeletonize(mask.astype(bool))
    lab, n = ndi.label(sk, structure=np.ones((3, 3)))
    lines = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < min_len * K:
            continue
        pts = np.stack([xs, ys], 1).astype(float)
        # order along the principal axis
        c = pts.mean(0)
        u, s_, vt = np.linalg.svd(pts - c, full_matrices=False)
        t = (pts - c) @ vt[0]
        order = np.argsort(t)
        P = pts[order]
        # bin into ~1.5 base px steps
        tt = t[order]
        bins = np.arange(tt.min(), tt.max() + 1e-6, 1.5 * K)
        Q = []
        for a, b in zip(bins, bins[1:]):
            sel = (tt >= a) & (tt < b + 1e-9)
            if sel.any():
                Q.append(P[sel].mean(0))
        if len(Q) >= 2:
            lines.append([to_base(q) for q in Q])
    return lines


def thickness(mask):
    """mean stroke width (base px) of a line mask"""
    if not mask.any():
        return 1.0
    dt = ndi.distance_transform_edt(mask)
    sk = skeletonize(mask.astype(bool))
    v = dt[sk]
    return float(2 * v.mean() / K) if len(v) else 1.0


def mean_rgb(img, mask):
    if not mask.any():
        return np.array([128, 128, 128.])
    return img[mask].mean(0)


def hexc(c):
    c = np.clip(np.asarray(c, float), 0, 255).astype(int)
    return '#%02x%02x%02x' % tuple(c[:3])


class Defs:
    def __init__(self, pre):
        self.pre, self.items, self.n = pre, [], 0

    def uid(self, k):
        self.n += 1
        return f'{self.pre}_{k}{self.n}'

    def lin(self, x1, y1, x2, y2, stops):
        i = self.uid('g')
        s = ''.join(f'<stop offset="{o}" stop-color="{c}"' + (f' stop-opacity="{a[0]}"' if a else '') + '/>' for o, c, *a in stops)
        self.items.append(f'<linearGradient id="{i}" gradientUnits="userSpaceOnUse" x1="{fnum(x1)}" y1="{fnum(y1)}" x2="{fnum(x2)}" y2="{fnum(y2)}">{s}</linearGradient>')
        return f'url(#{i})'

    def rad(self, cx, cy, r, stops, fx=None, fy=None, ry=None):
        i = self.uid('r')
        s = ''.join(f'<stop offset="{o}" stop-color="{c}"' + (f' stop-opacity="{a[0]}"' if a else '') + '/>' for o, c, *a in stops)
        foc = f' fx="{fnum(fx)}" fy="{fnum(fy)}"' if fx is not None else ''
        tr = f' gradientTransform="translate({fnum(cx)} {fnum(cy)}) scale(1 {fnum(ry / r)}) translate({fnum(-cx)} {fnum(-cy)})"' if ry else ''
        self.items.append(f'<radialGradient id="{i}" gradientUnits="userSpaceOnUse" cx="{fnum(cx)}" cy="{fnum(cy)}" r="{fnum(r)}"{foc}{tr}>{s}</radialGradient>')
        return f'url(#{i})'

    def blur(self, sd):
        i = self.uid('b')
        self.items.append(f'<filter id="{i}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{sd}"/></filter>')
        return f'url(#{i})'

    def clip(self, d):
        i = self.uid('c')
        self.items.append(f'<clipPath id="{i}"><path d="{d}"/></clipPath>')
        return f'url(#{i})'

    def wrap(self, gid, body):
        return f'<g id="{gid}"><defs>{"".join(self.items)}</defs>{body}</g>'


def stroke(pts, colour, w, op=None, cap='round'):
    if len(pts) < 2:
        return ''
    o = f' opacity="{op}"' if op is not None else ''
    return f'<path d="{bez(pts, False)}" fill="none" stroke="{colour}" stroke-width="{fnum(w)}" stroke-linecap="{cap}" stroke-linejoin="round"{o}/>'


def taper(pts, w0, w1, wmid=None):
    """a filled stroke whose width goes w0 -> wmid -> w1 along pts (both ends tapered)"""
    P = np.array(pts, float)
    n = len(P)
    if n < 2:
        return ''
    if wmid is None:
        wmid = max(w0, w1)
    L, R = [], []
    for i in range(n):
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        d = b - a
        d /= (np.hypot(*d) + 1e-9)
        nrm = np.array([-d[1], d[0]])
        s = i / (n - 1)
        w = (w0 + (wmid - w0) * s * 2) if s < .5 else (wmid + (w1 - wmid) * (s - .5) * 2)
        L.append(P[i] + nrm * w / 2)
        R.append(P[i] - nrm * w / 2)
    return bez(L + R[::-1])


# ---------------------------------------------------------------- measure
def jaw_curve():
    xs = [p[0] for p in V.JAW_PTS]
    ys = [p[1] for p in V.JAW_PTS]
    return lambda x: float(np.interp(x, xs, ys))


EAR_CUT = {'R': ([224, 250, 270, 290, 306], [403.5, 407.0, 408.5, 409.5, 411.0]),
           'L': ([224, 250, 270, 290, 306], [623.5, 620.0, 618.5, 617.5, 616.0])}


def measure():
    bald = V.big(V.BALD)
    ref, _ = V.reference()
    rf = V.features(ref)
    H, W = bald.shape[:2]
    hue, sat, val = V.hsv(bald)
    grey = (sat < .1) & (np.abs(val - .5) < .07)
    sil = ndi.binary_fill_holes(ndi.binary_opening(~grey, iterations=2))
    yy, xx = np.mgrid[0:H, 0:W]
    bx, by = F[0] + (xx + .5) / K, F[1] + (yy + .5) / K
    jaw = np.interp(bx, [p[0] for p in V.JAW_PTS], [p[1] for p in V.JAW_PTS], left=300, right=300)
    head = sil & (by < jaw + 1.2) & (by > 81)
    lab, n = ndi.label(head)
    head = lab == 1 + int(np.argmax(ndi.sum(head, lab, range(1, n + 1))))
    cutR = np.interp(by, *EAR_CUT['R'])
    cutL = np.interp(by, *EAR_CUT['L'])
    earzone = (by > 222) & (by < 308)
    ear_R = head & earzone & (bx < cutR)
    ear_L = head & earzone & (bx > cutL)
    face = head & ~ear_R & ~ear_L
    # ears: reach under the face a little (they sit behind it), so no gap opens on a head turn
    ear_R = ear_R | (head & earzone & (bx < cutR + 6))
    ear_L = ear_L | (head & earzone & (bx > cutL - 6))
    return dict(bald=bald, ref=ref, rf=rf, face=face, ear_R=ear_R, ear_L=ear_L, by=by, bx=bx)


# ---------------------------------------------------------------- draw
def face_group(M):
    D = Defs('fc')
    # (r8) the outline is the reference's own outline line (its dark ring just inside the skin); the skin stops at the
    # line's outer edge (no pale rim outside the outline): a skin pixel near the edge goes when it lies outside the nearest
    # ring pixel (nearer the background than that ring pixel's own outer edge)
    fm0 = M['face']
    band = ndi.binary_dilation(fm0, iterations=2 * K) & ~ndi.binary_erosion(fm0, iterations=12 * K)
    ring = line_mask(M, band, 1, 200)
    dt_out = ndi.distance_transform_edt(fm0)
    dist_r, (iy_, ix_) = ndi.distance_transform_edt(~ring, return_indices=True)
    depth = dt_out[iy_, ix_]
    cut = fm0 & ~ring & (dist_r < 8 * K) & (dt_out < depth - 1.6 * K)
    fm = ndi.binary_opening(fm0 & ~cut, iterations=K)
    lab_, n_ = ndi.label(fm)
    fm = lab_ == 1 + int(np.argmax(ndi.sum(fm, lab_, range(1, n_ + 1))))
    d = mask_d(fm, 2.0, 3, 400)
    pts = contour_pts(fm, 2.0, 3, 400)[0]
    ys = [p[1] for p in pts]
    top, bot = min(ys), max(ys)
    fill = D.lin(0, top, 0, bot, [(0, SKIN_L), (.55, SKIN), (1, SKIN_D)])
    cl = D.clip(d)
    blur = D.blur(9)
    # soft modelling: temples a touch darker, the jaw underside shaded (to the chin), a light forehead
    inside = (f'<ellipse cx="{AXIS}" cy="{top + 50}" rx="55" ry="38" fill="{SKIN_L}" opacity=".6" filter="{blur}"/>'
              f'<path d="M{F[0]} {bot - 30} Q{AXIS} {bot + 24} {F[2]} {bot - 30} L{F[2]} {bot + 20} L{F[0]} {bot + 20}Z" fill="{SKIN_D}" opacity=".45" filter="{D.blur(5)}"/>')
    # the outline: one even line just inside the silhouette (the reference's ring lies inside the skin)
    inset = [(x + (AXIS - x) * .012, y + (1 if y < top + 20 else 0) * 1.2) for x, y in pts]
    # (r2) the outline: the reference's own outline line (its dark ring just inside the skin), as one clean smoothed shape
    body = (f'<path d="{d}" fill="{fill}"/><g clip-path="{cl}">{inside}'
            f'<path d="{d}" fill="none" stroke="{SKIN_DD}" stroke-width="3.6" opacity=".9"/>'
            f'<path d="{ring_d(ring, 1.6, 2, 30)}" fill="{LINE}" fill-rule="evenodd"/></g>')
    crease = crease_lines(M) + chin_line(M)
    return D.wrap('face', body + crease), (top, bot)


def crease_lines(M):
    """double-eyelid creases above each eye (thin, taken from the reference's dark lines above the lash)"""
    rf = M['rf']
    out = ''
    for s in 'RL':
        b = V.EYES[s]
        sl = V.box(b)
        ink = np.zeros_like(rf['ink'])
        ink[sl] = rf['ink'][sl]
        lash = ndi.binary_dilation(rf[f'lash_{s}'], iterations=2 * K)
        ink &= ~lash & ~rf[f'iris_{s}'] & ~rf[f'brow_{s}']
        ink &= M['by'] < V.IRIS[s][1] - 6
        for ln in centreline(ndi.binary_opening(ink, iterations=1), 5):
            w = 1.3
            out += f'<path d="{taper(ln, .3, .3, w)}" fill="{LINE}" opacity=".85"/>'
    return out


def ear_group(M, s):
    D = Defs('er' + s)
    m = M[f'ear_{s}']
    d = mask_d(m, 2.2, 3, 30)
    pts = contour_pts(m, 2.2, 3, 30)[0]
    xs = [p[0] for p in pts]
    x0, x1 = min(xs), max(xs)
    fill = D.lin(x0 if s == 'R' else x1, 0, x1 if s == 'R' else x0, 0, [(0, SKIN_D), (.6, SKIN), (1, SKIN)])
    cl = D.clip(d)
    # inner ear: the reference's dark lines inside the ear
    # (r2) the ear's lines (outline and the inner folds): the reference's own dark lines in the ear, clean smoothed shapes
    ink = line_mask(M, ndi.binary_dilation(m, iterations=2 * K), 1, 30)
    cx = (x0 + x1) / 2
    inner = f'<ellipse cx="{fnum(cx)}" cy="266" rx="6" ry="16" fill="{SKIN_DD}" opacity=".45" filter="{D.blur(2.5)}"/>'
    body = (f'<path d="{d}" fill="{fill}"/><g clip-path="{cl}">{inner}'
            f'<path d="{d}" fill="none" stroke="{SKIN_DD}" stroke-width="3.6" opacity=".9"/>'
            f'<path d="{ring_d(ink, 1.0, 2, 10)}" fill="{LINE}" fill-rule="evenodd"/></g>')
    return D.wrap(f'ear_{s}', body)


def eye_groups(M, s):
    rf, ref = M['rf'], M['ref']
    white, iris, lash = rf[f'white_{s}'], rf[f'iris_{s}'], rf[f'lash_{s}']
    by = M['by']
    out = {}
    # opening (almond): top = the lash's lower edge (smoothed), bottom = a smooth curve under the iris; the lash covers
    # the top seam. Columns from the lash's outer end to its inner end.
    lc = np.nonzero(lash.any(0))[0]
    irow = np.nonzero(iris.any(1))[0]
    i_bot = to_base((0, irow.max()))[1] if len(irow) else V.IRIS[s][1] + 10
    xs_, top_ = [], []
    for c in lc:
        r = np.nonzero(lash[:, c])[0]
        xs_.append(to_base((c, 0))[0])
        top_.append(to_base((0, r.max()))[1])
    xs_, top_ = np.array(xs_), ndi.gaussian_filter1d(np.array(top_), 2 * K)
    x_out, x_in = (xs_.min(), xs_.max()) if s == 'R' else (xs_.max(), xs_.min())
    # (胖大叔) the opening = the measured white + iris (one smoothed shape, as the eye is drawn: the white goes round the
    # iris down to the lower lid); per column its top (under the lash) and bottom give the blink table
    opn = ndi.binary_fill_holes(ndi.binary_closing(white | iris, iterations=2 * K))
    opn = V._biggest(ndi.binary_opening(opn, iterations=K))
    opts = contour_pts(opn, 1.4, 2, 20)[0]
    d_open = bez(opts)
    oc = np.nonzero(opn.any(0))[0]
    X, T, B = [], [], []
    for c in oc[::3]:
        r = np.nonzero(opn[:, c])[0]
        X.append(to_base((c, 0))[0]); T.append(to_base((0, r.min()))[1]); B.append(to_base((0, r.max()))[1])
    X, T, B = np.array(X), ndi.gaussian_filter1d(np.array(T), 1.5), ndi.gaussian_filter1d(np.array(B), 1.5)
    B = np.maximum(B, T + .6)
    S = []
    for c, t, bb in zip(oc[::3], T, B):      # the lid's shadow ends where the measured white starts (the white's first row)
        r = np.nonzero(white[:, c])[0]
        S.append(to_base((0, r.min()))[1] if len(r) else t + 3.5)
    S = np.clip(ndi.gaussian_filter1d(np.array(S), 1.5), T, B)
    S = np.clip(np.maximum(S, T + SHADE_PX), T, B)
    wt_s = None
    table = [[round(float(x), 2), round(float(t) - .4, 2), round(float(b), 2)] for x, t, b in zip(X, T, B)]
    up = [(float(x), float(t) - 1.4) for x, t in zip(X, T)]
    wb = list(B)
    sh = [(float(x), float(y)) for x, y in zip(X, S)][::-1]
    d_shade = bez(up + sh)
    i_bot = float(np.nanmax(wb))
    # white: clean bright fill, a soft shadow band under the upper lid (its lower edge measured), slightly deeper at the outer corner
    D = Defs('ew' + s)
    cl = D.clip(d_open)
    wc = mean_rgb(ref, white)
    wc = np.clip(wc * .2 + np.array([255, 252, 250]) * .8, 0, 255)
    ymin = min(p[1] for p in up)
    fill = D.lin(0, ymin, 0, i_bot, [(0, hexc(wc * .985)), (.4, hexc(wc)), (1, hexc(wc))])
    shade = D.lin(0, ymin, 0, max(S) + 1, [(0, '#8f7470'), (.6, '#a68c88'), (1, '#b49c98')])
    # (r2) the white's soft grey-lavender shading: where the reference's white reads shaded (inside the opening, not its
    # bright white and not its iris) -- one smoothed shape under the lid and in the corners
    # (r5) the white: the opening is the soft grey-lavender of the shaded white (under the lid, in the corners); the bright
    # white is the measured bright part of the reference's white, one smoothed shape over it
    wm = ndi.binary_closing(white, iterations=K // 2 or 1)
    d_white = mask_d(wm, 1.0, 2, 4)
    shade_fill = D.lin(0, ymin, 0, i_bot, [(0, '#a08c92'), (.5, '#ac989c'), (1, '#b4a0a4')])
    out[f'eye_{s}'] = D.wrap(f'eye_{s}', f'<path d="{d_open}" fill="{shade_fill}" stroke="#ac989c" stroke-width="1.4"/>'
                                         f'<path d="{d_white}" fill="{fill}" filter="{D.blur(.3)}"/>')
    # iris
    D = Defs('ei' + s)
    # (胖大叔) the iris is a round ellipse fitted to the measured iris (its hull read as a diamond); the eye white masks it
    # (r3) the iris as drawn in the base: the measured amber iris (its hull: the big highlight on the upper rim cuts its
    # corner), and the highlight put back on the same spot over the rim -- the two together read as the round iris
    ipts = contour_pts(iris, 1.0, 2, 10)[0]
    d = bez(ipts)
    xs_i, ys_i = [q[0] for q in ipts], [q[1] for q in ipts]
    ix, iy = (min(xs_i) + max(xs_i)) / 2, (min(ys_i) + max(ys_i)) / 2
    rx, ry = (max(xs_i) - min(xs_i)) / 2, (max(ys_i) - min(ys_i)) / 2
    hb = M['ref']
    Lh, (_, sat_h, _) = V.lum(hb), V.hsv(hb)
    bright = (Lh > 225) & (sat_h < .12) & ndi.binary_dilation(iris, iterations=2 * K)
    lab_, n_ = ndi.label(bright)
    HL = None
    best = None
    for k_ in range(1, n_ + 1):
        yy_, xx_ = np.nonzero(lab_ == k_)
        if len(xx_) < 40 * K * K / 16:
            continue
        hx_, hy_ = to_base((xx_.mean(), 0))[0], to_base((0, yy_.mean()))[1]
        if hy_ < iy and abs(hx_ - ix) < rx and (best is None or len(xx_) > best[0]):
            best = (len(xx_), hx_, hy_)
    if best:
        HL = (best[1] - .5, best[2] + .4, float(np.sqrt(best[0] / np.pi) / K) * 1.35)
    # the round iris seen in the base: the amber hull plus its dark rim (thick at the top under the lash), one ellipse
    ring = (Lh < 85) & ndi.binary_dilation(iris, iterations=int(3.5 * K)) & ~ndi.binary_dilation(lash, iterations=1)
    vis = ndi.binary_fill_holes(ndi.binary_closing(iris | ring, iterations=K))
    cs_, _ = cv2.findContours(V._biggest(vis).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (ecx, ecy), (ew, eh), ea = cv2.fitEllipse(max(cs_, key=cv2.contourArea))
    ex_, ey_ = to_base((ecx, ecy))
    erx, ery = ew / 2 / K, eh / 2 / K
    d_round = (f'M{fnum(ex_ - erx)} {fnum(ey_)} a{fnum(erx)} {fnum(ery)} 0 1 0 {fnum(2 * erx)} 0 a{fnum(erx)} {fnum(ery)} 0 1 0 {fnum(-2 * erx)} 0Z')
    round_tf = f' transform="rotate({ea:.2f} {fnum(ex_)} {fnum(ey_)})"'
    g_iris = D.lin(0, iy - ry, 0, iy + ry, [(0, '#7e4e26'), (.3, '#8e5a2c'), (.62, '#ad7840'), (.88, '#cf9f62'), (1, '#c08f55')])
    ring = D.rad(ix, iy, max(rx, ry), [(0, '#000000', 0), (.78, '#000000', 0), (1, '#6a4018', .5)])
    pupil_y = iy + ry * .05
    cl = D.clip(d)
    body = (f'<path d="{d_round}"{round_tf} fill="#2a170c"/>'
            f'<path d="{d}" fill="{g_iris}"/><g clip-path="{cl}">'
            f'<path d="{d}" fill="{ring}"/>'
            f'<ellipse cx="{fnum(ix)}" cy="{fnum(pupil_y)}" rx="{fnum(rx * .42)}" ry="{fnum(ry * .5)}" fill="#5a3512" opacity=".9"/>'
            f'<ellipse cx="{fnum(ix)}" cy="{fnum(pupil_y + ry * .05)}" rx="{fnum(rx * .26)}" ry="{fnum(ry * .34)}" fill="#3a1f0a"/>'
            f'<ellipse cx="{fnum(ix)}" cy="{fnum(iy + ry * .62)}" rx="{fnum(rx * .62)}" ry="{fnum(ry * .28)}" fill="#e8c08a" opacity=".55" filter="{D.blur(1.4)}"/>'
            f'<path d="M{fnum(ix - rx)} {fnum(iy - ry)} H{fnum(ix + rx)} V{fnum(iy - ry * .25)} Q{fnum(ix)} {fnum(iy - ry * .05)} {fnum(ix - rx)} {fnum(iy - ry * .25)}Z" '
            f'fill="#6a4018" opacity=".25" filter="{D.blur(1.2)}"/>'
            f'<path d="{d}" fill="none" stroke="#7a4c1e" stroke-width="1.1" opacity=".8"/></g>')
    out[f'iris_{s}'] = D.wrap(f'iris_{s}', body)
    # highlight: one big upper spark (towards the outer corner) and a small lower one
    D = Defs('eh' + s)
    sx = -1 if s == 'R' else 1
    hx, hy, hr = HL if HL else (ix + sx * rx * .32, iy - ry * .42, rx * .3)
    out[f'hilite_{s}'] = D.wrap(f'hilite_{s}', f'<circle cx="{fnum(hx)}" cy="{fnum(hy)}" r="{fnum(hr)}" fill="#ffffff"/>'
                                               f'<circle cx="{fnum(ix - sx * rx * .38)}" cy="{fnum(iy + ry * .42)}" r="{fnum(rx * .13)}" fill="#ffffff" opacity=".85"/>')
    # upper lash line: the measured shape, clean dark fill with a soft lighter lower edge
    D = Defs('el' + s)
    lash_d = ndi.binary_dilation(lash, iterations=1)
    d = mask_d(lash_d, .9, 2, 8)
    lp = contour_pts(lash_d, .9, 2, 8)[0]
    lys = [p[1] for p in lp]
    lx = [p[0] for p in lp]
    # deep saturated browns (the base's lash is (78, 44, 3)): never the amber of the iris
    g_lash = D.lin(0, min(lys), 0, max(lys), [(0, '#140c08'), (.55, '#2a1a14'), (1, '#3a2418')])
    out[f'lash_{s}'] = D.wrap(f'lash_{s}', f'<path d="{d}" fill="{g_lash}"/>'
                                           f'<path d="{d}" fill="none" stroke="{LASH_D}" stroke-width=".6" opacity=".8"/>')
    # lower lid (下眼瞼): a thin soft line under the opening's outer two thirds, and a few tiny lower lashes at the outer end
    D = Defs('ed' + s)
    bot = [(x, yb + 1.7) for x, yt, yb in table]
    xs = [p[0] for p in bot]
    xo, xi = (min(xs), max(xs)) if s == 'R' else (max(xs), min(xs))
    sel = [p for p in bot if (p[0] - xi) / (xo - xi) > .08]
    sel.sort(key=lambda p: p[0])
    if len(sel) > 3:      # one smooth curve (a quadratic through the measured lower edge), not the column steps
        q = np.polyfit([p[0] for p in sel], [p[1] for p in sel], 2)
        sel = [(x, float(np.polyval(q, x))) for x in np.linspace(sel[0][0], sel[-1][0], 12)]
    # (r7) the lower lid (下眼瞼): one thin smooth line along the measured lower edge (a quadratic), fine at both ends
    lid = taper(sel, .3, .3, 1.7) if len(sel) > 2 else ''
    out[f'lowlash_{s}'] = D.wrap(f'lowlash_{s}', f'<path d="{lid}" fill="#4a2e24" opacity=".95"/>')
    return out, table, dict(open=d_open, centre=[round(float(ix), 2), round(float(iy), 2)], iris_r=[round(rx, 2), round(ry, 2)],
                            lash_box=[min(lx), min(lys), max(lx), max(lys)])


def brow_group(M, s):
    D = Defs('eb' + s)
    m = M['rf'][f'brow_{s}']
    m = V._biggest(ndi.binary_fill_holes(ndi.binary_closing(m, iterations=K)))
    pts = contour_pts(m, 1.0, 2, 6)[0]
    d = bez(pts)
    xs = [p[0] for p in pts]
    fill = D.lin(min(xs), 0, max(xs), 0, [(0, '#8a6448'), (.5, BROW), (1, '#8a6448')])
    return D.wrap(f'brow_{s}', f'<path d="{d}" fill="{fill}"/>')


def chin_line(M):
    """the small chin dimple under the mouth (the reference's short dark line), one tapered stroke"""
    rf = M['rf']
    ink = np.zeros_like(rf['ink'])
    sl = V.box((496, 326, 532, 338))
    ink[sl] = rf['ink'][sl]
    out = ''
    for ln in centreline(ndi.binary_opening(ink, iterations=1), 3):
        if len(ln) > 3:
            q = np.polyfit([p[0] for p in ln], [p[1] for p in ln], 2)
            ln = [(x, float(np.polyval(q, x))) for x in np.linspace(ln[0][0], ln[-1][0], 10)]
        out += f'<path d="{taper(ln, .3, .3, 1.5)}" fill="#c89582" opacity=".85"/>'
    return out


def nose_group(M):
    """big round nose: the measured hook line (tapered), a soft pink tip and the nostril shade"""
    D = Defs('ns')
    m = M['rf']['nose']
    out = f'<ellipse cx="513" cy="274" rx="15" ry="10" fill="#f6b4a6" opacity=".35" filter="{D.blur(4)}"/>'
    out += f'<ellipse cx="516" cy="281" rx="9" ry="3" fill="#e8a89c" opacity=".4" filter="{D.blur(1.2)}"/>'
    nl = line_mask(M, region(M, V.NOSE), 1, 6)
    nsh = ndi.binary_opening(M['rf']['nose'] & ~ndi.binary_dilation(nl, iterations=1), iterations=1)
    out += f'<path d="{mask_d(nsh, .9, 2, 4)}" fill="#ecbaa8" filter="{D.blur(.4)}"/>'
    out += f'<path d="{ring_d(nl, .8, 2, 4)}" fill="#7a4438" fill-rule="evenodd"/>'
    out += f'<ellipse cx="509" cy="266" rx="3" ry="4" fill="#ffffff" opacity=".45" filter="{D.blur(1.2)}"/>'
    return D.wrap('nose', out)


def mouth_mask(M):
    """the open smile under the mustache, measured from the reference: reddish pink, not the mustache's brown"""
    ref = M['ref']
    hue, sat, val = V.hsv(ref)
    L = V.lum(ref)
    sl = V.box((481, 299, 547, 326))
    m = np.zeros(L.shape, bool)
    red = ((hue < 16) | (hue > 340)) & (sat > .28) & (L > 70) & (L < 200)
    dark = (L < 70) & (M['by'] > 301)
    m[sl] = (red | dark)[sl]
    m = ndi.binary_closing(m, iterations=K)
    m = ndi.binary_fill_holes(m)
    return V._biggest(ndi.binary_opening(m, iterations=2))


def mouth_group(M):
    """resting mouth: the open smile (lower lip / mouth inside, teeth under the mustache), clean fills and one lip line"""
    D = Defs('mo')
    m = mouth_mask(M)
    pts = contour_pts(m, 1.4, 2, 10)[0]
    d = bez(pts)
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    cx = (x0 + x1) / 2
    fill = D.lin(0, y0, 0, y1, [(0, '#8a3a36'), (.35, '#c45e5c'), (.7, '#e8908a'), (1, '#e48882')])
    cl = D.clip(d)
    inside = (f'<path d="M{fnum(x0)} {fnum(y0 - 2)} H{fnum(x1)} V{fnum(y0 + 3.2)} Q{fnum(cx)} {fnum(y0 + 5.5)} {fnum(x0)} {fnum(y0 + 3.2)}Z" fill="#fff8f2"/>'
              f'<ellipse cx="{fnum(cx)}" cy="{fnum(y1 - 3)}" rx="{fnum((x1 - x0) * .32)}" ry="3.4" fill="#f2aaa2" opacity=".8" filter="{D.blur(1)}"/>')
    lower = sorted([p for p in pts if p[1] > (y0 + y1) / 2], key=lambda p: p[0])
    lip = f'<path d="{taper([(x, y + .6) for x, y in lower], .5, .5, 2.8)}" fill="#5e2a24"/>' if len(lower) > 3 else ''
    return D.wrap('smile', f'<path d="{d}" fill="{fill}"/><g clip-path="{cl}">{inside}</g>' + lip), dict(box=[x0, y0, x1, y1])


def mustache_mask(M):
    ref = M['ref']
    hue, sat, val = V.hsv(ref)
    L = V.lum(ref)
    sl = V.box((452, 280, 576, 314))
    m = np.zeros(L.shape, bool)
    brown = (L < 150) & ~(((hue < 16) | (hue > 340)) & (sat > .3) & (L > 70))
    m[sl] = brown[sl]
    m = ndi.binary_closing(m, iterations=K)
    m = ndi.binary_fill_holes(m)
    return V._biggest(ndi.binary_opening(m, iterations=K))


def mustache_group(M):
    """八字鬍（獨立一層）：量到的外形，乾淨的褐色漸層＋深色外框＋幾條順毛流的細線＋上緣高光；從人中長出來，兩端上捲（不破臉框）"""
    D = Defs('ms')
    m = mustache_mask(M)
    pts = contour_pts(m, 1.0, 2, 30)[0]
    d = bez(pts)
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    y0, y1 = min(ys), max(ys)
    fill = D.lin(0, y0, 0, y1, [(0, MUST_L), (.5, MUST), (1, MUST_D)])
    cl = D.clip(d)
    st_ = line_mask(M, ndi.binary_erosion(m, iterations=2 * K), 0, 4)
    strands = f'<path d="{ring_d(st_, .6, 1, 2)}" fill="{MUST_D}" fill-rule="evenodd"/>'
    hi = ''
    for sx in (-1, 1):
        hi += (f'<path d="M{fnum(AXIS + sx * 40)} {fnum(y0 + 9)} Q{fnum(AXIS + sx * 20)} {fnum(y0 + 2)} {fnum(AXIS + sx * 4)} {fnum(y0 + 5)}" '
               f'fill="none" stroke="#b8977c" stroke-width="2" stroke-linecap="round" opacity=".6"/>')
    body = (f'<path d="{d}" fill="{fill}"/><g clip-path="{cl}">{strands}{hi}</g>'
            f'<path d="{d}" fill="none" stroke="#2e1d15" stroke-width="2.2" stroke-linejoin="round"/>')
    return D.wrap('beard', body), dict(box=[min(xs), y0, max(xs), y1])


def blush_group(s, M):
    """the base's rosy cheeks (he always blushes a little): a soft round glow and a few short hatch lines"""
    D = Defs('bl' + s)
    cx = 442 if s == 'R' else 585
    cy = 276
    g = D.rad(cx, cy, 26, [(0, '#f28078', .85), (.6, '#f49a90', .45), (1, '#f8c0b0', 0)], ry=16)
    box_ = (412, 258, 472, 300) if s == 'R' else (555, 258, 615, 300)
    hl_ = line_mask(M, region(M, box_), 0, 4)
    hatch = f'<path d="{ring_d(hl_, .6, 1, 2)}" fill="#d0645e" fill-rule="evenodd"/>'
    return D.wrap(f'blush_{s}', f'<ellipse cx="{cx}" cy="{cy}" rx="28" ry="17" fill="{g}"/>' + hatch)


def main():
    M = measure()
    groups = {}
    groups['face'], (top, bot) = face_group(M)
    eyes = {}
    for s in 'RL':
        groups[f'ear_{s}'] = ear_group(M, s)
        g, table, info = eye_groups(M, s)
        groups.update(g)
        info['table'] = table
        eyes[s] = info
        groups[f'brow_{s}'] = brow_group(M, s)
        groups[f'blush_{s}'] = blush_group(s, M)
    groups['nose'] = nose_group(M)
    groups['smile'], mouth = mouth_group(M)
    groups['beard'], must = mustache_group(M)
    data = dict(date='2026-11-23', frame=F, face=dict(top=round(top, 2), chin=round(bot, 2)), eyes=eyes, mouth=mouth, mustache=must, groups=groups)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    print(OUT, 'face top', round(top, 1), 'chin', round(bot, 1), {s: eyes[s]['centre'] for s in 'RL'}, 'mouth', [round(v, 1) for v in mouth['box']],
          'mustache', [round(v, 1) for v in must['box']])


if __name__ == '__main__':
    main()
