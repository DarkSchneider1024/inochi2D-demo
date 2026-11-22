"""《鞋匠與小矮人》V7 小弟弟側面走路 shoe_kid_boyv3_side（2026-11-22）。

    python -X utf8 tools/shoe_v7/kid.py          # 先建正面
    python -X utf8 tools/shoe_v7/kid_side.py     -> inochi2D-demo/models/shoe_kid_boyv3_side.inp（.inx、.joints.json）

沿用少年亞瑟小孩模的側面（story_boy/side.py，V1 做法：正面部件轉 3/4 掛走路骨架＋九軸正臉 30 度），只改：
  - 鞋 → 赤腳（側面的小腿、腳踝、朝前進方向的腳掌與腳趾，手繪 SVG）；
  - 步幅再小一點（小孩：STRIDE_K 0.95 → 0.85）；
  - 不拿石中劍，腰臀那塊改深灰七分褲色，講解／思考的手層不帶進側面。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'story_boy'))
import side as S                      # noqa: E402  story_boy/side.py
import art as A                       # noqa: E402
from art import G, path               # noqa: E402

MID = 'shoe_kid_boyv3'


def bare_foot(far):
    """側面赤腳，本地座標：小腿上端中心 (0, 0)、往下 y+；高 h（和 side_boot 同一套擺法）"""
    g = G('side_foot_far' if far else 'side_foot')
    h = 300.0
    fill = g.lin(-70, 0, 180, 0, [(0, A.SKIN_D), (.3, A.SKIN), (.55, A.SKIN_L), (.8, A.SKIN), (1, A.SKIN_D)])
    d = (f'M-50 -8 L50 -8 L48 {h - 112:.0f} Q56 {h - 72:.0f} 104 {h - 54:.0f} Q150 {h - 44:.0f} 168 {h - 24:.0f} '
         f'Q178 {h - 4:.0f} 158 {h:.0f} L-44 {h:.0f} Q-70 {h - 4:.0f} -66 {h - 40:.0f} Q-60 {h - 80:.0f} -50 {h - 112:.0f}Z')
    c = g.clip(d)
    toes = ''.join(f'<path d="M{x} {h - 2:.0f} Q{x - 4} {h - 14:.0f} {x + 2} {h - 22 + i * 2:.0f}" fill="none" stroke="{A.SKIN_LINE}" '
                   f'stroke-width="2" stroke-linecap="round" opacity=".8"/>' for i, x in enumerate((150, 136, 123, 111)))
    ins = (f'<ellipse cx="-4" cy="{h - 104:.0f}" rx="14" ry="11" fill="{A.SKIN_D}" opacity=".55" filter="{g.blur(4)}"/>'
           f'<path d="M-30 30 Q-36 120 -30 {h - 140:.0f}" fill="none" stroke="{A.SKIN_L}" stroke-width="14" stroke-linecap="round" opacity=".5" filter="{g.blur(6)}"/>'
           f'<path d="M-60 {h - 6:.0f} H170 V{h + 10:.0f} H-60Z" fill="{A.SKIN_DD}" opacity=".5"/>'
           f'<ellipse cx="160" cy="{h - 22:.0f}" rx="9" ry="6" fill="#fde7dc" stroke="{A.SKIN_D}" stroke-width="1.4"/>' + toes)
    body = path(d, fill) + f'<g clip-path="{c}">{ins}</g>' + path(d, 'none', A.SKIN_LINE, 2.4)
    g.add(f'<g transform="scale(.74 1)">{body}</g>')
    return g, h


def build():
    import types
    # 小弟弟不拿石中劍：側面腳本裡的「手持劍」換成什麼都不做
    sys.modules['build_mrc_princes'] = types.SimpleNamespace(SWORD_ART={'stone': dict(L=1, gw=1, w=1)}, side_held=lambda *a, **k: None)
    # 腰臀那塊照七分褲的深灰
    A.PANTS_D, A.PANTS, A.PANTS_L, A.PANTS_LINE = '#26261f', '#36362c', '#4a4a3d', '#15150f'
    S.DROP_PARTS = tuple(S.DROP_PARTS) + ('指手_', '講解臂_', '握拳_')
    S.side_boot = bare_foot
    S.STRIDE_K = .85
    S.build(front=MID, sid=MID + '_side', title='小弟弟（鞋匠與小矮人 V7）說故事 v3・側面')


if __name__ == '__main__':
    build()
