"""對照圖：doc/角色模型/國王的新衣V6_大臣針先生_對照.jpg（每人一列：底圖｜正面｜臉特寫｜思考｜側面站姿｜側面走路 4 格）
仿 story_v7shoe/doc_sheet.py（不改它）。
    python -X utf8 inochi2D-demo/tools/story_grandpa/newclothes_sheet.py"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'story_v7shoe'))
from shots import Shots      # noqa: E402
from look import walk_pose   # noqa: E402

ROOT = HERE.parents[2]
BASE = ROOT / 'carrot-youtube/人物形象/32_國王的新衣V6換裝'
OUT = ROOT / 'doc/角色模型/國王的新衣V6_大臣針先生_對照.jpg'
font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 22)
W, H = 380, 700
ROWS = [('minister_nc_gpv3', '老大臣', (0, -760, 1.4)), ('needle_nc_m2v3', '針先生', (0, -800, 1.4))]


def main():
    rows = []
    with Shots() as sh:
        for mid, title, face in ROWS:
            base = Image.open(BASE / f'{mid}_底圖_v1.png').convert('RGB')
            base = base.resize((int(base.width * H / base.height), H))
            cells = [('底圖', base),
                     ('正面', sh.shot(mid, {}, (0, 60, .34), (W, H))),
                     ('臉特寫', sh.shot(mid, {}, face, (W, H))),
                     ('思考', sh.shot(mid, {'Arm:: Think': [1, 0]}, (0, 60, .34), (W, H))),
                     ('側面站姿', sh.shot(mid + '_side', {}, (0, 60, .34), (W, H)))]
            cells += [(f'側面走路 {i}', sh.shot(mid + '_side', walk_pose(i), (0, 60, .34), (W, H))) for i in (0, 9, 18, 27)]
            rows.append((title, cells))
    cw = max(c.width for _, cs in rows for _, c in cs)
    n = max(len(cs) for _, cs in rows)
    im = Image.new('RGB', (n * cw, len(rows) * (H + 64)), '#f4ece2')
    d = ImageDraw.Draw(im)
    for r, (title, cs) in enumerate(rows):
        y = r * (H + 64)
        d.text((8, y + 4), f'{title}（{ROWS[r][0]}）', fill='#392c23', font=font)
        for i, (n_, c) in enumerate(cs):
            x = i * cw + (cw - c.width) // 2
            im.paste(c, (x, y + 64))
            d.text((i * cw + 6, y + 34), n_, fill='#5a4636', font=font)
    im.save(OUT, quality=88)
    print(OUT)


if __name__ == '__main__':
    main()
