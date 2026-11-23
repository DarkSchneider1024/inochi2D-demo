"""《國王的新衣》V6 線先生、小朵的思考手臂：照 Gemini 比對圖手繪的姿勢層，取代 story_think.py 剛體轉出來的最後姿勢（2026-11-23）。

照 story_male/shoe_think_draw.py 的做法（不改它）：story_think.py 把原手臂剛體轉上去，柏達克系、卡洛兒系的握拳都只到領口、碰不到下巴；
  - 比對圖：Gemini 原位把模型靜止畫面改成思考姿勢（一手握拳托下巴、另一前臂橫在腰前托住那隻手肘），
    carrot-youtube/人物形象/32_國王的新衣V6換裝/<id>_思考比對圖_Gemini.png（和該臉模底圖同一張畫布）。
  - 程式照圖量關節（下面 POSE，底圖 px），手繪兩層（平滑漸層＋等寬輪廓線，顏色取該角色自己的袖子、皮膚）：
      思考手臂：托腮那隻的上臂（袖子）、前臂（手肘在下），腰前那隻的上臂、橫過腰的前臂、托住手肘的張開手
      思考拳（在臉、鬍子前面）：托在下巴下的握拳手
    兩層都複製胸腔的綁定（呼吸、身體搖擺）。
  - 仍是 Arm:: Think：0～0.667 照 story_think.py 的轉動把手舉起來，0.667～0.708 原手臂層（上臂、下臂、手肘、手掌、握拳…）
    換成這兩層，之後停在手繪姿勢。meta.storyThink 保留，另記 meta.storyThinkDrawn。
重跑順序：正面 builder → story_explain.py → （柏達克系）story_burly/arm_rigid.py → story_think.py → 這支。

    python -X utf8 tools/story_nc6/think_draw.py thread|duo
"""
import math
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'story_burly'))
from build_story_trio import Model, set_part_image      # noqa: E402

THINK = 'Arm:: Think'
LAYERS = ('思考手臂', '思考拳')
HIDE_STEMS = ('上臂_', '下臂_', '手掌_', '手指_', '握拳_', '手肘_')
SWAP = (0.6667, 0.7083)
REF = 'carrot-youtube/人物形象/32_國王的新衣V6換裝/{mid}_思考比對圖_Gemini.png'

# 量自 Gemini 比對圖（底圖 px；角色右手＝畫面左托下巴）
CAST = {
    'thread': dict(
        mid='thread_nc_burlyv3', scale=1.3, origin=(512, 750),
        SR=(300, 382), ER=(386, 612), WR=(492, 366), CHIN=(514, 272),
        SL=(724, 382), EL=(774, 628), WL=(462, 634),
        w_up=(56, 50), w_fore=(44, 34), fist=(40, 36), hand=1.0, sleeve_to=.86,
        sleeve=('#fbf6e6', '#efe5cc', '#cdbd98', '#6e5a3a'), skin=('#f6b98c', '#eba274', '#d4865c', '#84452c'),
        hair=True, z=(.44, .385)),
    'duo': dict(
        mid='duo_nc_carolv3', scale=1.257, origin=(512, 742),
        SR=(420, 418), ER=(404, 590), WR=(494, 412), CHIN=(510, 326),
        SL=(604, 418), EL=(656, 598), WL=(512, 626),
        w_up=(30, 21), w_fore=(17, 13), fist=(28, 24), fist_t=.6, hand=.55, sleeve_to=.5,
        sleeve=('#fde9ec', '#f8cdd4', '#e6a8b4', '#b07080'), skin=('#ffeadc', '#f7d5c6', '#dca294', '#c48a7c'),
        cuff='#f8e6a4', hair=False, z=(.55, .415)),
}


def cap_path(p0, p1, r0, r1, n_arc=10):
    """a limb segment p0->p1 with round ends (radius r0 at p0, r1 at p1), as one closed outline"""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-u[1], u[0]])
    pts = [p0 + n * r0, p1 + n * r1]
    for t in np.linspace(0, math.pi, n_arc)[1:-1]:          # round end at p1: +n -> +u -> -n
        pts.append(p1 + r1 * (n * math.cos(t) + u * math.sin(t)))
    pts += [p1 - n * r1, p0 - n * r0]
    for t in np.linspace(0, math.pi, n_arc)[1:-1]:          # round end at p0: -n -> -u -> +n
        pts.append(p0 + r0 * (-n * math.cos(t) - u * math.sin(t)))
    return 'M' + ' L'.join(f'{q[0]:.1f} {q[1]:.1f}' for q in pts) + ' Z'


def grad(gid, p0, p1, r, cols):
    """a gradient across the limb (shade - light - mid - shade)"""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-u[1], u[0]])
    m = (p0 + p1) / 2
    a, b = m - n * r, m + n * r
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}">'
            f'<stop offset="0" stop-color="{cols[2]}"/><stop offset=".35" stop-color="{cols[1]}"/><stop offset=".62" stop-color="{cols[0]}"/>'
            f'<stop offset="1" stop-color="{cols[2]}"/></linearGradient>')


def limb(gid, p0, p1, r0, r1, cols, extra=''):
    d = cap_path(p0, p1, r0, r1)
    return (grad(gid, p0, p1, max(r0, r1), cols)
            + f'<path d="{d}" fill="url(#{gid})"/>{extra}'
            + f'<path d="{d}" fill="none" stroke="{cols[3]}" stroke-width="2" stroke-linejoin="round"/>')


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def arm_hair(p0, p1, col, n=7, seed=3):
    rng = np.random.default_rng(seed)
    out = ''
    for k in range(n):
        q = lerp(p0, p1, .2 + .6 * k / n)
        dx, dy = rng.uniform(-14, 14), rng.uniform(-10, 10)
        out += f'<path d="M{q[0] + dx:.1f} {q[1] + dy:.1f} q-3 6 -1 11" fill="none" stroke="{col}" stroke-width="1" opacity=".45" stroke-linecap="round"/>'
    return out


def sleeve_arm(gid, S, E, c, who_hair):
    """upper arm: shoulder to elbow; the sleeve covers it down to sleeve_to, the bare skin below (elbow)"""
    (w0, w1), sk, sl = c['w_up'], c['skin'], c['sleeve']
    s = limb(gid + 's', S, E, w0 * .92, w1 * .88, sk)          # the bare arm under the sleeve (shows at the elbow)
    cut = lerp(S, E, c['sleeve_to'])
    s += limb(gid + 'c', S, cut, w0, w1 * 1.04, sl)
    # the rolled cuff / sleeve band at the sleeve's end
    u = np.array(E, float) - np.array(S, float)
    u /= np.linalg.norm(u)
    n = np.array([-u[1], u[0]])
    a, b = np.array(cut) + n * w1 * 1.08, np.array(cut) - n * w1 * 1.08
    a2, b2 = a - u * 12, b - u * 12
    band = c.get('cuff', sl[1])
    s += (f'<path d="M{a[0]:.1f} {a[1]:.1f} L{b[0]:.1f} {b[1]:.1f} L{b2[0]:.1f} {b2[1]:.1f} L{a2[0]:.1f} {a2[1]:.1f} Z" fill="{band}" '
          f'stroke="{sl[3]}" stroke-width="1.6" stroke-linejoin="round"/>')
    return s


def fist(F, toward, c):
    """a loose fist at F, knuckles toward `toward` (under the chin); the thumb on the near side"""
    rx, ry = c['fist']
    sk = c['skin']
    a = math.degrees(math.atan2(toward[1] - F[1], toward[0] - F[0]))
    g = (f'<linearGradient id="fg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{sk[2]}"/><stop offset=".55" stop-color="{sk[1]}"/>'
         f'<stop offset="1" stop-color="{sk[0]}"/></linearGradient>')
    body = (f'<path d="M{-rx} {-ry * .8} Q{-rx * .2} {-ry * 1.15} {rx * .7} {-ry * .9} Q{rx * 1.15} {-ry * .4} {rx * 1.05} {ry * .2} '
            f'Q{rx * .95} {ry * .95} {rx * .2} {ry} Q{-rx * .7} {ry * 1.05} {-rx} {ry * .6} Z" fill="url(#fg)" stroke="{sk[3]}" stroke-width="2" stroke-linejoin="round"/>')
    # curled fingers: three creases across the front of the fist
    for k in (-.45, 0, .45):
        body += (f'<path d="M{rx * .35} {ry * k:.1f} Q{rx * .85} {ry * k - 3:.1f} {rx * 1.0} {ry * k + 4:.1f}" fill="none" stroke="{sk[3]}" '
                 f'stroke-width="1.4" opacity=".7" stroke-linecap="round"/>')
    thumb = (f'<path d="M{-rx * .5} {-ry * .75} Q{rx * .1} {-ry * 1.35} {rx * .75} {-ry * 1.0} Q{rx * .9} {-ry * .75} {rx * .55} {-ry * .55} '
             f'Q{rx * .05} {-ry * .55} {-rx * .35} {-ry * .35} Z" fill="{sk[0]}" stroke="{sk[3]}" stroke-width="1.6" stroke-linejoin="round"/>')
    return f'<defs>{g}</defs><g transform="translate({F[0]:.1f} {F[1]:.1f}) rotate({a:.2f})">{body}{thumb}</g>'


def open_hand(W, toward, c):
    """an open hand from the wrist W toward `toward`, palm up, the fingers curling up round the other arm's elbow"""
    k = c['hand']
    sk = c['skin']
    a = math.degrees(math.atan2(toward[1] - W[1], toward[0] - W[0]))
    palm = (f'<path d="M-4 -22 Q30 -26 58 -22 Q66 0 60 22 Q30 28 -4 24 Z" fill="{sk[1]}" stroke="{sk[3]}" stroke-width="{2 / k:.2f}" stroke-linejoin="round"/>'
            f'<path d="M4 12 Q30 18 56 12" fill="none" stroke="{sk[2]}" stroke-width="{4 / k:.2f}" opacity=".45"/>')
    fingers = ''
    for j, v in enumerate((-16, -6, 4, 14)):
        L = 36 - abs(j - 1.3) * 5
        fingers += (f'<path d="M54 {v - 5} Q{54 + L * .6} {v - 7} {54 + L} {v - 14} Q{57 + L} {v - 20} {51 + L} {v - 19} '
                    f'Q{48 + L * .8} {v - 8} {54 + L * .45} {v + 5} L54 {v + 5} Z" fill="{sk[0]}" stroke="{sk[3]}" stroke-width="{1.6 / k:.2f}" stroke-linejoin="round"/>')
    thumb = (f'<path d="M14 -20 Q32 -36 50 -44 Q58 -40 42 -26 Q32 -18 26 -14 Z" fill="{sk[0]}" stroke="{sk[3]}" stroke-width="{1.6 / k:.2f}" stroke-linejoin="round"/>')
    return f'<g transform="translate({W[0]:.1f} {W[1]:.1f}) rotate({a:.2f}) scale({k})">{palm}{fingers}{thumb}</g>'


def art(c):
    SR, ER, WR, SL, EL, WL = (c[k] for k in ('SR', 'ER', 'WR', 'SL', 'EL', 'WL'))
    sk = c['skin']
    (f0, f1) = c['w_fore']
    # the waist arm first (behind), then the chin arm in front of it, then the open hand under the chin arm's elbow
    s = sleeve_arm('ul', SL, EL, c, c['hair'])
    s += limb('fl', EL, WL, f0, f1, sk, arm_hair(EL, WL, sk[3], seed=5) if c['hair'] else '')
    s += sleeve_arm('ur', SR, ER, c, c['hair'])
    s += limb('fr', ER, WR, f0, f1, sk, arm_hair(ER, WR, sk[3], seed=7) if c['hair'] else '')
    tip = (ER[0] - 6 * c['hand'], ER[1] + 10 * c['hand'])
    s += open_hand(WL, tip, c)
    return s


def render(page, svg, box, k=2.0):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    page.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style><svg xmlns="http://www.w3.org/2000/svg" width="{w * k:.0f}" '
                     f'height="{h * k:.0f}" viewBox="{x0} {y0} {w} {h}">{svg}</svg>')
    return Image.open(BytesIO(page.locator('svg').screenshot(omit_background=True))).convert('RGBA')


def new_layer(model, c, name, img, box, z):
    """a copy of 胸腔 (all its bindings: breath, sway, squat) carrying the picture on the box (base px)"""
    import build_carol_leads as L
    part = L.clone_part(model, '胸腔', name, z)
    part['masks'] = []
    part['opacity'] = 1
    set_part_image(model, part, img)
    x0, y0, x1, y1 = box
    # placed in true root space (the parent's actual origin): body.py moves the Body node when it rescales the body,
    # so carol's fit_grid (fixed Body frame) would put the layer off by that shift
    _fit_burly(model, part, box, c['scale'], origin=c['origin'])
    # the chest's deform bindings were for its own mesh: drop them (only transforms / opacity follow the chest)
    for p in model.params.values():
        p['bindings'] = [b for b in p['bindings'] if not (b['node'] == part['uuid'] and b['param_name'] == 'deform')]
    return part


def _fit_burly(model, part, box, k, cols=6, rows=8, origin=(512, 750)):
    """an even grid over the box (base px) in the part's own parent space (root = (base - origin) * k)"""
    root = model.parts['Root']
    ox, oy = model.position(part, root)
    tx, ty = part['transform']['trans'][:2]
    px, py = ox - tx, oy - ty                     # parent origin in root space
    x0, y0, x1, y1 = box
    cx, cy = ((x0 + x1) / 2 - origin[0]) * k, ((y0 + y1) / 2 - origin[1]) * k
    part['transform']['trans'][0], part['transform']['trans'][1] = cx - px, cy - py
    W, H = (x1 - x0) * k, (y1 - y0) * k
    verts, uvs, idx = [], [], []
    for r in range(rows):
        for q in range(cols):
            u, v = q / (cols - 1), r / (rows - 1)
            verts += [(u - .5) * W, (v - .5) * H]
            uvs += [u, v]
    for r in range(rows - 1):
        for q in range(cols - 1):
            a = r * cols + q
            idx += [a, a + 1, a + cols, a + 1, a + cols + 1, a + cols]
    part['mesh'].update(verts=verts, uvs=uvs, indices=idx, origin=[0, 0])


def reshaped(c, meta):
    """(2026-11-23 體型 body.py) 肩、肘、垂下的手跟著身體的寬度曲線與等比縮放移動；托下巴的手腕、下巴在頭旁不動；粗細乘身體比例"""
    if not meta:
        return c
    sys.path.insert(0, str(HERE))
    import body as BD
    f = BD.body_map(meta)
    k, (ox, oy) = c['scale'], c['origin']
    c = dict(c)
    for key in ('SR', 'ER', 'SL', 'EL', 'WL'):
        x, y = f((c[key][0] - ox) * k, (c[key][1] - oy) * k)
        c[key] = (round(x / k + ox, 1), round(y / k + oy, 1))
    s = meta['body']['scale'] * (1 + (meta['body'].get('arm', 1) - 1) * .5)
    for key in ('w_up', 'w_fore', 'fist'):
        c[key] = tuple(v * s for v in c[key])
    c['hand'] = c['hand'] * s
    return c


def main(who):
    c = CAST[who]
    model = Model(c['mid'])
    if THINK not in model.params or 'storyThink' not in model.json.get('meta', {}):
        raise SystemExit('先跑 story_think.py ' + c['mid'])
    if 'storyThinkDrawn' in model.json['meta']:
        raise SystemExit('已有手繪思考手臂：先從 builder 重建、story_explain、story_think 再跑')
    c = reshaped(c, model.json['meta'].get('storyNc6Body'))
    xs = [c[k][0] for k in ('SR', 'ER', 'WR', 'SL', 'EL', 'WL')]
    ys = [c[k][1] for k in ('SR', 'ER', 'WR', 'SL', 'EL', 'WL')]
    pad = c['w_up'][0] + 30
    boxA = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    t = c.get('fist_t', .5)
    F = (c['WR'][0] + (c['CHIN'][0] - c['WR'][0]) * t, c['WR'][1] + (c['CHIN'][1] - c['WR'][1]) * t)
    fr = max(c['fist']) + 16
    boxB = (F[0] - fr - 20, F[1] - fr - 20, F[0] + fr + 20, F[1] + fr + 20)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='msedge')
        page = br.new_page(device_scale_factor=1)
        imA = render(page, art(c), boxA)
        imB = render(page, fist(F, (c['CHIN'][0], c['CHIN'][1] - 30), c), boxB)
        br.close()
    prm = model.params[THINK]
    ax = prm['axis_points'][0]
    on = [0.0 if t <= SWAP[0] + 1e-4 else 1.0 for t in ax]
    za, zb = c['z']
    for name, im, box, z in (('思考手臂', imA, boxA, za), ('思考拳', imB, boxB, zb)):
        part = new_layer(model, c, name, im, box, z)
        prm['bindings'].append({'node': part['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                'isSet': [[True] for _ in ax], 'values': [[v] for v in on]})
    hide = {model.parts[n]['uuid'] for n in model.parts if n.startswith(HIDE_STEMS) and model.parts[n]['type'] == 'Part'}
    have = set()
    for b in prm['bindings']:
        if b['param_name'] == 'opacity' and b['node'] in hide:
            b['values'] = [[v[0] * (1 - o)] for v, o in zip(b['values'], on)]
            have.add(b['node'])
    for u in hide - have:
        prm['bindings'].append({'node': u, 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                'isSet': [[True] for _ in ax], 'values': [[1 - o] for o in on]})
    model.json['meta']['storyThinkDrawn'] = {'ref': REF.format(mid=c['mid']), 'pose': {k: c[k] for k in ('SR', 'ER', 'WR', 'SL', 'EL', 'WL', 'CHIN')},
                                             'layers': list(LAYERS), 'swap': list(SWAP)}
    model.save()
    print(c['mid'], '思考手臂（手繪）', boxA, boxB)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in CAST:
        sys.exit('用法：think_draw.py thread|duo')
    main(sys.argv[1])
