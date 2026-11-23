"""胖大叔對照圖（2026-11-23）：每個模型一列
底圖｜正面｜臉特寫｜光頭對光頭參考｜表情（開心、害羞、驚訝、生氣、難過）｜講解｜思考｜側面站姿｜走路 4 格｜側面頭部
    python -X utf8 inochi2D-demo/tools/story_chubby/sheets.py [out.jpg]   -> doc/角色模型/胖大叔_對照.jpg
需要角色工坊 serve.py（埠 8876）。渲染工具匯入 story_burly/shots.py（只讀）。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'story_burly'))
sys.path.insert(0, str(HERE.parent))
from shots import Shots          # noqa: E402
from build_story_trio import Model  # noqa: E402

ROOT = HERE.parents[2]
S = 1.25
ROWS = [('chubby_hand_v3', 'chubby_hand_v3_side', 'psd-create/images/chubby_hand_v3/base.png', 'psd-create/images/chubby_hand_v3/bald_ref/bald_ref_aligned.png'),
        ('baker_chubby_v3', 'baker_chubby_v3_side', 'psd-create/images/baker_chubby_v3/base.png', 'psd-create/images/chubby_hand_v3/bald_ref/bald_ref_aligned.png')]
H = 520
FONT = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 20)


def wy(y):
    return (y - 750) * S


def walk_pose(mid, t):
    M = Model(mid)
    c = M.clips['動作/走路']
    names = {p['uuid']: n for n, p in M.params.items()}
    fr = t * c['length']
    pose = {}
    for l in c['lanes']:
        kf = l['keyframes']
        v = kf[-1]['value']
        for a, b in zip(kf, kf[1:]):
            if a['frame'] <= fr <= b['frame']:
                u = (fr - a['frame']) / max(1e-9, b['frame'] - a['frame'])
                v = a['value'] + (b['value'] - a['value']) * u
                break
        n = names.get(l['uuid'])
        if n:
            pose.setdefault(n, [0.0, 0.0])[l.get('target', 0)] = v
    return pose


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 28), fill=(250, 248, 240))
    d.text((6, 2), text, fill=(30, 30, 30), font=FONT)
    return im


def fit(im, h=H):
    return im.resize((max(1, round(im.width * h / im.height)), h))


def row(sh, front, side, base, bald):
    cells = []
    if (ROOT / base).exists():
        cells.append(label(fit(Image.open(ROOT / base).convert('RGB').crop((150, 20, 874, 1530))), '底圖'))
    full = (0, wy(780), .262)
    cells.append(label(sh.shot(front, {}, full, (380, H)), '正面'))
    face = (0, wy(235), 1.55)
    cells.append(label(sh.shot(front, {}, face, (380, H)), '臉特寫'))
    bald_m = sh.shot(front, {'Acc:: Hair Off': [1, 0], 'Eye:: Jelly': [0, 0]}, face, (380, H))
    br = Image.open(ROOT / bald).convert('RGB')
    # the bald reference at the same framing: centre (512, 235) base px, 380 px wide view = 380 / (1.55 * 1.25) base px
    span_w, span_h = 380 / (1.55 * S), H / (1.55 * S)
    bc = br.crop((round(512 - span_w / 2), round(235 - span_h / 2), round(512 + span_w / 2), round(235 + span_h / 2))).resize((380, H))
    pair = Image.new('RGB', (760, H)); pair.paste(bald_m, (0, 0)); pair.paste(bc, (380, 0))
    cells.append(label(pair, '光頭（模型｜光頭參考）'))
    ex = [('開心', {'Expression:: Happy': [1, 0]}), ('害羞', {'Face:: Story Blush': [1, 0], 'Expression:: Happy': [.4, 0]}),
          ('驚訝', {'Eye:: Shock': [1, 0], 'Mouth:: Open': [1, 0], 'Mouth:: Form': [1, 0]}), ('生氣', {'Expression:: Angry': [1, 0]}),
          ('難過', {'Expression:: Sad': [1, 0], 'Face:: Tears': [1, 0]})]
    grid = Image.new('RGB', (3 * 230, 2 * (H // 2)), (128, 128, 128))
    for i, (n, p) in enumerate(ex):
        im = label(sh.shot(front, p, (0, wy(250), 1.25), (230, H // 2)), n)
        grid.paste(im, ((i % 3) * 230, (i // 3) * (H // 2)))
    cells.append(label(grid, '表情'))
    cells.append(label(sh.shot(front, {'Arm:: Left:: Explain': [1, 0], 'Arm:: Left:: Point': [1, 0]}, full, (380, H)), '講解（單手比 1）'))
    cells.append(label(sh.shot(front, {'Arm:: Think': [1, 0]}, full, (380, H)), '思考'))
    cells.append(label(sh.shot(front, {'Arm:: Wave': [1, 0]}, full, (380, H)), '揮手'))
    if (ROOT / f'inochi2D-demo/models/{side}.inp').exists():
        cells.append(label(sh.shot(side, {}, full, (380, H)), '側面站姿'))
        walk = Image.new('RGB', (4 * 260, H))
        for i in range(4):
            walk.paste(label(sh.shot(side, walk_pose(side, i / 4), (0, wy(780), .262), (260, H)), f'走路 {i + 1}/4'), (i * 260, 0))
        cells.append(walk)
        cells.append(label(sh.shot(side, {}, (40, wy(235), 1.4), (380, H)), '側面頭部'))
    w = sum(c.width for c in cells) + 6 * len(cells)
    out = Image.new('RGB', (w, H), (255, 255, 255))
    x = 0
    for c in cells:
        out.paste(c, (x, 0)); x += c.width + 6
    return out


def main(out=None):
    out = Path(out) if out else ROOT / 'doc/角色模型/胖大叔_對照.jpg'
    rows = []
    with Shots() as sh:
        for front, side, base, bald in ROWS:
            if (ROOT / f'inochi2D-demo/models/{front}.inp').exists():
                rows.append(row(sh, front, side, base, bald))
    W = max(r.width for r in rows)
    sheet = Image.new('RGB', (W, sum(r.height + 8 for r in rows)), (255, 255, 255))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height + 8
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
