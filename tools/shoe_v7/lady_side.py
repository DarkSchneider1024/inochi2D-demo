"""買鞋太太側面走路 shoe_lady_aubv3_side：V1 做法（身體 3/4＋九軸正臉約 30 度），2026-11-22。

    python -X utf8 tools/shoe_v7/lady_side.py        -> models/shoe_lady_aubv3_side.inp（.inx、.joints.json）

直接沿用 guinevere_aub/side.py（茄子小姐 v4 長裙骨架的 V1 式側面：關節常數、長裙蓋腿、步伐撐開裙襬），
只換來源模型與服裝設定：沒有武器、披風；長裙下的腿畫成膚色（底圖露出腳踝、深色平底鞋），耳旁頭髮用深紫。
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
spec = importlib.util.spec_from_file_location('guinevere_side', TOOLS / 'guinevere_aub' / 'side.py')
GS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(GS)
S = GS.S

GS.FRONT, GS.SID = 'shoe_lady_aubv3', 'shoe_lady_aubv3_side'
GS.OUTFIT = dict(
    shoe='flat',
    ear_hair=('#2a1838', '#4a3060', '#6d4d86'), ear_hair_line='#120818',
    torso=(),
    held={}, upright={}, held_k={}, dim=(),
    long_skirt=True,
    z=dict(S.FAR_ELBOW),
)
GS.STOCK = [(0, '#c99a92'), (.45, '#e7b6b0'), (.7, '#f2cdc6'), (1, '#d2a49c')]   # bare legs (ankles show under the hem)


def tube(page, x0, y0, y1, w0, w1):
    """guinevere side.tube with a skin outline / highlight instead of the stocking's"""
    h = y1 - y0
    box = (x0 - max(w0, w1) / 2 - 4, y0 - 4, x0 + max(w0, w1) / 2 + 4, y1 + 4)
    d = (f'M{x0 - w0 / 2} {y0} Q{x0 - w0 / 2 - 4} {y0 + h * .45} {x0 - w1 / 2} {y1} L{x0 + w1 / 2} {y1} '
         f'Q{x0 + w0 / 2 + 3} {y0 + h * .45} {x0 + w0 / 2} {y0} Z')
    stops = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in GS.STOCK)
    svg = (f'<defs><linearGradient id="st" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient></defs>'
           f'<path d="{d}" fill="url(#st)" stroke="#8a5a52" stroke-width="2.4"/>'
           f'<path d="M{x0 - w0 * .12} {y0 + 10} Q{x0 - w0 * .14} {y0 + h * .5} {x0 - w1 * .1} {y1 - 6}" stroke="#fbe3dc" '
           f'stroke-width="3" fill="none" opacity=".5" stroke-linecap="round"/>')
    return S.render(page, svg, box, ppu=2.5), box


GS.tube = tube
# 深色平底鞋（底圖）：卡洛兒側面的咖啡色樂福鞋換深色，鞋面反光改灰
S.LOAFER = dict(S.LOAFER, light='#5a4c54', mid='#2c2228', dark='#120c10', line='#08040a')
_loafer0 = S._loafer


def _dark_loafer(far, buckle=True):
    svg, box = _loafer0(far, False)
    return svg.replace('#e9b88a', '#9a8c94').replace('#e0a878', '#7a6c74'), box


S._loafer = _dark_loafer


def build():
    model = GS.build()
    m = model.json['meta']
    m.update(name='買鞋太太（茄子小姐 v3）・側面', artist='Claude (tools/shoe_v7/lady_side.py via guinevere_aub/side.py on shoe_lady_aubv3)')
    model.save()
    return model


if __name__ == '__main__':
    build()
