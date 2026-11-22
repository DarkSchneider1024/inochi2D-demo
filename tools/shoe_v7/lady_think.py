"""《鞋匠與小矮人》V7 買鞋太太 shoe_lady_aubv3：思考手臂照 Gemini 比對圖手繪（2026-11-22）。

    python -X utf8 tools/shoe_v7/lady.py                       # 建正面
    python -X utf8 tools/story_think.py shoe_lady_aubv3        # 共用思考動作（手臂剛體轉、握拳手、動畫 動作/思考）
    python -X utf8 tools/shoe_v7/lady_think.py                 # 本檔：最後那一段換成照比對圖手繪的思考手臂

起因：茄子小姐臉模的思考手臂（泡泡長袖照剛體轉）托不到下巴、袖子斜一大片。使用者 2026-11-22：「只有基礎人物用GPT 如果是故事人物用
gemini 生成比對圖即可」→ 用 Gemini 照底圖原位生一張太太的思考姿勢比對圖
（carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝/shoe_lady_aubv3_思考比對圖_Gemini_v1.png），手臂形狀照它量（底圖 px），
程式手繪成兩層，不用 GPT 部件：
  - 思考臂_R：角色右手（畫面左）——泡泡袖上臂垂在身側、前臂泡泡袖往上、袖口、握拳托下巴（食指彎在下巴下）。
  - 思考臂_L：角色左手（畫面右）——上臂垂在身側、前臂橫在腰前、袖口、手掌從下面托住右手肘（在思考臂_R 前面）。
Arm:: Think 0.25→0.55：原本的手臂層（story_think 轉動中的上臂、下臂、手掌、握拳）淡出，這兩層淡入；前半段仍是 story_think 的抬手動作。
story_think.py 重跑會拿掉整個 Arm:: Think 參數，之後要再跑本檔（冪等：先拿掉自己的兩層）。
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (TOOLS, TOOLS / 'story_mix', TOOLS / 'guinevere_aub'):
    sys.path.insert(0, str(p))
import mix                                   # noqa: E402
import front as GF                           # noqa: E402
from build_story_trio import set_part_image  # noqa: E402

MID = 'shoe_lady_aubv3'
THINK = 'Arm:: Think'
K = 1.3
FADE = (.25, .55)
LAYERS = ('思考臂_R', '思考臂_L')

LINE, SKIN_LINE = '#3e0c16', '#a4675a'
DEFS = ('<defs>'
        + GF.grad('slv', [(0, '#7a2030'), (.35, '#b14252'), (.6, '#cf5d6a'), (1, '#8e2a3a')])
        + GF.grad('slvv', [(0, '#c55767'), (.5, '#a83b4c'), (1, '#7e2333')], 0, 0, 0, 1)
        + GF.grad('cuff', [(0, '#86283a'), (.5, '#a83d4e'), (1, '#7a2030')])
        + GF.grad('skin', [(0, '#f8dcd2'), (.6, '#f2c9bb'), (1, '#e3ad9e')], 0, 0, 1, 1)
        + '</defs>')


def p(d, fill, line=LINE, w=2.2):
    return f'<path d="{d}" fill="{fill}" stroke="{line}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'


def ln(d, col=LINE, w=1.6, op=.7):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" opacity="{op}"/>'


# ---------------------------------------------------------------- shapes in BASE px, measured on the Gemini comparison image
ARM_R = (
    # upper arm: puffed sleeve hanging at her side, elbow at the waist
    p('M398 280 C384 292 376 318 373 352 C370 392 369 436 372 470 C374 492 384 504 398 504 C410 504 418 494 420 476 '
      'C422 440 421 396 418 352 C416 318 412 292 398 280 Z', 'url(#slv)')
    + ln('M384 330 C380 372 380 420 384 466', '#e98d93', 3.5, .35)
    # forearm: the puffed sleeve rising in front of the chest, cuff at the wrist
    + p('M398 494 C398 462 400 420 404 388 C406 362 420 344 444 338 C458 334 470 334 480 330 L500 324 '
        'C500 352 488 396 468 436 C454 466 438 490 420 504 C410 508 400 504 398 494 Z', 'url(#slv)')
    + ln('M414 378 C428 360 446 350 466 344', LINE, 1.8, .55)
    + ln('M420 470 C440 440 458 404 470 372', '#e98d93', 4, .3)
    + p('M452 318 L496 304 L504 330 L461 344 Z', 'url(#cuff)')
    # the fist under the chin: index finger curled under the chin, thumb along the near side
    + p('M462 316 C456 292 460 266 478 254 C492 244 514 238 528 246 C540 254 540 274 530 290 C522 304 506 316 488 322 '
        'C478 324 466 324 462 316 Z', 'url(#skin)', SKIN_LINE, 2)
    + ln('M478 270 C490 264 504 260 516 260', SKIN_LINE, 1.5, .8)
    + ln('M474 288 C488 282 502 280 514 282', SKIN_LINE, 1.5, .8)
    + ln('M478 304 C490 300 500 298 508 300', SKIN_LINE, 1.5, .8)
    + ln('M528 254 C524 270 520 284 512 296', SKIN_LINE, 1.6, .85)
)

ARM_L = (
    # upper arm hanging at her left side
    p('M602 282 C620 292 636 318 646 352 C656 392 662 436 662 474 C662 500 652 520 634 522 C618 522 610 508 608 488 '
      'C604 446 600 396 596 350 C594 316 594 292 602 282 Z', 'url(#slv)')
    + ln('M640 346 C650 390 654 434 654 476', '#e98d93', 3.5, .3)
    # forearm across the waist, puff bulging downwards
    + p('M650 484 C644 470 612 462 574 464 C548 466 528 472 516 480 L514 530 C536 546 590 552 626 544 '
        'C650 538 662 518 650 484 Z', 'url(#slvv)')
    + ln('M600 476 C590 500 588 520 596 540', LINE, 1.6, .45)
    + p('M478 486 L518 480 L520 532 L480 534 Z', 'url(#cuff)')
    # the hand from below, holding the right elbow; fingers to the left
    + p('M480 490 C456 486 428 486 402 490 C386 492 374 500 380 508 C390 514 414 510 436 512 '
        'C416 516 394 520 386 528 C380 536 392 540 410 536 C440 532 462 536 480 532 Z', 'url(#skin)', SKIN_LINE, 2)
    + ln('M440 498 C424 500 406 502 392 504', SKIN_LINE, 1.4, .75)
    + ln('M444 522 C428 524 412 528 400 530', SKIN_LINE, 1.4, .75)
)

BOXES = {'思考臂_R': (360, 230, 550, 516), '思考臂_L': (366, 274, 676, 560)}
ART = {'思考臂_R': ARM_R, '思考臂_L': ARM_L}


def b2r(x, y):
    return (x - 512) * K, (y - 750) * K


def main():
    M = mix.load(MID)
    assert THINK in M.params, 'run story_think.py first'
    for n in LAYERS:
        if n in M.parts:
            mix.drop_node(M, n)
    prm = M.params[THINK]
    axis = prm['axis_points'][0]
    fade = [float(np.clip((t - FADE[0]) / (FADE[1] - FADE[0]), 0, 1)) for t in axis]
    # every part the think pose moves (and the fist it swaps in) fades out
    moved = {b['node'] for b in prm['bindings']}
    by_uuid = {q['uuid']: q for q in M.parts.values()}
    for uid in moved:
        part = by_uuid.get(uid)
        if not part or part.get('type') != 'Part':
            continue
        op = [b for b in prm['bindings'] if b['node'] == uid and b['param_name'] == 'opacity']
        if op:
            op[0]['values'] = [[v[0] * (1 - f)] for v, f in zip(op[0]['values'], fade)]
        else:
            prm['bindings'].append(dict(node=uid, param_name='opacity', values=[[1 - f] for f in fade],
                                        isSet=[[True] for _ in fade], interpolate_mode='Linear'))
    tmpl = M.parts['胸腔']
    parent = M.parents[tmpl['uuid']]
    front = min(q.get('zsort', 0) for q in M.parts.values() if q.get('type') == 'Part')
    with GF.SVG() as P:
        for i, n in enumerate(LAYERS):
            x0, y0, x1, y1 = BOXES[n]
            img = P.render(DEFS + ART[n], (x0, y0, x1, y1), int((x1 - x0) * 2), int((y1 - y0) * 2))
            part = deepcopy(tmpl)
            part.update(uuid=M.uuid, name=n, masks=[], opacity=1, children=[])
            M.uuid += 1
            parent['children'].append(part)
            M.parents[part['uuid']] = parent
            M.parts[n] = part
            (ax, ay), (bx, by) = b2r(x0, y0), b2r(x1, y1)
            part['mesh'] = dict(origin=[0, 0], indices=[0, 2, 1, 1, 2, 3], uvs=[0, 0, 1, 0, 0, 1, 1, 1], verts=[0] * 8)
            mix.set_wverts(M, part, [(ax, ay), (bx, ay), (ax, by), (bx, by)])
            set_part_image(M, part, img)
            part['zsort'] = front - .02 - .01 * i          # in front of everything: the fist sits on the chin; the left hand over the right elbow
            prm['bindings'].append(dict(node=part['uuid'], param_name='opacity', values=[[f] for f in fade],
                                        isSet=[[True] for _ in fade], interpolate_mode='Linear'))
    M.json['meta'].setdefault('shoeV7', {})['think'] = 'Gemini 比對圖手繪（tools/shoe_v7/lady_think.py）'
    mix.gc_textures(M)
    M.save()
    print(M.path)


if __name__ == '__main__':
    main()
