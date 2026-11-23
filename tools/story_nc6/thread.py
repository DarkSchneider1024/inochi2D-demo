"""《國王的新衣》V6 線先生（騙子裁縫）thread_nc_burlyv3：柏達克臉模（burly_hand_v3）換裝（2026-11-23）。

    python -X utf8 tools/story_nc6/thread.py            -> models/thread_nc_burlyv3.inp
    python -X utf8 tools/story_nc6/thread.py --side     -> models/thread_nc_burlyv3_side.inp（先要有正面）

底圖 carrot-youtube/人物形象/32_國王的新衣V6換裝/thread_nc_burlyv3_底圖_v1.png（Gemini 原位換裝）：
米色襯衫捲袖、綠條紋背心、皮帶掛線軸＋腰包、棕褲、棕靴；短髮、鬍渣照柏達克。
做法照鞋匠 V7 農夫 shoe_v7/farmer.py（只匯入它和 arthur_cast／hunter 的工具，不改它們）：Head 底下的臉、五官、耳、鬍子、
頭髮一層都不重畫（光頭臉和 burly_hand_v3 逐像素相同）；身體各層同輪廓換畫（手繪 SVG）：背心用 art.vest() 換綠色色票，
直條紋用背心自己的輪廓裁切疊上（SVG，不是貼圖色階化）；線軸是新的一層（綁腰包的動作）。
拿掉：疤、披肩、毛領；前臂護腕拿掉（捲袖露出手臂，同農夫）。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'story_burly'))
sys.path.insert(0, str(TOOLS / 'shoe_v7'))
import arthur_cast as AC                                       # noqa: E402
from arthur_cast import A, B, G, path, shape, hue, tint, palette, BRASSSET  # noqa: E402
import hunter as HU                                            # noqa: E402
import farmer as FA                                            # noqa: E402
from build_story_trio import Model                             # noqa: E402

MID = 'thread_nc_burlyv3'
TITLE = '線先生（國王的新衣，柏達克臉模）'
GREEN = dict(VEST='#5f9a4c', VEST_L='#78b360', VEST_D='#3f7333', VEST_LINE='#1f3a18')
STRIPE = '#2f5f2a'
PANTS = hue(.075, .30, 1.0)                # 棕褲
BROWN_BOOT = dict(BOOT='#6a4630', BOOT_L='#8a6046', BOOT_D='#48301f', BOOT_LINE='#271a10')


def striped_vest():
    """art.vest() 綠色版＋直條紋（用背心自己的輪廓裁切；條紋寬窄照底圖：約 26 px 一組）"""
    with palette(**GREEN):
        g = A.vest()
    import re
    svg = re.sub(r'<circle[^>]*/>', '', g.out())     # 背心的銅釘拿掉（底圖的條紋背心沒有釘）
    d = A.poly_d(A.M['vest_l'])
    stripes = ''.join(f'<rect x="{x}" y="300" width="13" height="700" fill="{STRIPE}" opacity=".55"/>' for x in range(519, 760, 28))
    hl = ''.join(f'<rect x="{x + 14}" y="300" width="3" height="700" fill="#9fd08a" opacity=".25"/>' for x in range(519, 760, 28))
    add = f'<clipPath id="thread_vclip"><path d="{d}"/></clipPath><g clip-path="url(#thread_vclip)">{stripes}{hl}</g>'
    k = svg.rindex('</g>')
    return svg[:k] + add + svg[k:]


def spool():
    """線軸：木頭兩端、米色線圈、一段垂下的線頭，用小皮繩掛在皮帶（腰包左前）"""
    g = G('spool')
    wood = g.lin(300, 0, 360, 0, [(0, '#7a5232'), (.4, '#b98a5c'), (1, '#6a4428')])
    thread = g.lin(306, 0, 354, 0, [(0, '#b9ab8c'), (.35, '#efe4c8'), (.7, '#d9cba8'), (1, '#a8997a')])
    s = path('M330 694 Q326 720 330 744', 'none', '#3a2015', 4)          # 皮繩
    s += path('M306 748 L354 748 L352 760 L308 760Z', wood, '#3a2414', 1.6)   # 上端
    s += path('M310 760 L350 760 L350 806 L310 806Z', thread, '#6e6048', 1.5)
    s += ''.join(f'<path d="M310 {y} Q330 {y + 3} 350 {y}" fill="none" stroke="#a89878" stroke-width="1" opacity=".7"/>' for y in range(766, 804, 5))
    s += path('M306 806 L354 806 L352 818 L308 818Z', wood, '#3a2414', 1.6)   # 下端
    s += path('M348 790 Q366 806 360 828 Q354 846 364 856', 'none', '#cfc2a2', 1.8)   # 線頭
    s += '<ellipse cx="322" cy="776" rx="4" ry="14" fill="#fffaf0" opacity=".45"/>'
    g.add(s)
    return g


def thread(model, P):
    AC.remove(model, ('疤', '疤_頰', '披肩_前', '披肩_後', '毛領_前', '毛領_後'), ('Acc:: Scar Off', 'Acc:: Cape Off', 'Acc:: Fur Off'))
    S = P.scene
    sc = {'vest': striped_vest(), 'forearm': FA.bare_forearm(), 'wave_fore': FA.bare_wave_fore(S['wave_fore'])}
    for gname in ('thigh', 'calf', 'pants_top'):
        sc[gname] = tint(S[gname], PANTS)
    with palette(**BROWN_BOOT):
        sc['boot'] = AC.boot_plain('#7a5238', '#271a10').out()
    AC.dress(model, P, sc)
    HU.lower_sleeve_cap(model, P)          # 沒有披肩蓋肩：袖山改斜肩（同獵人、農夫）
    boxes = {}
    cloth = dict(cloth='#efe5cc', cloth_d='#d2c3a0', line='#7a6646')
    trim = AC.Metal('#efe5cc', '#d2c3a0', '#a89470', '#5a4a30')
    boxes['後領'] = AC.body_layer(model, P, '後領', AC.collar(False, trim=trim, **cloth).out(), .595, (6, 4))
    boxes['前領'] = AC.body_layer(model, P, '前領', AC.collar(True, trim=trim, **cloth).out(), .456, (8, 6))
    z = model.parts['腰包_R']['zsort']
    boxes['線軸'] = AC.body_layer(model, P, '線軸', spool().out(), z - .0004, (4, 6), template='腰包_R')
    for n in ('背心_R', '背心_L'):
        FA.weave(model, n, .06, seed=31 if n.endswith('R') else 32)
    return boxes


def build():
    model = Model(AC.FACE)
    with sync_playwright() as pw:
        P = B.Painter(pw)
        boxes = thread(model, P)
        P.close()
    uid = {p['uuid'] for p in model.json['param']}
    for clip in model.clips.values():
        clip['lanes'] = [l for l in clip['lanes'] if l['uuid'] in uid]
    import head9 as H9
    H9.apply(model, B)
    B.clean_transparent(model)
    B.gc_textures(model)
    model.json['meta'].update(name=TITLE, artist='Claude (story_burly/art.py + story_nc6/thread.py, hand-drawn SVG)',
                              rigger='Claude (story_nc6/thread.py on burly_hand_v3)')
    model.path = AC.MODELS / f'{MID}.inp'
    import os
    import arm_rigid
    from story_squat70 import add_squat70
    add_squat70(model, log=lambda *a: None)
    arm_rigid.apply(model, log=lambda *a: None)
    old = os.environ.get('STORY_SQUAT70')
    os.environ['STORY_SQUAT70'] = '0'
    try:
        model.save()
    finally:
        if old is None:
            os.environ.pop('STORY_SQUAT70', None)
        else:
            os.environ['STORY_SQUAT70'] = old
    print(model.path, boxes)


def build_side():
    import side
    side.DROP_PARTS = tuple(dict.fromkeys(side.DROP_PARTS + ('指手_', '講解臂_', '握拳_', '思考')))
    side.LEG_THIN, side.BOOT_W = HU.LEG_THIN, HU.BOOT_W
    pal = dict(BROWN_BOOT, **{k: PANTS(getattr(A, k)) for k in ('PANTS', 'PANTS_L', 'PANTS_D', 'PANTS_LINE')})
    try:
        with palette(**pal):
            side.build(front=MID, sid=f'{MID}_side', extra_torso=('後領', '前領', '線軸'), title=TITLE + '・側面')
    finally:
        side.LEG_THIN, side.BOOT_W = 1.0, 1.0


if __name__ == '__main__':
    if '--side' in sys.argv:
        build_side()
    else:
        build()
