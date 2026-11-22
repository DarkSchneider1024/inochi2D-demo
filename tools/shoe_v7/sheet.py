"""《鞋匠與小矮人》V7 太太、農夫、小弟弟對照圖：doc/角色模型/鞋匠V7_太太農夫小弟弟_對照.jpg

    python -X utf8 tools/shoe_v7/sheet.py [輸出路徑]       （要本機 8876 伺服器）

一人一列：底圖｜正面｜臉特寫｜講解｜思考｜側面站姿｜側面走路 4 格。
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'story_burly'))
sys.path.insert(0, str(HERE.parent / 'guinevere_aub'))
from shots import Shots   # noqa: E402
from sheet import walkpose   # noqa: E402

ROOT = HERE.parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'doc/角色模型/鞋匠V7_太太農夫小弟弟_對照.jpg'
BASES = ROOT / 'carrot-youtube/人物形象/30_鞋匠與小矮人V7換裝'
FONT = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 22)
W, H = 420, 860
PEOPLE = [('shoe_lady_aubv3', '買鞋太太', -770), ('shoe_farmer_burlyv3', '農夫', -760), ('shoe_kid_boyv3', '小弟弟', -640)]


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 10 + d.textlength(text, font=FONT), 32), fill=(0, 0, 0))
    d.text((5, 3), text, fill='white', font=FONT)
    return im


def base_tile(mid):
    im = Image.open(BASES / f'{mid}_底圖_v1.png').convert('RGB')
    k = H / im.height
    im = im.resize((round(im.width * k), H), Image.LANCZOS)
    x = (im.width - W) // 2
    return im.crop((x, 0, x + W, H))


def main():
    rows = []
    with Shots() as sh:
        for mid, name, fy in PEOPLE:
            side = mid + '_side'
            full = lambda m, p={}: sh.shot(m, p, focus=(0, -90, .38), size=(W, H))
            t = [label(base_tile(mid), f'{name} 底圖'), label(full(mid), '正面'),
                 label(sh.shot(mid, {}, focus=(0, fy, 1.5), size=(W, H)), '臉特寫'),
                 label(full(mid, {'Arm:: Right:: Explain': [1, 0]}), '講解'),
                 label(full(mid, {'Arm:: Think': [1, 0]}), '思考'),
                 label(full(side), '側面站姿')]
            t += [label(full(side, walkpose(2 * math.pi * i / 8)), f'走路 {i // 2 + 1}/4') for i in range(0, 8, 2)]
            rows.append(t)
    o = Image.new('RGB', (W * max(map(len, rows)), H * len(rows)), '#808080')
    for r, t in enumerate(rows):
        for c, im in enumerate(t):
            o.paste(im, (c * W, r * H))
    o.thumbnail((4200, 4200))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    o.save(OUT, quality=88)
    print(OUT)


if __name__ == '__main__':
    main()
