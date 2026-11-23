"""《國王的新衣》V6 麵包師傅 baker_chubby_v3（胖大叔換裝，2026-11-23）。
    python -X utf8 inochi2D-demo/tools/story_chubby/baker.py        -> models/baker_chubby_v3.inp、baker_chubby_v3_side.inp
底圖（造型參考）：carrot-youtube/人物形象/33_胖大叔/baker_chubby_v3_底圖_v1.png（Gemini 在胖大叔底圖 v2 上原位換裝；
工作底圖 psd-create/images/baker_chubby_v3/base.png，和胖大叔的工作底圖同一組座標）。
同一張臉、同一副骨架（build.build 加 outfit），只換身體幾組的畫法、加兩層：
  - 襯衫、袖子、領子改白色（白色麵包師傅襯衫，袖子一樣捲到手肘），前臂撒麵粉；
  - 新層「圍裙」（米色長圍裙：胸片＋掛脖帶＋腰間綁帶蝴蝶結＋到膝下的裙片，撒麵粉），在襯衫與手臂之間，跟軀幹呼吸；
  - 新層「帽子」（白色廚師高帽），掛在頭上、九軸同一套投影，開關 Acc:: Hat Off；光頭（Acc:: Hair Off）時也收起；
  - 吊帶拿掉（腰帶、褲頭留著，被圍裙蓋住）。
部件全部程式手繪（不請 GPT）；光頭臉和 chubby_hand_v3 逐像素相同（臉、五官的層一張都不換）。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art as A          # noqa: E402
import build as BL       # noqa: E402

MID, SID = 'baker_chubby_v3', 'baker_chubby_v3_side'
TITLE = '麵包師傅（胖大叔換裝）'
WHITE = dict(fill='#fbfbf8', light='#ffffff', dark='#e3e6ec', deep='#c8ccd6', line='#3e4250', buttons=False)
APRON, APRON_L, APRON_D, APRON_DD, APRON_LINE = '#dcc6a0', '#ecdcbc', '#c4ab82', '#a98e66', '#5a4630'
FLOUR = '#ffffff'
AX = A.AXIS


def flour(g, spots, op=.75):
    """撒在布上、手臂上的麵粉：幾團柔邊白點"""
    b = g.blur(2.2)
    s = ''
    for x, y, r in spots:
        s += f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * .7:.1f}" fill="{FLOUR}" opacity="{op}" filter="{b}"/>'
        s += ''.join(f'<circle cx="{x + dx}" cy="{y + dy}" r="1.6" fill="{FLOUR}" opacity=".9"/>' for dx, dy in ((-r * .8, -r * .3), (r * .6, r * .5), (r * .9, -r * .6)))
    return s


# ------------------------------------------------------------------ apron (base px of the chubby work base)
# (2026-11-23 第二輪) 跟著啤酒肚：胸片往外鼓、腰間綁帶在肚子下面往下彎、裙片寬到腿外、長度照縮短的腿（膝下）
WY0, WYC = 806.0, 880.0          # 腰帶上緣：兩側 y、二次曲線控制點 y（中間垂到 843）


def waist_y(x, off=0.0):
    return WY0 + off + (WYC - WY0) / 2 * (1 - ((x - AX) / 248) ** 2)


BIB = [(AX - 146, 482), (AX + 146, 482), (AX + 190, 540), (AX + 228, 610), (AX + 250, 700), (AX + 246, 780), (AX + 232, 826), (AX + 120, 846),
       (AX, 852), (AX - 120, 846), (AX - 232, 826), (AX - 246, 780), (AX - 250, 700), (AX - 228, 610), (AX - 190, 540)]
SKIRT = [(AX - 244, 812), (AX - 120, 838), (AX, 846), (AX + 120, 838), (AX + 244, 812), (AX + 256, 920), (AX + 264, 1060), (AX + 268, 1168),
         (AX + 130, 1180), (AX, 1184), (AX - 130, 1180), (AX - 268, 1168), (AX - 264, 1060), (AX - 256, 920)]


def apron():
    g = A.G('apron')
    fill = g.lin(AX - 270, 0, AX + 270, 0, [(0, APRON_D), (.2, APRON), (.5, APRON_L), (.8, APRON), (1, APRON_D)])
    bib = A.curve_d(BIB, True, 5)
    skirt = A.curve_d(SKIRT, True, 5)
    b = g.blur(8)
    s = ''
    # neck straps (base v1): two wide bands from the bib's top corners up over the shoulders, beside the neck and collar
    # (they end behind the collar at y 340; the bib top sits at y 482, well under the chin and the collar)
    for sx in (-1, 1):
        s += A.path(f'M{AX + sx * 146} 486 L{AX + sx * 118} 486 L{AX + sx * 88} 338 L{AX + sx * 112} 336Z', APRON_D, APRON_LINE, 1.8)
    cb = g.clip(bib)
    s += A.path(bib, fill) + (f'<g clip-path="{cb}"><ellipse cx="{AX + 10}" cy="680" rx="220" ry="150" fill="{APRON_L}" opacity=".55" filter="{b}"/>'
                              f'<path d="M{AX - 250} 740 Q{AX} 880 {AX + 250} 740 L{AX + 250} 860 L{AX - 250} 860Z" fill="{APRON_D}" opacity=".6" filter="{b}"/>'
                              f'<path d="M{AX - 252} 560 Q{AX - 214} 690 {AX - 248} 820 L{AX - 262} 820 L{AX - 262} 560Z" fill="{APRON_DD}" opacity=".4" filter="{b}"/>'
                              f'<path d="M{AX + 252} 560 Q{AX + 214} 690 {AX + 248} 820 L{AX + 262} 820 L{AX + 262} 560Z" fill="{APRON_DD}" opacity=".4" filter="{b}"/>'
                              + flour(g, ((AX + 70, 540, 12), (AX - 100, 650, 10), (AX + 130, 700, 9))) + '</g>') + A.path(bib, 'none', APRON_LINE, 2.2)
    cs = g.clip(skirt)
    folds = ''.join(f'<path d="{A.crescent(a, m, e, t)}" fill="{APRON_DD}" opacity=".45"/>' for a, m, e, t in (
        ((AX - 160, 880), (AX - 172, 1030), (AX - 164, 1170), 6), ((AX + 150, 880), (AX + 162, 1030), (AX + 156, 1170), -6),
        ((AX - 40, 900), (AX - 46, 1040), (AX - 40, 1180), 4)))
    s += A.path(skirt, fill) + (f'<g clip-path="{cs}">{folds}<path d="M{AX - 268} 1130 Q{AX} 1200 {AX + 268} 1130 L{AX + 268} 1200 L{AX - 268} 1200Z" '
                                f'fill="{APRON_D}" opacity=".5" filter="{b}"/>' + flour(g, ((AX - 130, 950, 13), (AX + 100, 1040, 11), (AX - 60, 1120, 9))) + '</g>'
                                ) + A.path(skirt, 'none', APRON_LINE, 2.2)
    # waist band (dips under the belly) and the bow (ties hanging down the front)
    band = f'M{AX - 248} {WY0} Q{AX} {WYC} {AX + 248} {WY0} L{AX + 250} {WY0 + 28} Q{AX} {WYC + 28} {AX - 250} {WY0 + 28}Z'
    s += A.path(band, APRON, APRON_LINE, 2.0)
    by = waist_y(AX) + 14          # bow knot centre
    s += A.path(f'M{AX - 6} {by + 4} L{AX - 22} {by + 100} L{AX - 8} {by + 160} L{AX + 2} {by + 158} L{AX - 6} {by + 100} L{AX + 6} {by + 6}Z', APRON_D, APRON_LINE, 1.8)
    s += A.path(f'M{AX + 6} {by + 4} L{AX + 26} {by + 94} L{AX + 22} {by + 148} L{AX + 32} {by + 148} L{AX + 36} {by + 94} L{AX + 14} {by + 4}Z', APRON_D, APRON_LINE, 1.8)
    for sx in (-1, 1):
        s += A.path(f'M{AX} {by} Q{AX + sx * 30} {by - 26} {AX + sx * 46} {by - 12} Q{AX + sx * 50} {by + 10} {AX + sx * 30} {by + 20} '
                    f'Q{AX + sx * 12} {by + 16} {AX} {by + 4}Z', APRON_L, APRON_LINE, 1.8)
    s += A.path(f'M{AX - 9} {by - 8} H{AX + 9} V{by + 14} H{AX - 9}Z', APRON, APRON_LINE, 1.8)
    g.add(s)
    return g


def hat():
    """白色廚師高帽（base v1：寬蘑菇形）：一圈帽帶＋上面一團團分開、各有輪廓與陰影的蓬布"""
    g = A.G('hat')
    # (第二輪) 蓬布畫成一顆顆分開的圓（後面的先畫，前面的蓋上去、各有輪廓線），每顆下緣有灰藍陰影、左上有亮面
    puffs = ((AX - 4, -16, 66), (AX - 96, 22, 62), (AX + 92, 18, 62), (AX - 150, 92, 54), (AX + 148, 88, 54), (AX - 48, 46, 62), (AX + 52, 44, 62))
    s = ''
    for i, (x, y, r) in enumerate(puffs):
        rg = g.uid('pr')
        g.defs.append(f'<radialGradient id="{rg}" cx="{x - r * .3}" cy="{y - r * .4}" r="{r * 1.5}" gradientUnits="userSpaceOnUse">'
                      f'<stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#f4f6fa"/><stop offset="1" stop-color="#c9cfdb"/></radialGradient>')
        s += f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#{rg})" stroke="#3e4250" stroke-width="2.4"/>'
        s += (f'<path d="M{x - r * .62:.1f} {y + r * .42:.1f} Q{x:.1f} {y + r * .78:.1f} {x + r * .62:.1f} {y + r * .42:.1f}" fill="none" '
              f'stroke="#b4bccb" stroke-width="3" stroke-linecap="round" opacity=".7"/>')
        s += f'<ellipse cx="{x - r * .32:.1f}" cy="{y - r * .38:.1f}" rx="{r * .26:.1f}" ry="{r * .16:.1f}" fill="#ffffff" opacity=".9"/>'
    band = f'M{AX - 124} 108 Q{AX} 86 {AX + 124} 108 L{AX + 128} 176 Q{AX} 140 {AX - 128} 176Z'
    s += A.path(band, g.lin(0, 90, 0, 176, [(0, '#ffffff'), (1, '#e3e6ec')]), '#3e4250', 2.4)
    s += f'<path d="M{AX - 124} 158 Q{AX} 124 {AX + 124} 158" fill="none" stroke="#c8ccd6" stroke-width="2.2"/>'
    g.add(s)
    return g


def forearm_flour():
    g = A.forearm()
    g.add(flour(g, ((190, 790, 9), (176, 840, 8), (230, 760, 7)), .8))
    return g


A.OUTFIT.update({'shirt': lambda: A.chest(WHITE), 'upper': lambda: A.sleeve(WHITE), 'collar_front': lambda: A.collar(True, WHITE),
                 'collar_back': lambda: A.collar(False, WHITE), 'forearm': forearm_flour, 'apron': apron, 'hat': hat})


class Outfit:
    Z = {'圍裙': .552}

    def plan(self, model, plan, new_part, copy_breath):
        plan = [p for p in plan if p[0] not in ('背心_R', '背心_L')]
        for n in ('背心_R', '背心_L'):
            BL.drop(model, n)
        part = new_part(model, '圍裙', '胸腔')
        copy_breath(model, part, '胸腔')
        new_part(model, '帽子', '頭頂髮')
        return plan + [('圍裙', 'apron', 0, (10, 14)), ('帽子', 'hat', 0, (8, 6))]

    def after(self, model, P, boxes):
        hat_ = model.parts['帽子']
        hat_['zsort'] = model.parts['頭頂髮']['zsort'] - .002
        for prm in model.params.values():          # the hat: no hair sway, no other carried-over binding (head9 adds its turn)
            prm['bindings'] = [b for b in prm['bindings'] if b['node'] != hat_['uuid']]
        bind = {'node': hat_['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear', 'isSet': [[True], [True]], 'values': [[1], [0]]}
        model.params['Acc:: Hair Off']['bindings'].append(dict(bind))
        model.param('Acc:: Hat Off', [0, 1], [dict(bind)])


def toggles_no_straps(model):
    old = model.params.pop('Acc:: Beard Off', None)
    if old:
        model.json['param'].remove(old)
    model.param('Acc:: Beard Off', [0, 1], [{'node': model.parts['鬍子']['uuid'], 'param_name': 'opacity', 'interpolate_mode': 'Linear',
                                              'isSet': [[True], [True]], 'values': [[1], [0]]}])


if __name__ == '__main__':
    BL.toggles = toggles_no_straps
    BL.build(MID, TITLE, Outfit())
