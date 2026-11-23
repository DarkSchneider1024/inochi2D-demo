"""除錯：線稿誤差依區域分（模型多出 FP、參考有模型缺 FN，像素數）；眼睛各遮罩 IoU。預覽渲染（face_trace.json）。"""
import json, sys, numpy as np
from scipy import ndimage as ndi
import verify_chubby_bald_match as V, face_preview as FP
data = json.loads(open('face_trace.json', encoding='utf-8').read()); g = dict(data['groups'])
for sd in 'RL':
    cp = f'<clipPath id="pv{sd}"><path d="{data["eyes"][sd]["open"]}"/></clipPath>'
    for k in (f'iris_{sd}', f'hilite_{sd}'):
        g[k] = f'<defs>{cp}</defs><g clip-path="url(#pv{sd})">{g[k]}</g>'
img = FP.render_groups(g); ref, _ = V.reference()
res, mf, rf = V.score(img, ref)
print('total', res['summary'])
ex = V.collar_mask(mf['ink'].shape)
a, b = mf['ink'] & ~ex, rf['ink'] & ~ex
tol = V.LINE_TOL * V.K
fa = a & (ndi.distance_transform_edt(~b) > tol); fb = b & (ndi.distance_transform_edt(~a) > tol)
print('ink model', a.sum(), 'ref', b.sum(), 'FP', fa.sum(), 'FN', fb.sum())
R = {'outline_top': (376, 80, 652, 200), 'ear_R': (376, 200, 412, 320), 'ear_L': (615, 200, 652, 320), 'brows': (412, 170, 615, 212),
     'eye_R': (412, 212, 500, 272), 'eye_L': (527, 212, 615, 272), 'nose': (495, 250, 532, 288), 'cheek_R': (412, 260, 470, 300),
     'cheek_L': (557, 260, 615, 300), 'mouth': (470, 285, 557, 335), 'jaw': (376, 300, 652, 384), 'side_R': (376, 200, 412, 320)}
for k, bb in R.items():
    sl = V.box(bb)
    print(f'{k:12s} FP {int(fa[sl].sum()):6d}  FN {int(fb[sl].sum()):6d}')
print({k: round(v * 100, 1) for k, v in res['eyes'].items()})
print({k: v['err'] for k, v in res['pos'].items()})
