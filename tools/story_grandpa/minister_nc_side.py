"""老大臣側面走路 minister_nc_gpv3_side（V1 做法：3/4 側身＋九軸正臉約 30 度），沿用 story_grandpa/side.py（不改它）：
  - 袍領、袍襬跟軀幹同一個柱面一起轉（加進 TORSO）；帽子、眼鏡、長鬍是頭部層，九軸烘進網格時一起轉。
  - 長袍：步幅縮成 STRIDE 倍（腿留在袍子裡，照梅林 story_merlin/side.py），袍襬下半跟近側腳前後擺 HEM_FOLLOW。
  - 側面另畫的褲頭、鞋用老大臣的深紫黑褲、黑棕鞋。
    python -X utf8 inochi2D-demo/tools/story_grandpa/minister_nc_side.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.argv = [sys.argv[0], 'minister_nc_gpv3', 'minister_nc_gpv3_side']
import side as S          # noqa: E402
import minister_nc as MN  # noqa: E402

STRIDE = .55
HEM_FOLLOW = .22

S.DROP_PARTS = S.DROP_PARTS + ('指手_', '握拳_', '講解_', '思考')
S.DROP_PARAMS = S.DROP_PARAMS + ('Arm:: Think', 'Acc:: Robe Collar Off')
S.TORSO = S.TORSO + ('袍領', '袍襬')
S.HALF['袍領'] = 216.0
S.HALF['袍襬'] = 216.0
for k, v in {**MN.PANTS, **MN.SHOES}.items():
    setattr(S.A, k, v)
_extra = S.side_extra
S.side_extra = lambda n, x, y, hair: _extra(n, x, y, hair or n == '帽子')     # 帽子跟後腦髮量一起往後撐，蓋住後腦的頭髮
S.build()

sys.path.insert(0, str(HERE.parent))
from build_story_trio import Model  # noqa: E402
import build as B                   # noqa: E402
M = Model('minister_nc_gpv3_side')
sm = lambda t: (lambda q: q * q * (3 - 2 * q))(max(0.0, min(1.0, t)))
for side in ('Front', 'Back'):
    for j in ('Hip', 'Knee', 'Foot'):
        prm = M.params[f'Leg:: {side}:: {j}']
        for b in prm['bindings']:
            b['values'] = [[q * STRIDE for q in row] for row in b['values']]
# 袍襬下半跟近側腳（Front Hip）前後擺
prm = M.params['Leg:: Front:: Hip']
rz = next(b for b in prm['bindings'] if b['param_name'] == 'transform.r.z')
a0, a1 = rz['values'][0][0], rz['values'][-1][0]
prm['axis_points'] = [[0.0, .5, 1.0], [0.0]]
for b in prm['bindings']:
    v0, v1 = b['values'][0][0], b['values'][-1][0]
    b['values'], b['isSet'] = [[v0], [(v0 + v1) / 2], [v1]], [[True], [True], [True]]
part = M.parts['袍襬']
px, py = B.abs_pos(M, part)
hip_y, hem_y = (S.HIP[1] - 750) * B.SCALE, (1470 - 750) * B.SCALE
leg_len = (S.ANKLE[1] - S.HIP[1]) * B.SCALE
v = part['mesh']['verts']
frames = [[[-leg_len * math.sin(ang) * HEM_FOLLOW * sm((yy + py - hip_y) / (hem_y - hip_y)) ** 1.3, 0.0] for yy in v[1::2]] for ang in (a0, 0.0, a1)]
prm['bindings'].append({'node': part['uuid'], 'param_name': 'deform', 'interpolate_mode': 'Linear', 'isSet': [[True]] * 3, 'values': [[fr] for fr in frames]})
M.json['meta']['name'] = '老大臣（國王的新衣）・側面'
M.save()
print('side robe', M.path)
