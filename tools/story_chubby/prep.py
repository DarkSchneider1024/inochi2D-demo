"""胖大叔（chubby_hand_v3）底圖整理：Gemini 底圖 687×1024 → 1024×1536 工作底圖（等比 ×1.5、角色中線 x=345 放到 513.5、
往上移 25 px 讓鞋底落在 y≈1500，背景灰 142 換成 #808080）。照 story_tareme/prep.py 的做法（只讀參考，複製改寫）。

    python -X utf8 inochi2D-demo/tools/story_chubby/prep.py
        -> psd-create/images/chubby_hand_v3/base.png、bald_ref/bald_ref_aligned.png、base_note.txt

只做等比縮放與平移（不改比例、不改任何像素的相對位置）。
原始檔：carrot-youtube/人物形象/33_胖大叔/胖大叔_底圖_v2.png、胖大叔_光頭參考_v2.png（2026-11-23 使用者確認 v2；光頭參考身體和底圖逐像素一致，免對位）。
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'carrot-youtube/人物形象/33_胖大叔'
OUT = ROOT / 'psd-create/images/chubby_hand_v3'
S = 1.5
AX_SRC, AX = 345.0, 513.5
DX = AX - AX_SRC * S                # x' = 1.5 x - 4
DY = -25.0
BG = 142


def to_work(x, y):
    return x * S + DX, y * S + DY


def normalise(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    diff = np.abs(a - BG).max(-1)
    sil = diff > 14
    n, lab, st, _ = cv2.connectedComponentsWithStats(sil.astype(np.uint8))
    body = lab == 1 + int(np.argmax(st[1:, 4]))
    body = cv2.dilate(body.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    w = np.clip((diff - 3) / 20, 0, 1)
    w[~body] = 0
    w = w[..., None]
    a = a * w + (a + (128 - BG)) * (1 - w)
    a[~body] = 128
    M = np.float32([[S, 0, DX], [0, S, DY]])
    out = cv2.warpAffine(np.clip(a, 0, 255).astype(np.uint8), M, (1024, 1536), flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(128, 128, 128))
    return Image.fromarray(out)


def main(src_base=None, out_name='base.png', bald=True):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'bald_ref').mkdir(exist_ok=True)
    normalise(Path(src_base) if src_base else SRC / '胖大叔_底圖_v2.png').save(OUT / out_name)
    if bald:
        normalise(SRC / '胖大叔_光頭參考_v2.png').save(OUT / 'bald_ref/bald_ref_aligned.png')
    (OUT / 'base_note.txt').write_text(
        '工作底圖＝carrot-youtube/人物形象/33_胖大叔/胖大叔_底圖_v2.png（Gemini，687×1024）等比 ×1.5，'
        f'x 平移 {DX:+.2f}（角色中線 345 → 513.5）、y 平移 {DY:+.0f}，背景灰 142 換成 128。光頭參考同一組變換。'
        '（inochi2D-demo/tools/story_chubby/prep.py，2026-11-23）\n', encoding='utf-8')
    print(OUT / out_name)


if __name__ == '__main__':
    main(*sys.argv[1:2])
