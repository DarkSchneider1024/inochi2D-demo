"""胖大叔（chubby_hand_v3）：從工作底圖量各部件的輪廓（只量形狀，不取顏色、不向量化內部）。
    python -X utf8 inochi2D-demo/tools/story_chubby/measure.py   -> story_chubby/measure.json、measure_masks.npz、角色工坊/輸出/胖大叔/量測疊圖.jpg
做法同 story_boy/measure.py（只讀參考）：底圖依顏色分成 膚／米白（襯衫）／褐（褲）／深（吊帶、鞋、墨線）／髮，墨線歸給最近的顏色；
每個部件＝指定範圍內的某幾類、取最大連通塊、補洞、輪廓平滑。成對部件只量畫面左半（角色右側），建模時對 AXIS 鏡像。
被別的部件擋住的地方（上臂伸進軀幹、前臂伸進袖口、大腿伸進襯衫下、鞋伸進褲管）用手量多邊形補齊。
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'psd-create/images/chubby_hand_v3/base.png'
OUT = ROOT / '角色工坊/輸出/胖大叔'
AXIS = 513.5


def classes(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(int)
    H, S, V = hsv[..., 0] * 2, hsv[..., 1], hsv[..., 2]
    sil = np.abs(rgb.astype(int) - 128).max(-1) > 14
    n, lab, st, _ = cv2.connectedComponentsWithStats(sil.astype(np.uint8))
    sil = lab == 1 + int(np.argmax(st[1:, 4]))
    sil = cv2.morphologyEx(sil.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    Y = np.arange(sil.shape[0])[:, None].repeat(sil.shape[1], 1)
    skin = sil & (S >= 25) & (S <= 120) & ((H <= 30) | (H >= 340)) & (V > 190)
    cream = sil & (S < 35) & (V > 180) & ~skin
    hair = sil & (Y < 330) & (H >= 10) & (H <= 45) & (S > 50) & (V >= 50) & (V < 200)
    pants = sil & (Y > 760) & (H >= 15) & (H <= 45) & (S > 70) & (V >= 70) & (V < 200)
    dark = sil & (V < 90) & ~hair
    names = ['skin', 'cream', 'hair', 'pants', 'dark']
    lab = np.zeros(sil.shape, np.uint8)
    for i, m in enumerate((skin, cream, hair, pants, dark)):
        lab[m] = i + 1
    _, idx = cv2.distanceTransformWithLabels((lab == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(lab)
    lut = np.zeros(idx.max() + 1, np.uint8)
    lut[idx[ys, xs]] = lab[ys, xs]
    full = lut[idx]
    full[~sil] = 0
    return sil, {n: full == i + 1 for i, n in enumerate(names)}, {'dark_raw': dark}


def blob(mask, box=None, close=3, keep=1):
    m = mask.copy()
    if box:
        x0, y0, x1, y1 = box
        z = np.zeros_like(m)
        z[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        m = z
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return np.zeros_like(mask)
    order = np.argsort(-st[1:, 4])[:keep] + 1
    m = np.isin(lab, order).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    cv2.drawContours(out, cs, -1, 1, -1)
    return out.astype(bool)


def outline(mask, sigma=2.0, step=3):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float) + .5
    k = int(sigma * 3)
    w = np.exp(-.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    w /= w.sum()
    ext = np.vstack([c[-k:], c, c[:k]])
    sm = np.stack([np.convolve(ext[:, i], w, 'valid') for i in (0, 1)], 1)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in sm[::step]]


def poly(pts, shape):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


# 手量（底圖 px）：袖子和軀幹的分界（肩→腋下→袖口內側）
ARMPIT = [(372, 372), (330, 404), (312, 470), (302, 560), (296, 620), (288, 690), (282, 760)]


def main():
    rgb = np.asarray(Image.open(BASE).convert('RGB'))
    sil, C, extra = classes(rgb)
    Hh, W = sil.shape
    Y = np.arange(Hh)[:, None].repeat(W, 1)
    X = np.arange(W)[None, :].repeat(Hh, 0)
    left = X < int(AXIS)
    out = {'_axis': AXIS, '_base': BASE.relative_to(ROOT).as_posix()}
    masks = {'sil': sil}
    # head of hair (whole outline incl. the skull under it) and the visible hair with holes
    hair = blob(C['hair'] | (C['skin'] & (Y < 300)), (360, 50, 670, 330), close=7)
    out['hair'] = outline(hair, 1.5, 2)
    masks['hair'] = hair
    hp = C['hair'].copy()
    hp[330:] = False
    hp[168:330, 418:610] = False      # 臉上的眉、眼、八字鬍是褐色但不是頭髮（臉部五官另由 face.py 描）
    hp = cv2.morphologyEx(hp.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(hp)
    hp = np.isin(lab_, [i for i in range(1, n_) if st_[i, 4] > 150]).astype(np.uint8)
    cs, _ = cv2.findContours(hp, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out['hair_front_rings'] = [[[round(float(x) + .5, 1), round(float(y) + .5, 1)] for x, y in c[::2, 0, :]] for c in cs if cv2.contourArea(c) > 40]
    masks['hair_px'] = C['hair']
    # sleeve (right arm, image left): cream left of the armpit line, down to the rolled cuff's lower edge
    cut = poly([(0, 330)] + ARMPIT + [(282, 800), (0, 800)], sil.shape)
    sleeve = blob(C['cream'] & cut, (120, 360, 380, 760), close=5) | poly([(300, 420), (350, 390), (372, 380), (340, 560), (300, 600)], sil.shape)
    sleeve = blob(sleeve, None, 5)
    out['sleeve'] = outline(sleeve, 2.0, 2)
    masks['sleeve'] = sleeve
    fore = blob(C['skin'] & left, (120, 680, 300, 900), close=5) | poly([(168, 690), (276, 730), (262, 760), (160, 720)], sil.shape)
    fore = blob(fore, None, 5)
    out['fore'] = outline(fore, 2.0, 2)
    masks['fore'] = fore
    hand = blob(C['skin'] & left, (110, 840, 260, 1000), close=3)
    out['hand'] = outline(hand, 1.2, 2)
    masks['hand'] = hand
    # shirt torso (both halves, the belly), without the sleeves; it runs on under the collar and the waistband
    torso = blob((C['cream'] | C['dark']) & ~cut & ~poly([(int(2 * AXIS) - x, y) for x, y in [(0, 330)] + ARMPIT + [(282, 800), (0, 800)]], sil.shape),
                 (270, 360, 760, 830), close=7)
    out['torso'] = outline(torso, 2.0, 2)
    masks['torso'] = torso
    strap = blob(extra['dark_raw'] & left, (330, 360, 420, 800), close=3)
    out['strap'] = outline(strap, 1.2, 2)
    masks['strap'] = strap
    leg = blob(C['pants'] & left, (270, 840, int(AXIS), 1400), close=5) | poly([(292, 830), (513, 830), (513, 870), (290, 870)], sil.shape)
    leg = blob(leg, None, 5)
    out['leg'] = outline(leg, 1.5, 2)
    masks['leg'] = leg
    shoe = blob(sil & left & (Y > 1380), (250, 1370, int(AXIS), 1536), close=7) | poly([(326, 1376), (432, 1376), (440, 1404), (318, 1404)], sil.shape)
    shoe = blob(shoe, None, 5)
    out['boot'] = outline(shoe, 1.5, 2)
    masks['boot'] = shoe
    (HERE / 'measure.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    np.savez_compressed(HERE / 'measure_masks.npz', **masks)
    OUT.mkdir(parents=True, exist_ok=True)
    over = rgb.copy() // 2 + 60
    cols = {'hair': (180, 140, 255), 'sleeve': (60, 220, 60), 'fore': (255, 120, 120), 'hand': (255, 170, 120), 'torso': (255, 255, 255),
            'strap': (255, 0, 255), 'leg': (220, 190, 120), 'boot': (150, 80, 40)}
    for k, c in cols.items():
        cv2.polylines(over, [np.array(out[k], np.int32)], True, c, 2)
    Image.fromarray(over).save(OUT / '量測疊圖.jpg', quality=88)
    print({k: (len(v), [round(min(p[i] for p in v)) for i in (0, 1)] + [round(max(p[i] for p in v)) for i in (0, 1)]) for k, v in out.items()
           if isinstance(v, list) and k != 'hair_front_rings'})


if __name__ == '__main__':
    main()
