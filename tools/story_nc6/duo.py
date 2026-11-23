"""《國王的新衣》V6 小朵 duo_nc_carolv3：卡洛兒 v3（carol_hand_v3）換裝成 6～7 歲小女孩（2026-11-23）。

    python -X utf8 tools/story_nc6/duo.py            -> models/duo_nc_carolv3.inp（＋ shared_characters/duo_nc_carolv3/）
    python -X utf8 tools/story_nc6/duo.py --side     -> models/duo_nc_carolv3_side.inp（先要有正面）

底圖 carrot-youtube/人物形象/32_國王的新衣V6換裝/duo_nc_carolv3_底圖_v1.png（Gemini）：金髮雙丸子頭＋兩側垂到胸口的長髮、
淺粉黃圓領短袖洋裝（粉色上身、奶油白前襟兩顆釦、黃色下身、裙子到膝上）、白短襪、黑娃娃鞋。
做法照愛麗絲 alice_carolv3（build_carol_leads.py 的 SPECS 機制，不改那支檔）：在這裡登記自己的 SPECS／RAMPS，部件 SVG 在
tools/carol_leads/duo_nc_carolv3.svg（手繪，座標畫在卡洛兒 v3 的畫布上：同骨架，形狀照底圖的比例量，不描底圖）。
臉、眼、眉、嘴、脖子一層都不動（光頭臉和 carol_hand_v3 逐像素相同；check_carol_leads.py 驗）。
雙丸子頭用卡洛兒的「葉飾」兩層（頭頂兩側、跟頭走、Acc:: Hair Off 一起關）。2026-11-23 使用者「後髮就不要了，跟原圖一樣，兩包頭」：
馬尾兩層隱藏，後髮改成收到後頸的包頭後腦。
小孩比例：模型本身和卡洛兒同骨架同大小，影片裡由 heights.json 縮成小孩身高（見 doc/角色模型/國王的新衣V6角色.md）。
毯子：不畫進模型（站姿不抱毯子）；劇情的小毯子是道具圖 carrot-video/國王的新衣/v6/props/blanket_duo.png（story_nc6/blanket.py）。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
import build_carol_leads as L    # noqa: E402

MID = 'duo_nc_carolv3'
L.RAMPS['babypink'] = ('#7a3c4c', '#b8667a', '#e398a8', '#f6c2cc', '#fbd9de', '#fde9ec', '#fff6f8')
GOLD = 'golden@.2-1.05'
L.SPECS[MID] = dict(
    name='小朵（國王的新衣，卡洛兒 v3）', story='國王的新衣', replaces=['kid'],
    recolor={'bang_right': GOLD, 'bang_center': GOLD, 'side_lock': GOLD, 'glove': 'hand@.6-1.0'},
    layers={
        '後髮_短': dict(group='cap', crop=(386, 90, 252, 258)),
        '馬尾_R': dict(hide=True), '馬尾_L': dict(hide=True),     # 2026-11-23 使用者：「後髮就不要了，跟原圖一樣，兩包頭」
        '葉飾_R': dict(group='bun', crop=(360, 22, 132, 128)),
        '葉飾_L': dict(group='bun', crop=(532, 22, 132, 128), mirror=True),
        '領子_R': dict(group='collar', crop=(448, 358, 128, 62)),
        '裙_中': dict(group='dress_skirt', crop=(316, 598, 392, 262)),
        '裙_擺_R': dict(group='dress_skirt', crop=(316, 846, 196, 104)),
        '裙_擺_L': dict(group='dress_skirt', crop=(512, 846, 196, 104)),
        '馬尾梢_R': dict(hide=True), '馬尾梢_L': dict(hide=True), '蝴蝶結_R': dict(hide=True), '蝴蝶結_L': dict(hide=True),
        '呆毛': dict(hide=True), '髮夾': dict(hide=True), '腰': dict(hide=True),
        '領巾_R': dict(hide=True), '領巾尾_R': dict(hide=True), '領巾尾_L': dict(hide=True), '領巾結': dict(hide=True),
    },
    # 雙丸子在瀏海後面（瀏海蓋住丸子的根）。沒有垂下的長髮：後髮只是包頭的後腦（收到後頸），臉旁只留卡洛兒的短鬢角
    z={'葉飾_R': .155, '葉飾_L': .154},
    clones=[],
    wave=('babypink@.45-1.1', 'hand@.6-1.0'),
)

# 側面（story_carol_side/side.py 的 OUTFIT 登記；不改那支檔）
SIDE_OUTFIT = dict(
    shoe='loafer',                                         # 黑色娃娃鞋（側面低跟皮鞋換黑色、銀扣），白短襪另外補在腳踝
    ear_hair=('#c8961e', '#e8b830', '#f8d860'), ear_hair_line='#8a6410',
    z=dict(),
)
BLACK_SHOE = dict(dark='#0c0c10', mid='#2a2a33', light='#4a4a56', line='#050507', buckle='#d4d8e0', buckle_line='#6a6e78',
                  sole='#16161c')


def build_front():
    L.build(MID)
    L.write_landmarks(MID)


def build_side():
    sys.path.insert(0, str(TOOLS / 'story_carol_side'))
    import side as S
    S.OUTFIT[MID] = SIDE_OUTFIT
    S.LOAFER = BLACK_SHOE
    S.DROP_PARTS = S.DROP_PARTS + ('握拳_', '講解_', '思考')
    S.DROP_PARAMS = S.DROP_PARAMS + ('Arm:: Think',)
    S.build(MID)
    white_socks(MID + '_side')


def white_socks(sid, start=.62):
    """側面的襪子是 sock_tube 從小腿接下來的一段（膚色）：腳踝那段（下面 1-start）改成白短襪＋襪口，形狀（alpha）不動"""
    from io import BytesIO
    import numpy as np
    from PIL import Image
    from build_story_trio import Model, set_part_image
    m = Model(sid)
    for n in ('靴筒_R', '靴筒_L'):
        p = m.parts.get(n)
        if not p:
            continue
        a = np.asarray(Image.open(BytesIO(m.textures[p['textures'][0]][5:])).convert('RGBA')).astype(np.float32)
        H, W = a.shape[:2]
        y0 = int(H * start)
        xs = np.arange(W)
        on = np.where(a[y0, :, 3] > 128)[0]
        if not len(on):
            continue
        c, hw = (on[0] + on[-1]) / 2, max(1, (on[-1] - on[0]) / 2)
        shade = 1 - .22 * np.clip(np.abs(xs - c) / hw, 0, 1) ** 2
        far = n.endswith('_L')
        base = np.array([246, 244, 241], np.float32) * (.86 if far else 1.0)
        a[y0:, :, :3] = base * shade[None, :, None]
        band = slice(y0, min(H, y0 + max(3, H // 14)))
        a[band, :, :3] = np.array([228, 224, 220], np.float32) * (.86 if far else 1.0) * shade[None, :, None]
        set_part_image(m, p, Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    # 側面低跟皮鞋的高光是寫死的暖橘色（給咖啡色皮鞋用的）：黑娃娃鞋上改成同亮度的冷灰
    for n in ('鞋_R', '鞋_L'):
        p = m.parts.get(n)
        if not p:
            continue
        a = np.asarray(Image.open(BytesIO(m.textures[p['textures'][0]][5:])).convert('RGBA')).astype(np.float32)
        rgb = a[..., :3]
        sat = rgb.max(-1) - rgb.min(-1)
        warm = (sat > 18) & (a[..., 3] > 0)
        lum = (rgb * [.299, .587, .114]).sum(-1, keepdims=True) * .6
        a[..., :3] = np.where(warm[..., None], lum * np.array([1.0, 1.0, 1.08]), rgb)
        set_part_image(m, p, Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    m.save()
    print('white socks', m.path)


if __name__ == '__main__':
    if '--side' in sys.argv:
        build_side()
    else:
        build_front()
