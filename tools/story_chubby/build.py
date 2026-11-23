"""胖大叔說故事 v3（chubby_hand_v3）建模（2026-11-23）。
    python -X utf8 inochi2D-demo/tools/story_chubby/build.py   -> inochi2D-demo/models/chubby_hand_v3.inp、psd-create/images/chubby_hand_v3/landmarks.json
    （之後跑 story_explain.py、story_think.py 加講解、思考；講解 clip 改單手版由 post.py 做）

做法照柏達克、垂眼姐姐（story_burly/build.py、story_tareme/build.py，skill story-handpaint-alignment 第 6 節）：骨架、參數、表情、
動作沿用 mr_carrot_hand_v3（只讀），
  - 全部部件照他自己的底圖量形狀（measure.py、face.py）後手繪（art.py、expr.py），換成平均網格放在量到的框；
  - 臉、眼、眉、鼻、嘴、耳、八字鬍是他自己描出的光頭臉（face_trace.json，96% 量法 verify_chubby_bald_match.py）；九軸 head9.py；
  - 眨眼用網格變形（照他自己每欄量到的開口），果凍眼、揮手、手臂剛體旋轉同柏達克；
  - 八字鬍：複製「臉」的網格與全部綁定的獨立圖層（不破框、不和臉分離），開關 Acc:: Beard Off；
  - 吊帶左右兩層（沿用卡洛特背心的兩層），開關 Acc:: Suspenders Off；襯衫領前後兩片夾住粗脖子。
共用程式只匯入不修改：story_burly/build.py 的函式（把它的模組常數換成這裡的值）、build_story_trio、arm_rigid。
"""
from copy import deepcopy
import importlib.util
import json
import math
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))                       # this folder's art / expr / head9 first
sys.path.append(str(TOOLS / 'story_burly'))         # arm_rigid
import art                                          # noqa: E402
import expr                                         # noqa: E402,F401  (before the burly module puts its folder first)
import head9 as H9                                  # noqa: E402
from build_story_trio import set_part_image, rotate  # noqa: E402,F401

_spec = importlib.util.spec_from_file_location('burly_build_shared', TOOLS / 'story_burly/build.py')
BB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BB)

ROOT = TOOLS.parents[1]
MODELS = TOOLS.parent / 'models'
MID = 'chubby_hand_v3'
TITLE = '胖大叔說故事 v3'
SRC = 'mr_carrot_hand_v3'
BASE = 'carrot-youtube/人物形象/33_胖大叔/胖大叔_底圖_v2.png'
BALD_TOP = 83.5
SOLE = art.SOLE      # (2026-11-23 第二輪) 腿短粗：鞋底 1500 → 1414.4（art.LEG_Y）
# 光頭頭頂 83.5 → 鞋底 1500 = 1416.5 底圖 px；卡洛特 1434 × 1.3 = 1864 模型單位；身高 95 % → 1771 / 1416.5
SCALE = 1.25
AXIS = art.AXIS
HEAD_PIVOT = (AXIS, 385.0)

Z = {
    '後領': .595, '脖子': .59, '脖子影': .585, '胸腔': .58, '前領': .575, '腰帶': .5825, '背心_R': .56, '背心_L': .555, '褲頭': .61,
    '大腿_R': .636, '大腿_L': .635, '小腿_R': .632, '小腿_L': .631, '鞋_R': .64, '鞋_L': .639,
    '上臂_R': .466, '上臂_L': .4655, '揮手上臂_R': .466, '揮手上臂_L': .4655, '手掌_R': .4652, '手掌_L': .4647, '下臂_R': .464, '下臂_L': .4635,
    '揮手前臂_R': .452, '揮手前臂_L': .451,
    '閉眼線_R': .2295, '閉眼線_L': .2295, '腮紅_R': .07, '腮紅_L': .07,
}
DROP = ('眼鏡', '背帶', '水壺', '指南針', '領巾', '腰包_L', '腰包_R', '襯衫領', '手指_R', '手指_L', '臉陰影', '臉線', '瀏海', '襯衫下擺',
        '推鏡上臂_R', '推鏡前臂_R', *[f'{n}_{s}' for n in ('上睫毛', '上眼皮', '下眼皮', '眼褶', '閉眼') for s in 'RL'])

BB.SCALE, BB.Z, BB.art, BB.TR, BB.AXIS = SCALE, Z, art, art.TRACE, AXIS
BB.SHOULDER, BB.ELBOW, BB.WRIST = art.SHOULDER, art.ELBOW, art.WRIST
BB.WAVE_TURN, BB.WAVE_LEAN, BB.WAVE_SWAY = 14.0, -14.0, .15
BB.SWING, BB.SWING_FORE, BB.BEND, BB.WRIST_TURN, BB.GREET = 6.0, 3.0, 14.0, 10.0, 140.0
BB.HAIR_C = (AXIS, 150.0)
world, place, fit, new_part, drop, bind, abs_pos, base_xy = BB.world, BB.place, BB.fit, BB.new_part, BB.drop, BB.bind, BB.abs_pos, BB.base_xy


def move_node(model, name, bx, by):
    node = model.parts[name]
    cx, cy = world(bx, by)
    ax, ay = abs_pos(model, node)
    node['transform']['trans'][0] += cx - ax
    node['transform']['trans'][1] += cy - ay
    for ch in node.get('children', []):
        ch['transform']['trans'][0] -= cx - ax
        ch['transform']['trans'][1] -= cy - ay


def copy_breath(model, part, template):
    for prm in model.params.values():
        prm['bindings'] += [dict(deepcopy(b), node=part['uuid']) for b in prm['bindings']
                            if b['node'] == model.parts[template]['uuid'] and b['param_name'] == 'transform.t.y']


def hair_sway(model):
    """短髮：頭頂、髮尾小幅擺動，鬢角（耳朵高度以下）不動"""
    sway = model.params['Hair:: Sway']
    keys = sway['axis_points'][0]
    names = ('後髮_主', '頭頂髮')
    sway['bindings'] = []
    for name, amp in (('後髮_主', 3.0), ('頭頂髮', 5.0)):
        part = model.parts[name]
        pts = base_xy(model, part)

        def fn(x, y, ph, amp=amp):
            r = math.hypot(x - AXIS, y - 200.0)
            w = max(0.0, min(1.0, (r - 70) / 80)) ** 1.3
            if y > 200:
                w *= max(0.0, 1 - (y - 200) / 30)
            vary = 1 + .3 * math.sin(x / 9.0) * math.cos(y / 13.0)
            return [ph * w * amp * vary, -abs(ph) * w * 1.4]
        bind(model, 'Hair:: Sway', part, 'deform', [[[v * SCALE for v in fn(x, y, 2 * k - 1)] for x, y in pts] for k in keys])
    model.params['Acc:: Hair Off']['bindings'] = [
        {'node': model.parts[n]['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear', 'isSet': [[True], [True]], 'values': [[1], [0]]} for n in names]


def toggles(model):
    for name, layers in (('Acc:: Beard Off', ('鬍子',)), ('Acc:: Suspenders Off', ('背心_R', '背心_L'))):
        old = model.params.pop(name, None)
        if old:
            model.json['param'].remove(old)
        model.param(name, [0, 1], [{'node': model.parts[n]['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                    'isSet': [[True], [True]], 'values': [[1], [0]]} for n in layers])


def build(mid=MID, title=TITLE, outfit=None):
    """outfit: baker.py 的換裝（只換身體幾組的畫法、可加圖層），臉、頭、骨架不變"""
    from build_story_trio import Model
    model = Model(SRC)
    root = model.parts['Root']
    move_node(model, 'Head', *HEAD_PIVOT)
    for name, template in (('後領', '背心_R'), ('前領', '背心_R')):
        part = new_part(model, name, template)
        copy_breath(model, part, template)
    for n in [n for n in model.parts if n in DROP or n.startswith(('Hair Lock ', '舉手上臂_', '握手_', '無掌_'))]:
        drop(model, n)
    old = model.params.pop('Acc:: Glasses Off', None)
    if old:
        model.json['param'].remove(old)
    carrot_boxes = {n: [v / SCALE + (512 if i % 2 == 0 else 750) for i, v in enumerate(model.box(p, root))]
                    for n, p in model.parts.items() if p.get('type') == 'Part'}
    boxes = {}
    TR = art.TRACE
    with sync_playwright() as pw:
        P = BB.Painter(pw)
        plan = [('脖子', 'neck', 0, (5, 10)), ('後領', 'collar_back', 0, (6, 3)), ('胸腔', 'shirt', 0, (10, 10)), ('前領', 'collar_front', 0, (8, 4)),
                ('腰帶', 'belt', 0, (10, 3)), ('褲頭', 'pants_top', 0, (8, 4)), ('背心_R', 'strap', 0, (3, 10)), ('背心_L', 'strap', 1, (3, 10)),
                ('後髮_主', 'hair_back', 0, (12, 12)), ('頭頂髮', 'hair_front', 0, (12, 12))]
        for stem, group, grid in (('上臂', 'upper', (6, 12)), ('下臂', 'forearm', (6, 9)), ('手掌', 'hand', (5, 7)), ('大腿', 'thigh', (2, 2)),
                                  ('小腿', 'calf', (2, 2)), ('鞋', 'boot', (2, 2))):
            plan += [(f'{stem}_R', group, 0, grid), (f'{stem}_L', group, 1, grid)]
        plan += [('臉', 'face', 0, (10, 10)), ('耳朵_R', 'ear_R', 0, (4, 5)), ('耳朵_L', 'ear_L', 0, (4, 5)), ('鼻子', 'nose', 0, (4, 5)),
                 ('腮紅_R', 'blush_R', 0, (4, 4)), ('腮紅_L', 'blush_L', 0, (4, 4)),
                 ('故事差分_眉毛_怒', 'brows_angry', 0, (8, 3)), ('故事差分_眉毛_哀', 'brows_sad', 0, (8, 3)),
                 ('嘴_啊', 'm_a', 0, (4, 4)), ('嘴_喔', 'm_o', 0, (4, 4)), ('故事差分_嘴_笑_Happy', 'm_happy', 0, (4, 4)),
                 ('故事差分_嘴_平_Angry', 'm_angry', 0, (4, 4)), ('故事差分_嘴_嘟_Sad', 'm_sad', 0, (4, 4)), ('故事差分_嘴_啊_Laugh', 'm_laugh', 0, (4, 4)),
                 ('故事差分_淚_積', 'tear_pool', 0, (8, 3)), ('故事差分_淚_滴', 'tear_drop', 0, (8, 4))]
        for s_ in 'RL':
            plan += [(f'故事差分_閉眼_{s_}_Happy', f'eye_happy_{s_}', 0, (4, 4)), (f'故事差分_閉眼_{s_}_Laugh', f'eye_laugh_{s_}', 0, (4, 4)),
                     (f'故事差分_怒眼_{s_}_Angry', f'lid_angry_{s_}', 0, (6, 4)), (f'故事差分_哀眼_{s_}_Sad', f'lid_sad_{s_}', 0, (6, 4))]
        for n, group in (('眼白', 'eye'), ('眼球', 'iris'), ('高光', 'hilite'), ('上眼線', 'lash'), ('下眼線', 'lowlash')):
            plan += [(f'{n}_R', f'{group}_R', 0, BB.EYE_GRID), (f'{n}_L', f'{group}_L', 0, BB.EYE_GRID)]
        for s_ in 'RL':
            new_part(model, f'閉眼線_{s_}', f'上眼線_{s_}')
            plan.append((f'閉眼線_{s_}', f'eye_shut_{s_}', 0, (14, 3)))
        if outfit:
            plan = outfit.plan(model, plan, new_part, copy_breath)
        coarse = {'neck', 'collar_back', 'shirt', 'belt', 'pants_top', 'strap', 'hair_back', 'upper', 'forearm', 'hand', 'thigh', 'calf', 'boot'}
        for name, group, mirror, grid in plan:
            box = P.box(group, bool(mirror))
            place(model, name, box, P.paint(group, box, bool(mirror), k=2 if group in coarse else 4), grid)
            boxes[name] = box
        for name, group in (('眉毛_R', 'brow_R'), ('眉毛_L', 'brow_L'), ('上唇', 'smile')):
            box = P.box(group)
            part = fit(model, name, box)
            set_part_image(model, part, P.paint(group, box, k=4))
            part['opacity'] = 1
            boxes[name] = box
        for n in ('下唇陰影', '口腔', '舌頭', '下排牙齒', '上排牙齒'):
            model.parts[n]['opacity'] = 0
        fbox = boxes['臉']
        cf = carrot_boxes['臉']
        fx = lambda x: fbox[0] + (x - cf[0]) * (fbox[2] - fbox[0]) / (cf[2] - cf[0])
        fy = lambda y: fbox[1] + (y - cf[1]) * (fbox[3] - fbox[1]) / (cf[3] - cf[1])
        for n in ('故事差分_臉紅_1', '故事差分_臉紅_2', '故事差分_臉紅_3'):
            b = carrot_boxes[n]
            fit(model, n, (fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])))
        for s in 'RL':
            node = model.parts[f'EyeBall {s}']
            cx, cy = world(*TR['eyes'][s]['centre'])
            ax, ay = abs_pos(model, node)
            node['transform']['trans'][0] += cx - ax
            node['transform']['trans'][1] += cy - ay
            for ch in node['children']:
                ch['transform']['trans'][0] -= cx - ax
                ch['transform']['trans'][1] -= cy - ay
        # --- rigs
        BB.head_motion(model)
        BB.eye_rig_traced(model)
        hair_sway(model)
        BB.arm_rig(model)
        boxes.update(BB.wave(model, P))
        # the handlebar mustache: a copy of the face (its mesh and every binding), drawn inside the face's box
        mouth_z = min(model.parts[n]['zsort'] for n in ('上唇', '嘴_啊', '嘴_喔', '故事差分_嘴_笑_Happy', '故事差分_嘴_平_Angry',
                                                        '故事差分_嘴_嘟_Sad', '故事差分_嘴_啊_Laugh'))
        Z['鬍子'] = mouth_z - .002
        BB.face_copy(model, '鬍子', P.paint('beard', fbox, k=4))
        boxes['鬍子'] = fbox
        new_part(model, '脖子影', '鼻子')
        for prm in model.params.values():
            prm['bindings'] = [x for x in prm['bindings'] if x['node'] != model.parts['脖子影']['uuid']]
        nsb = P.box('neck_shadow')
        place(model, '脖子影', nsb, P.paint('neck_shadow', nsb), (5, 4))
        model.parts['脖子影']['masks'] = [{'source': model.parts['脖子']['uuid'], 'mode': 'Mask'}]
        if outfit:
            outfit.after(model, P, boxes)
        P.close()
    BB.jelly_eyes(model)
    toggles(model)
    H9.apply(model, BB)
    for n in ('眉毛_R', '眉毛_L', '故事差分_眉毛_怒', '故事差分_眉毛_哀'):
        model.parts[n]['zsort'] = .006
    for n, z in Z.items():
        if n in model.parts:
            model.parts[n]['zsort'] = z
    if outfit:
        for n, z in outfit.Z.items():
            if n in model.parts:
                model.parts[n]['zsort'] = z
    shadow = model.parts['影子']
    shadow['transform']['trans'][1] = world(AXIS, SOLE)[1]
    for name in ('Arm:: Right:: Glasses', 'Glasses:: Push'):
        p = model.params.pop(name, None)
        if p:
            model.json['param'].remove(p)
    model.clips.pop('動作/推眼鏡', None)
    uid = {p['uuid'] for p in model.json['param']}
    for clip in model.clips.values():
        clip['lanes'] = [l for l in clip['lanes'] if l['uuid'] in uid]
    BB.clean_transparent(model)
    BB.gc_textures(model)
    model.json['meta'].update(name=title, artist='Claude (story_chubby/art.py, hand-drawn SVG)', rigger='Claude (story_chubby/build.py on mr_carrot_hand_v3)')
    model.path = MODELS / f'{mid}.inp'
    model.save()
    landmarks(model, boxes, mid)
    print(model.path, 'parts', sum(1 for p in model.parts.values() if p.get('type') == 'Part'), 'textures', len(model.textures))
    return model


def landmarks(model, boxes, mid=MID):
    work = f'psd-create/images/{mid}/base.png'
    L = dict(id=mid, date='2026-11-23', unit=f'底圖像素 [x0,y0,x1,y1]（工作底圖 {work}）', base=BASE, base_work=work,
             builder='inochi2D-demo/tools/story_chubby/build.py', face_gate='inochi2D-demo/tools/story_chubby/verify_chubby_bald_match.py', adjust={},
             note='胖大叔：Gemini 底圖等比 ×1.5 成工作底圖（prep.py）。身體、頭髮照底圖量輪廓（measure.py）或手量點後手繪（art.py）；臉照光頭參考描形（face.py）。'
                  '量測框＝各部件 SVG 繪製範圍（含被擋住、手量補上的部分：肩頭、上臂伸進軀幹、褲頭、大腿）。左側四肢、吊帶對 x=513.5 鏡像；'
                  '脖子照標準脖子（胖一點、不描底圖）；八字鬍是臉的複製層。')
    skip = ('揮手', '故事差分', '閉眼線')
    L['boxes'] = {n: [round(float(v), 1) for v in b] for n, b in boxes.items() if not n.startswith(skip) and n in model.parts}
    d = ROOT / 'psd-create/images' / mid
    d.mkdir(parents=True, exist_ok=True)
    try:
        old = json.loads((d / 'landmarks.json').read_text(encoding='utf-8'))
        for k in ('bald_ref', 'bald_ref_note'):
            if k in old:
                L[k] = old[k]
    except (OSError, ValueError):
        pass
    L.setdefault('bald_ref', f'psd-create/images/{MID}/bald_ref/bald_ref_aligned.png')
    (d / 'landmarks.json').write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
    (d / 'height.json').write_text(json.dumps(dict(bald_top_base_px=BALD_TOP, sole_base_px=SOLE, bald_to_sole_base_px=SOLE - BALD_TOP,
                                                   bald_to_sole_model_units=round((SOLE - BALD_TOP) * SCALE, 1), hair_top_base_px=50.0,
                                                   note='工作底圖 1024×1536；模型單位＝底圖 px × 1.25；卡洛特 v3 光頭頭頂到鞋底 1434 × 1.3 = 1864 模型單位；'
                                                        '95 % ≈ 1771'), ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    build()


SHOULDER, ELBOW, WRIST = art.SHOULDER, art.ELBOW, art.WRIST
clean_transparent, gc_textures, set_world = BB.clean_transparent, BB.gc_textures, None
