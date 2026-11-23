"""胖大叔光頭臉相似度（2026-11-23，照 story_tareme/verify_tareme_bald_match.py（只讀，複製改寫）、柏達克、卡洛兒的量法，改胖大叔的框與顏色規則）。

    python -X utf8 inochi2D-demo/tools/story_chubby/verify_chubby_bald_match.py [model.inp] [--out 資料夾] [--tag 名稱]

座標＝工作底圖（psd-create/images/chubby_hand_v3/base.png，prep.py 由 Gemini 底圖等比 ×1.5）。需要角色工坊 serve.py（埠 8876）。
參考圖＝底圖露出的部分用底圖；被頭髮擋住的（頭殼、額頭、耳朵上緣、兩頰外緣）用 Gemini 光頭參考（身體和底圖逐像素一致，免對位）。
頭髮＝底圖和光頭參考差很多的地方（兩眼橢圓內不算），往外擴，接縫羽化。模型用 Acc:: Hair Off＝1（八字鬍留著，兩邊都有）。
分項與權重同卡洛兒、香皮尼、柏達克：膚色輪廓×.25 ＋ 六個眼睛 IoU 平均×.35 ＋ 五官位置×.15 ＋ 線稿 F×.25。門檻 96%，不可再降、不可豁免。
脖子範圍（下顎線以下的雙下巴、領口）不計分（標準脖子）。胖大叔的顏色規則：
  - 虹膜是暖褐：色相 12～48 度、彩度 > .22、亮度 40～200。
  - 上睫毛線＝亮度 < 75 的暗色，但褐色（彩度 < .75、亮度 > 45）算虹膜不算睫毛。
  - 嘴＝八字鬍下面的張嘴笑（MOUTH 框只取鬍子下緣以下），鬍子本身算線稿。
"""
from argparse import ArgumentParser
import base64
from io import BytesIO
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
SCALE = 1.25                     # build.py SCALE
IMG = ROOT / 'psd-create/images/chubby_hand_v3'
OUTPUT = IMG / 'bald_match'
BASE = IMG / 'base.png'
BALD = IMG / 'bald_ref/bald_ref_aligned.png'
DRAFT = ROOT / 'inochi2D-demo/models/chubby_hand_v3.inp'
FRAME = (376, 80, 652, 384)       # 工作底圖座標：整顆光頭含耳朵，下緣到下巴下
K = 4
SKIN_BOTTOM = 380
EYES = {'R': (428, 206, 494, 266), 'L': (533, 206, 599, 266)}
BROWS = {'R': (426, 180, 494, 210), 'L': (533, 180, 601, 210)}
NOSE = (494, 256, 532, 285)
MOUTH = (482, 304, 545, 324)
EYE_ELL = {'R': (461.0, 239.0, 30, 24), 'L': (566.0, 239.0, 30, 24)}
IRIS = {'R': (465.0, 242.5), 'L': (563.5, 242.5)}
JAW_PTS = [(405, 300), (412, 322), (420, 340), (440, 354), (480, 362), (515, 370), (555, 362), (590, 352), (606, 340), (615, 322), (622, 300)]   # 光頭參考的下顎線（雙下巴外緣，逐欄量）
POS_TOL = 8.0
LINE_TOL = 1.5
THRESHOLD = 96.0      # 2026-11-13 使用者：「改 96% 過。」（不可再降、不可豁免；畫質要乾淨才算過）

RENDER = """async ([scale, cx, cy, pose, hide]) => {
  const d = window.demo, p = d.puppet;
  for (const k of Object.keys(d.auto)) d.auto[k] = false;
  p.reset();
  for (const [n, v] of Object.entries(pose)) if (p.has(n)) p.set(n, v[0], v[1]);
  for (let i = 0; i < 3; i++) await new Promise(r => requestAnimationFrame(r));
  for (const [n, v] of Object.entries(pose)) if (p.has(n)) p.set(n, v[0], v[1]);
  p.update();
  const root = [...p.nodes.values()].find(n => n.name === 'Root');
  for (const n of p.parts) n.hide = hide.includes(n.name);
  d.renderer.draw({cx: root.world[12] + (cx - 512) * scale, cy: root.world[13] + (cy - 750) * scale, scale: %d / scale});
  for (const n of p.parts) n.hide = false;
  return document.querySelector('canvas').toDataURL('image/png');
}""" % K


def render(model_path, pose=None):
    # (2026-11-23) 果凍眼的彈簧在 demo 頁一直被驅動（auto 全關仍會晃），眼球每次渲染差 ±0.7 px、分數跳 93～96：量靜止臉，固定 Eye:: Jelly＝0
    x0, y0, x1, y1 = FRAME
    w, h = (x1 - x0) * K, (y1 - y0) * K
    with sync_playwright() as pw:
        page = pw.chromium.launch(channel='msedge').new_page(viewport={'width': 2 * w + 400, 'height': h + 200})
        page.route('**/models/mr_carrot_hand.inp*', lambda route: route.fulfill(path=str(model_path)))
        page.goto('http://127.0.0.1:8876/inochi2D-demo/official.html?model=mr_carrot_hand')
        page.wait_for_function("window.demo?.puppet?.json?.meta?.name?.length > 0", timeout=60000)
        data = page.evaluate(RENDER, [SCALE, (x0 + x1) / 2, (y0 + y1) / 2, pose or {'Acc:: Hair Off': [1, 0], 'Eye:: Jelly': [0, 0]}, []])
    im = Image.open(BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
    cx, cy = im.width // 2, im.height // 2
    if w > im.width or h > im.height:
        raise RuntimeError(f'渲染畫布 {im.size} 小於量測框 {(w, h)}')
    return im.crop((cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h))


def big(path):
    x0, y0, x1, y1 = FRAME
    im = Image.open(path).convert('RGB').crop(FRAME)  # noqa
    return np.asarray(im.resize(((x1 - x0) * K, (y1 - y0) * K), Image.Resampling.BICUBIC)).astype(np.float32)


def box(b):
    x0, y0 = FRAME[:2]
    return slice(int((b[1] - y0) * K), int((b[3] - y0) * K)), slice(int((b[0] - x0) * K), int((b[2] - x0) * K))


def hsv(rgb):
    h = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    return h[..., 0] * 2, h[..., 1] / 255, h[..., 2] / 255


def lum(rgb):
    return rgb @ np.float32([.299, .587, .114])


def eye_ellipses(shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    out = {}
    for s, (cx, cy, rx, ry) in EYE_ELL.items():
        out[s] = ((xx - (cx - FRAME[0]) * K) / (rx * K)) ** 2 + ((yy - (cy - FRAME[1]) * K) / (ry * K)) ** 2 <= 1
    return out


def reference():
    """底圖為主；頭髮蓋住的地方用光頭參考（頭髮＝兩張差很多的地方，眼睛橢圓內不算）。接縫羽化。"""
    base, bald = big(BASE), big(BALD)
    ell = eye_ellipses(base.shape[:2])
    eyes = ell['R'] | ell['L']
    d = np.abs(base - bald).max(-1)
    hair = (ndi.gaussian_filter(d, K * .6) > 32) & ~eyes
    hair = ndi.binary_opening(hair, iterations=K)
    lab, n = ndi.label(hair)
    if n:
        sizes = ndi.sum(hair, lab, range(1, n + 1))
        hair = np.isin(lab, 1 + np.nonzero(sizes > 30 * K * K)[0])
    hair = ndi.binary_closing(hair, iterations=K) & ~eyes
    hair = ndi.binary_dilation(hair, iterations=3 * K) & ~eyes     # 髮梢的淡色毛邊也算頭髮（不讓底圖的髮色暈在光頭外圍）
    a = ndi.gaussian_filter((~hair).astype(np.float32), K * 1.2)[..., None]
    return base * a + bald * (1 - a), ~hair


def features(rgb, alpha=None):
    """同一套規則量參考與模型（模型先疊在 #808080 灰底上）"""
    if alpha is not None:
        rgb = rgb * alpha[..., None] + 128 * (1 - alpha[..., None])
    hue, sat, val = hsv(rgb)
    L = lum(rgb)
    out = {}
    grey = (sat < .1) & (np.abs(val - .5) < .07)
    skin = ~grey if alpha is None else alpha > .5
    skin[int((SKIN_BOTTOM - FRAME[1]) * K):] = False
    skin = ndi.binary_fill_holes(ndi.binary_opening(skin, iterations=2))
    lab, n = ndi.label(skin)
    if n:
        sizes = ndi.sum(skin, lab, range(1, n + 1))
        skin = lab == 1 + int(np.argmax(sizes))
    skin = skin & ~neck_zone(skin.shape)
    out['skin'] = skin
    local = ndi.uniform_filter(L, 9 * K)
    out['ink'] = skin & (L < local - 22)
    ell = eye_ellipses(skin.shape)
    for side, b in EYES.items():
        sl = box(b)
        m = np.zeros_like(skin)
        amber = (hue[sl] > 12) & (hue[sl] < 48) & (sat[sl] > .22) & (L[sl] > 40) & (L[sl] < 200)
        e_ink = (L[sl] < 75) & ~((L[sl] > 45) & amber & (sat[sl] < .75))
        hh, ww = amber.shape
        yy, xx = np.mgrid[0:hh, 0:ww]
        cx, cy = (IRIS[side][0] - b[0]) * K, (IRIS[side][1] - b[1]) * K
        near = ((xx - cx) / (15 * K)) ** 2 + ((yy - cy) / (18 * K)) ** 2 <= 1
        e_iris = ndi.binary_opening(amber & near & ~e_ink, iterations=2)
        hull = np.zeros((hh, ww), np.uint8)
        if e_iris.any():
            ys, xs = np.nonzero(e_iris)
            cv2.fillConvexPoly(hull, cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32)), 1)
        hull = hull.astype(bool)
        # 上睫毛線＝虹膜凸包以外、上半部最大的暗色塊
        e_lash = _biggest(ndi.binary_opening(e_ink & (yy < cy) & ~hull, iterations=1))
        e_iris = hull & ~e_lash
        # 眼白：橢圓內、每一欄睫毛線以下、亮且低彩度、不是虹膜
        below = np.zeros_like(e_lash)
        cols = np.nonzero(e_lash.any(0))[0]
        for c in cols:
            r = np.nonzero(e_lash[:, c])[0].max()
            below[r + 1:, c] = True
        # （眼白和膚色同色）下界＝虹膜最低那一列：眼白不會低於虹膜下緣，再往下是臉頰
        if e_iris.any():
            below[np.nonzero(e_iris.any(1))[0].max() + 1:, :] = False
        e_white = ell[side][sl] & below & (sat[sl] < .22) & (L[sl] > 175) & ~e_iris
        e_white = ndi.binary_opening(e_white, iterations=2)
        lab, n = ndi.label(e_white)
        touch = ndi.binary_dilation(hull, iterations=4 * K)
        keep = [i for i in range(1, n + 1) if (touch & (lab == i)).any()]
        e_white = np.isin(lab, keep)
        for key, part in (('white', e_white), ('iris', e_iris), ('lash', e_lash)):
            mm = m.copy(); mm[sl] = part
            out[f'{key}_{side}'] = mm
        bs = box(BROWS[side])
        brow = (L[bs] < 150) & (sat[bs] > .12) & skin[bs]
        mm = m.copy(); mm[bs] = ndi.binary_opening(brow, iterations=1)
        out[f'brow_{side}'] = mm
    for key, b, thr in (('nose', NOSE, 14), ('mouth', MOUTH, 22)):
        sl = box(b)
        med = np.median(L[sl])
        mm = np.zeros_like(skin)
        mm[sl] = (med - L[sl]) > thr
        mm[sl] = ndi.binary_opening(mm[sl], iterations=1)
        out[key] = mm
    return out


def _biggest(m):
    lab, n = ndi.label(m)
    if not n:
        return m
    return lab == 1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1))))


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def centroid(m):
    ys, xs = np.nonzero(m)
    if not len(xs):
        return None
    return FRAME[0] + (xs.mean() + .5) / K, FRAME[1] + (ys.mean() + .5) / K


def fscore(a, b, tol):
    if not a.any() or not b.any():
        return 0.0, 0.0, 0.0
    da = ndi.distance_transform_edt(~a)
    db = ndi.distance_transform_edt(~b)
    p = float((db[a] <= tol).mean())
    r = float((da[b] <= tol).mean())
    return (2 * p * r / (p + r) if p + r else 0.0), p, r


def _jaw(shape):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    bx, by = FRAME[0] + (xx + .5) / K, FRAME[1] + (yy + .5) / K
    jaw = np.interp(bx, [p[0] for p in JAW_PTS], [p[1] for p in JAW_PTS], left=JAW_PTS[0][1], right=JAW_PTS[-1][1])
    return by, jaw


def collar_mask(shape):
    """線稿不計下顎線往下 3 px 以下（領子、脖子）"""
    by, jaw = _jaw(shape)
    return by > jaw + 3


def neck_zone(shape):
    """脖子範圍：下顎 V 線往下 1 px 以下（只用在膚色輪廓）"""
    by, jaw = _jaw(shape)
    return by > jaw + 1


def score(model_rgba, ref):
    m_rgb = np.asarray(model_rgba).astype(np.float32)
    alpha = m_rgb[..., 3] / 255
    mf = features(m_rgb[..., :3], alpha)
    rf = features(ref)
    res = {'skin': iou(mf['skin'], rf['skin'])}
    eyes = {}
    for side in 'RL':
        for key in ('white', 'iris', 'lash'):
            eyes[f'{key}_{side}'] = iou(mf[f'{key}_{side}'], rf[f'{key}_{side}'])
    res['eyes'] = eyes
    pos = {}
    for key in ('white_R', 'iris_R', 'lash_R', 'white_L', 'iris_L', 'lash_L', 'brow_R', 'brow_L', 'nose', 'mouth'):
        a, b = centroid(mf[key]), centroid(rf[key])
        err = float(np.hypot(a[0] - b[0], a[1] - b[1])) if a and b else 99.0
        pos[key] = dict(model=a, ref=b, err=round(err, 2), score=max(0.0, 1 - err / POS_TOL))
    res['pos'] = pos
    ex = collar_mask(mf['ink'].shape)
    f, p, r = fscore(mf['ink'] & ~ex, rf['ink'] & ~ex, LINE_TOL * K)
    res['line'] = dict(f=f, precision=p, recall=r)
    eye_mean = float(np.mean(list(eyes.values())))
    pos_mean = float(np.mean([v['score'] for v in pos.values()]))
    total = .25 * res['skin'] + .35 * eye_mean + .15 * pos_mean + .25 * f
    res['summary'] = {k: round(100 * v, 2) for k, v in
                      dict(total=total, skin=res['skin'], eyes=eye_mean, pos=pos_mean, line=f).items()}
    return res, mf, rf


def sheet(model_rgba, ref, mf, rf, res, path):
    m = np.asarray(model_rgba).astype(np.float32)
    a = m[..., 3:4] / 255
    comp = (m[..., :3] * a + 128 * (1 - a)).astype(np.uint8)
    refu = np.clip(ref, 0, 255).astype(np.uint8)
    diff = np.full(comp.shape, 255, np.uint8)
    diff[mf['skin'] & rf['skin']] = (225, 225, 225)
    for key in [k for k in rf if k not in ('skin', 'ink')]:
        diff[rf[key] & ~mf[key]] = (60, 110, 255)
        diff[mf[key] & ~rf[key]] = (255, 70, 70)
        diff[mf[key] & rf[key]] = (60, 60, 60)
    diff[rf['skin'] & ~mf['skin']] = (150, 180, 255)
    diff[mf['skin'] & ~rf['skin']] = (255, 170, 170)
    ink = np.full(comp.shape, 255, np.uint8)
    ink[rf['ink']] = (60, 110, 255)
    ink[mf['ink']] = (255, 70, 70)
    ink[mf['ink'] & rf['ink']] = (30, 30, 30)
    panels = [comp, refu, diff, ink]
    h, w = comp.shape[:2]
    out = Image.new('RGB', (w * 4, h + 60), '#f4ece2')
    for i, p in enumerate(panels):
        out.paste(Image.fromarray(p), (i * w, 60))
    d = ImageDraw.Draw(out)
    font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 30)
    s = res['summary']
    d.text((10, 10), f"模型｜參考｜形狀差異（紅多藍缺）｜線稿（紅模型、藍參考、黑重合）  綜合 {s['total']:.2f}%  "
                     f"膚色 {s['skin']:.1f}  眼 {s['eyes']:.1f}  位置 {s['pos']:.1f}  線 {s['line']:.1f}", font=font, fill='#392c23')
    out.resize((out.width // 2, out.height // 2), Image.Resampling.LANCZOS).save(path, quality=92)
    (a0, b0), (a1, b1) = [(int((x - FRAME[0]) * K), int((y - FRAME[1]) * K)) for x, y in ((425, 178), (602, 270))]
    eyes = [Image.fromarray(p[b0:b1, a0:a1]) for p in panels[:3]]
    z = Image.new('RGB', (eyes[0].width, eyes[0].height * 3))
    for i, e in enumerate(eyes):
        z.paste(e, (0, i * e.height))
    z.save(str(path).replace('.jpg', '_眼睛.jpg'), quality=92)


def main():
    ap = ArgumentParser()
    ap.add_argument('model', nargs='?', default=str(DRAFT))
    ap.add_argument('--out', default=str(OUTPUT.with_name('光頭臉比對')))
    ap.add_argument('--tag', default='latest')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ref, hair = reference()
    img = render(Path(a.model).resolve())
    res, mf, rf = score(img, ref)
    sheet(img, ref, mf, rf, res, out / f'光頭臉比對_{a.tag}.jpg')
    Image.fromarray(np.clip(ref, 0, 255).astype(np.uint8)).save(out / '參考_底圖加光頭.png')
    res['passed'] = res['summary']['total'] >= THRESHOLD
    res['model'] = str(a.model)
    (out / f'光頭臉比對_{a.tag}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    s = res['summary']
    eyes = '  '.join(f'{k} {100 * v:.1f}' for k, v in res['eyes'].items())
    pos = '  '.join(f"{k} {v['err']:.2f}" for k, v in res['pos'].items())
    print(f"綜合 {s['total']:.2f}%（{'PASS' if res['passed'] else 'FAIL'}，門檻 {THRESHOLD}）  膚色輪廓 {s['skin']:.2f}  "
          f"眼睛 {s['eyes']:.2f}  位置 {s['pos']:.2f}  線稿 F {s['line']:.2f}"
          f"（P {100 * res['line']['precision']:.1f} R {100 * res['line']['recall']:.1f}）")
    print('眼 IoU：', eyes)
    print('位置誤差 px：', pos)


if __name__ == '__main__':
    main()
