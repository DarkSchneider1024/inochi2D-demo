"""face_trace.json 的光頭臉直接用 SVG 疊起來量分（不經模型，快速迭代用；正式分數以 verify_chubby_bald_match.py 渲染模型為準）。
    python -X utf8 inochi2D-demo/tools/story_chubby/face_preview.py [--tag x]
"""
import json
import sys
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_chubby_bald_match as V   # noqa: E402

ORDER = ['ear_R', 'ear_L', 'neck', 'face', 'blush_R', 'blush_L', 'eye_R', 'eye_L', 'iris_R', 'iris_L', 'hilite_R', 'hilite_L',
         'lowlash_R', 'lowlash_L', 'lash_R', 'lash_L', 'brow_R', 'brow_L', 'nose', 'smile', 'beard']


def render_groups(groups, order=ORDER, frame=V.FRAME, k=V.K):
    x0, y0, x1, y1 = frame
    w, h = (x1 - x0) * k, (y1 - y0) * k
    body = ''.join(groups[g] for g in order if g in groups)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='msedge')
        page = br.new_page(viewport={'width': w, 'height': h})
        page.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style><svg width="{w}" height="{h}" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}">{body}</svg>')
        png = page.locator('svg').screenshot(omit_background=True)
        br.close()
    return Image.open(BytesIO(png)).convert('RGBA')


def main():
    ap = ArgumentParser()
    ap.add_argument('--tag', default='preview')
    a = ap.parse_args()
    data = json.loads((HERE / 'face_trace.json').read_text(encoding='utf-8'))
    groups = dict(data['groups'])
    try:
        import art
        groups['neck'] = art.neck().out()
    except Exception:
        pass
    for sd in 'RL':     # the model masks the eyeball and its highlight with the eye white
        cp = f'<clipPath id="pvclip{sd}"><path d="{data["eyes"][sd]["open"]}"/></clipPath>'
        for g in (f'iris_{sd}', f'hilite_{sd}'):
            groups[g] = f'<defs>{cp}</defs><g clip-path="url(#pvclip{sd})">{groups[g]}</g>'
    img = render_groups(groups)
    ref, _ = V.reference()
    res, mf, rf = V.score(img, ref)
    out = V.IMG / '光頭臉比對'
    out.mkdir(parents=True, exist_ok=True)
    V.sheet(img, ref, mf, rf, res, out / f'光頭臉比對_{a.tag}.jpg')
    s = res['summary']
    print(f"綜合 {s['total']:.2f}%  膚色 {s['skin']:.2f}  眼 {s['eyes']:.2f}  位置 {s['pos']:.2f}  線 {s['line']:.2f}"
          f"（P {100 * res['line']['precision']:.1f} R {100 * res['line']['recall']:.1f}）")
    print('  '.join(f'{k} {100 * v:.1f}' for k, v in res['eyes'].items()))
    print('  '.join(f"{k} {v['err']:.2f}" for k, v in res['pos'].items()))


if __name__ == '__main__':
    main()
