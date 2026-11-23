"""《國王的新衣》V6 小朵的小毯子道具圖（2026-11-23）：手繪 SVG → 透明 PNG。

    python -X utf8 tools/story_nc6/blanket.py   -> carrot-video/國王的新衣/v6/props/blanket_duo.png（摺好拿在手上）
                                                   blanket_duo_open.png（攤開披在國王身上）

毯子是劇情道具（底圖小朵手臂上掛的白色小毯、粉紅滾邊），不畫進模型；劇本用道具圖處理（stage.js 的 prop／ui picture）。
大小：摺好的寬約 0.55 個小朵肩寬，舞台照劇本縮放。
"""
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'carrot-video/國王的新衣/v6/props'

DEFS = ('<defs><linearGradient id="bk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#f1eef8"/>'
        '<stop offset="1" stop-color="#d9d3ea"/></linearGradient>'
        '<linearGradient id="bk2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ece8f4"/><stop offset="1" stop-color="#cfc8e2"/></linearGradient></defs>')
LINE = '#8f86a8'
TRIM = '#f4b8c4'

FOLDED = (DEFS +
          # back layer (the fold hanging down), front layer, pink border along the bottom edges
          f'<path d="M40 70 Q150 50 260 72 L270 300 Q210 318 150 306 Q90 318 34 300 Z" fill="url(#bk2)" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
          f'<path d="M34 286 Q90 304 150 292 Q210 304 270 286 L270 300 Q210 318 150 306 Q90 318 34 300 Z" fill="{TRIM}" stroke="{LINE}" stroke-width="2"/>'
          f'<path d="M20 40 Q150 16 280 42 Q292 120 284 200 Q216 224 150 212 Q84 224 16 200 Q8 120 20 40 Z" fill="url(#bk)" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
          f'<path d="M16 188 Q84 212 150 200 Q216 212 284 188 L284 200 Q216 224 150 212 Q84 224 16 200 Z" fill="{TRIM}" stroke="{LINE}" stroke-width="2"/>'
          f'<path d="M70 50 Q80 120 74 190 M150 36 Q156 110 152 200 M226 46 Q222 120 228 190" fill="none" stroke="#c9c1dd" stroke-width="3" opacity=".7"/>'
          f'<path d="M40 60 Q60 120 50 180" fill="none" stroke="#ffffff" stroke-width="8" opacity=".7" stroke-linecap="round"/>')
OPEN = (DEFS +
        f'<path d="M30 40 Q260 10 490 40 Q520 200 500 360 Q470 390 430 372 Q380 400 330 380 Q280 404 230 382 Q180 404 130 380 Q80 398 40 370 Q8 220 30 40 Z" '
        f'fill="url(#bk)" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
        f'<path d="M40 358 Q80 386 130 368 Q180 392 230 370 Q280 392 330 368 Q380 388 430 360 Q470 378 500 348 L500 360 Q470 390 430 372 Q380 400 330 380 '
        f'Q280 404 230 382 Q180 404 130 380 Q80 398 40 370 Z" fill="{TRIM}" stroke="{LINE}" stroke-width="2"/>'
        f'<path d="M110 50 Q130 200 100 360 M200 40 Q220 200 200 370 M300 40 Q290 200 310 370 M400 44 Q380 200 410 360" fill="none" stroke="#c9c1dd" stroke-width="4" opacity=".6"/>')


def render(page, svg, w, h):
    page.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style><svg xmlns="http://www.w3.org/2000/svg" width="{w * 2}" height="{h * 2}" viewBox="0 0 {w} {h}">{svg}</svg>')
    return Image.open(BytesIO(page.locator('svg').screenshot(omit_background=True))).convert('RGBA')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='msedge')
        pg = br.new_page()
        render(pg, FOLDED, 300, 330).save(OUT / 'blanket_duo.png')
        render(pg, OPEN, 520, 410).save(OUT / 'blanket_duo_open.png')
        br.close()
    print(OUT)
