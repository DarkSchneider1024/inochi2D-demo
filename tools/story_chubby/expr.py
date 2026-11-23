"""胖大叔表情（2026-11-23，照 story_tareme/expr.py 複製改寫；垂眼姐姐、柏達克的檔不動）：照她自己描出的五官（face_trace.json）重畫
生氣、難過、微笑、大笑的眉／眼皮／閉眼／嘴，與眨眼的乾淨閉眼線。座標＝工作底圖 px（chubby_hand_v3/base.png）。
以下為原說明：
做法照 story_male/male2_expr.py（只讀參考）：全部乾淨手繪的 SVG 筆畫（兩端收尖的實心筆畫），座標＝底圖 px；兩眼、兩眉各自用自己的形狀，不鏡像。

  - 怒：眉＝描好的眉，內端壓低（繞眉中心轉 9 度、下移 1.5 px）；眼皮＝膚色片從上眼線往下蓋，內眼角壓低 4.5 px、外眼角 0.5 px，
        下緣一條和上眼線同粗的斜線；嘴＝比靜止嘴短的平線、兩端下彎，不露牙。
  - 哀：眉內端抬高（轉 −11 度、上移 1 px）；眼皮＝外側下垂（外眼角壓低 4 px、內眼角保持）；嘴＝小八字。
  - 笑（微笑／大笑）：閉眼＝沿他自己上眼線跨度的一條上拱弧線（外端粗、內眼角尖）；嘴＝靜止嘴線下的小開口笑（上排牙、舌頭）。
build.py 把這些放到原本的差分圖層（綁定、開關、遮罩不變）。
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = json.loads((HERE / 'face_trace.json').read_text(encoding='utf-8'))
AXIS = 513.5
LINE = '#2d1408'
LIP = '#9b6257'
LID_SKIN = '#fbe2d2'


def smooth(pts, k):
    out = []
    p = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for j in range(k):
            t = j / k
            out.append(tuple(.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t +
                                   (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    out.append(tuple(pts[-1]))
    return out


def stroke(pts, w0, w1, wmid=None, colour=LINE, opacity=1.0):
    P = smooth(pts, 10)
    n = len(P)
    wmid = (w0 + w1) / 2 if wmid is None else wmid
    left, right = [], []
    for i, (x, y) in enumerate(P):
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        t = i / (n - 1)
        w = (w0 + (wmid - w0) * t * 2) if t < .5 else (wmid + (w1 - wmid) * (t - .5) * 2)
        w *= .5 * (1 - (1 - min(1, 4 * t, 4 * (1 - t))) ** 2 * .65)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return f'<path d="M{"L".join("%.2f %.2f" % q for q in left + right[::-1])}Z" fill="{colour}" opacity="{opacity}"/>'


def eye(s):
    e = dict(T['eyes'][s])
    e['cols'] = e['table']
    e['lash'] = [(x, t - 1.2) for x, t, _b in e['table']]
    return e


def outer_first(pts, s):
    """points ordered from the outer corner to the inner one (R: left to right; L: right to left)"""
    return sorted(pts, key=lambda p: p[0], reverse=(s == 'L'))


def lash_line(s, n=7):
    """the traced lash line's centre, resampled to n points, outer corner first"""
    pts = outer_first(eye(s)['lash'], s)
    k = max(1, len(pts) // (n - 1))
    out = pts[::k]
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return [tuple(p) for p in out]


# ---------------------------------------------------------------- brows: the traced brow, turned about its own middle
def brow_centre(s):
    return (460.0, 195.0) if s == 'R' else (567.0, 195.0)


def brows(kind):
    out = ''
    for s in 'RL':
        cx, cy = brow_centre(s)
        sgn = 1 if s == 'R' else -1                 # + turns the inner end (toward the axis) down
        rot, dy = (9.0 * sgn, 1.5) if kind == 'angry' else (-11.0 * sgn, -1.0)
        svg = T['groups'][f'brow_{s}'].replace('id="', f'id="x{kind[0]}')
        svg = svg.replace('url(#', f'url(#x{kind[0]}')
        out += f'<g transform="translate(0 {dy}) rotate({rot} {cx:.2f} {cy:.2f})">{svg}</g>'
    return out


# ---------------------------------------------------------------- lids (each eye its own)
def lid(kind, s):
    pts = lash_line(s)
    n = len(pts)
    line = []
    for i, (x, y) in enumerate(pts):
        u = i / (n - 1)                              # 0 outer .. 1 inner
        d = (.4 + 3.4 * u ** 1.3) if kind == 'angry' else (3.4 * (1 - u) ** 1.3 + .3)
        line.append((x, y + d))
    top = min(y for _, y in pts) - 3.0
    x0, x1 = pts[0][0], pts[-1][0]
    ext = -3.0 if (s == 'R') else 3.0                # the flap runs a little past the outer corner
    flap = [(x0 + ext, top), (x1 - ext * .6, top), (x1 - ext * .6, line[-1][1] - .6)] + [(x, y - .6) for x, y in line[::-1]] + [(x0 + ext, line[0][1] - .6)]
    d = 'M' + 'L'.join('%.2f %.2f' % q for q in flap) + 'Z'
    w0, wm, w1 = (3.0, 3.0, 1.4) if kind == 'angry' else (2.4, 2.8, 1.3)
    return f'<path d="{d}" fill="{LID_SKIN}"/>' + stroke(line, w0, w1, wm)


# ---------------------------------------------------------------- closed eyes (smile, laugh)
def closed_eye(kind, s):
    e = eye(s)
    cols = e['cols']
    xs = [c[0] for c in cols]
    mid = sum((c[1] + c[2]) / 2 for c in cols) / len(cols)
    xo, xi = (min(xs) - 2.0, max(xs) + 2.5) if s == 'R' else (max(xs) + 2.0, min(xs) - 2.5)
    lift = 4.2 if kind == 'happy' else 5.0
    base = mid + 1.5
    pts = [(xo + (xi - xo) * u, base - lift * math.sin(math.pi * min(1.0, u * 1.08)) ** .9 + 1.2 * u) for u in (0, .17, .35, .52, .7, .86, 1.0)]
    return stroke(pts, 3.0, 1.2, 3.0)


def _polyfit(xs, ys, deg):
    """least squares polynomial (pure python; small normal equations), returns f(x)"""
    n = deg + 1
    S = [[sum(x ** (i + j) for x in xs) for j in range(n)] for i in range(n)]
    Y = [sum(y * x ** i for x, y in zip(xs, ys)) for i in range(n)]
    for i in range(n):                                     # Gauss-Jordan
        piv = S[i][i]
        S[i] = [v / piv for v in S[i]]
        Y[i] /= piv
        for k in range(n):
            if k != i:
                fk = S[k][i]
                S[k] = [a - fk * b for a, b in zip(S[k], S[i])]
                Y[k] -= fk * Y[i]
    return lambda x: sum(c * x ** i for i, c in enumerate(Y))


def lid_curves(s):
    """(r5) the blink's smoothed curves of one eye, from the traced opening (face_trace cols x, top, bottom): top = a cubic
    through the opening's top edge, bottom = a quadratic through its lower edge; the closed line lies 0.6 px over the lower edge.
    build.trace_lids uses the same fits (the lash line slides down by shut - top, one smooth piece)."""
    c = eye(s)['cols']
    xs = [p[0] for p in c]
    m = sum(xs) / len(xs)                                  # centred (better conditioned)
    ft = _polyfit([x - m for x in xs], [p[1] for p in c], 3)
    fb = _polyfit([x - m for x in xs], [p[2] for p in c], 2)
    return xs, (lambda x: ft(x - m)), (lambda x: fb(x - m) - .6)


BLINK_LIFT = 1.3          # the clean lid line's centre over the opening's top edge (where the traced lash line sits)


def blink_ends(s):
    xs, _, _ = lid_curves(s)
    return (min(xs) - 2.5, max(xs) + 1.0) if s == 'R' else (max(xs) + 2.5, min(xs) - 1.0)


def blink_rest_y(s, x):
    """the clean lid line's rest centre at x (base px): along the opening's smoothed top, the outer end bending down a little"""
    xs, ft, _ = lid_curves(s)
    xo, xi = blink_ends(s)
    u = (x - xo) / (xi - xo)
    y = ft(min(max(x, min(xs)), max(xs))) - BLINK_LIFT
    if u < .1:
        y += 1.2 * (1 - max(0.0, u) / .1)
    return y


def blink_line(s):
    """(r5 主工作階段：「閉眼那格上眼線變成一條起伏的鋸齒線」) a clean upper lid line for the blink: drawn at the open lash
    line's place along the smoothed opening (even thickness through the middle, thick at the outer corner, a fine point at
    the inner one). build.py swaps it in for the traced lash line early in Eye:: Blink and slides it, per column, down to the
    smoothed closed curve -- so half-closed and closed both show one smooth line."""
    xo, xi = blink_ends(s)
    pts = [(xo + (xi - xo) * u, blink_rest_y(s, xo + (xi - xo) * u)) for u in (0, .1, .25, .42, .6, .78, .9, 1.0)]
    return stroke(pts, 2.8, .9, 2.6)


# ---------------------------------------------------------------- mouths（胖大叔：靜止嘴是八字鬍下的張口笑 x 481..547, y 301..322；
# 表情嘴都放在鬍子層下面，上緣被鬍子蓋住）
CX = 514.0


def open_smile(kind):
    if kind == 'happy':
        x0, x1, top, mid, bot = 478.0, 550.0, 300.0, 303.0, 326.0
    else:
        x0, x1, top, mid, bot = 474.0, 554.0, 299.0, 302.0, 334.0
    cx = CX
    inside = f'M{x0} {top}Q{cx} {mid + 1.2} {x1} {top}Q{x1 - 8} {bot} {cx} {bot}Q{x0 + 8} {bot} {x0} {top}Z'
    clip = f'<clipPath id="cbsm{kind}"><path d="{inside}"/></clipPath>'
    teeth = f'M{x0} {top - 2}L{x1} {top - 2}L{x1} {mid + 6}Q{cx} {mid + 9} {x0} {mid + 6}Z'
    tongue = f'<ellipse cx="{cx}" cy="{bot - 1}" rx="{(x1 - x0) * .26:.2f}" ry="{(bot - mid) * .34:.2f}" fill="#e88a86"/>'
    return (f'<defs>{clip}</defs><path d="{inside}" fill="#7a2e2e" stroke="{LINE}" stroke-width="2.2" stroke-linejoin="round"/>'
            f'<g clip-path="url(#cbsm{kind})"><path d="{teeth}" fill="#fffaf6"/>{tongue}</g>')


def angry_mouth():
    """咬牙的方嘴（兩端下彎）"""
    x0, x1, top, bot = 488.0, 540.0, 306.0, 322.0
    d = f'M{x0} {top + 4}Q{CX} {top - 1} {x1} {top + 4}L{x1 + 2} {bot}Q{CX} {bot - 3} {x0 - 2} {bot}Z'
    return (f'<path d="{d}" fill="#fffaf6" stroke="{LINE}" stroke-width="2.2" stroke-linejoin="round"/>'
            f'<path d="M{x0} {(top + bot) / 2 + 1.5}Q{CX} {(top + bot) / 2 - 1} {x1} {(top + bot) / 2 + 1.5}" fill="none" stroke="{LINE}" stroke-width="1.3"/>')


def sad_mouth():
    pts = [(494.0, 321.0), (503.0, 315.6), (514.0, 314.0), (525.0, 315.6), (534.0, 321.0)]
    return stroke(pts, 1.4, 1.4, 2.6, colour=LINE)


def talk_mouth(kind):
    """嘴_啊（說話張嘴）／嘴_喔（驚訝圓嘴）"""
    if kind == 'a':
        x0, x1, top, bot = 490.0, 538.0, 303.0, 328.0
        d = f'M{x0} {top}Q{CX} {top + 3} {x1} {top}Q{x1 - 3} {bot} {CX} {bot}Q{x0 + 3} {bot} {x0} {top}Z'
        ty = 322.0
    else:
        d = 'M514 302C527 302 529 312 528.4 318C527.6 325 521.6 330 514 330C506.4 330 500.4 325 499.6 318C499 312 501 302 514 302Z'
        ty = 324.0
    return (f'<path d="{d}" fill="#7a2e2e" stroke="{LINE}" stroke-width="2.2" stroke-linejoin="round"/>'
            f'<ellipse cx="514" cy="{ty}" rx="10" ry="3.6" fill="#e88a86"/>')


def tears(drop):
    """淚：沿下眼瞼的水光線（積）；外眼角掛一滴（滴）"""
    out = ''
    for s in 'RL':
        tb = T['eyes'][s]['table']
        pts = [(x, b + .8) for x, _t, b in tb[3:-3:3]]
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
        if not drop:
            out += (f'<path d="{d}" fill="none" stroke="#bfe6ff" stroke-width="2.4" stroke-linecap="round" opacity=".9"/>'
                    f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width=".9" stroke-linecap="round" opacity=".9"/>')
        else:
            x, y = pts[0] if s == 'R' else pts[-1]
            out += (f'<path d="M{x:.1f} {y:.1f} Q{x - 4.5:.1f} {y + 11:.1f} {x:.1f} {y + 15:.1f} Q{x + 4.5:.1f} {y + 11:.1f} {x:.1f} {y:.1f}Z" '
                    f'fill="#cdeeff" stroke="#7fb8dc" stroke-width=".8" opacity=".95"/><ellipse cx="{x - 1:.1f}" cy="{y + 10:.1f}" rx="1.1" ry="1.7" fill="#fff"/>')
    return out


def groups():
    """scene groups for build.py (group id -> svg)"""
    g = {'brows_angry': brows('angry'), 'brows_sad': brows('sad'), 'm_happy': open_smile('happy'), 'm_laugh': open_smile('laugh'),
         'm_angry': angry_mouth(), 'm_sad': sad_mouth(), 'm_a': talk_mouth('a'), 'm_o': talk_mouth('o'),
         'tear_pool': tears(False), 'tear_drop': tears(True)}
    for s in 'RL':
        g[f'lid_angry_{s}'] = lid('angry', s)
        g[f'lid_sad_{s}'] = lid('sad', s)
        g[f'eye_happy_{s}'] = closed_eye('happy', s)
        g[f'eye_laugh_{s}'] = closed_eye('laugh', s)
        g[f'eye_shut_{s}'] = blink_line(s)
    return {k: f'<g id="{k}">{v}</g>' for k, v in g.items()}
