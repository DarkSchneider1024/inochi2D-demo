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
BIB = [(AX - 146, 482), (AX + 146, 482), (AX + 178, 540), (AX + 205, 600), (AX + 222, 700), (AX + 214, 780), (AX - 214, 780), (AX - 222, 700),
       (AX - 205, 600), (AX - 178, 540)]
SKIRT = [(AX - 226, 790), (AX + 226, 790), (AX + 236, 950), (AX + 244, 1120), (AX + 248, 1232), (AX + 120, 1244), (AX, 1248), (AX - 120, 1244),
         (AX - 248, 1232), (AX - 244, 1120), (AX - 236, 950)]


def apron():
    g = A.G('apron')
    fill = g.lin(AX - 250, 0, AX + 250, 0, [(0, APRON_D), (.2, APRON), (.5, APRON_L), (.8, APRON), (1, APRON_D)])
    bib = A.curve_d(BIB, True, 5)
    skirt = A.curve_d(SKIRT, True, 5)
    b = g.blur(8)
    s = ''
    # neck straps (base v1): two wide bands from the bib's top corners up over the shoulders, beside the neck and collar
    # (they end behind the collar at y 340; the bib top sits at y 482, well under the chin and the collar)
    for sx in (-1, 1):
        s += A.path(f'M{AX + sx * 146} 486 L{AX + sx * 118} 486 L{AX + sx * 88} 338 L{AX + sx * 112} 336Z', APRON_D, APRON_LINE, 1.8)
    cb = g.clip(bib)
    s += A.path(bib, fill) + (f'<g clip-path="{cb}"><ellipse cx="{AX}" cy="640" rx="190" ry="120" fill="{APRON_L}" opacity=".5" filter="{b}"/>'
                              f'<path d="M{AX - 214} 720 Q{AX} 800 {AX + 214} 720 L{AX + 214} 790 L{AX - 214} 790Z" fill="{APRON_D}" opacity=".6" filter="{b}"/>'
                              + flour(g, ((AX + 70, 520, 12), (AX - 90, 640, 10), (AX + 120, 680, 9))) + '</g>') + A.path(bib, 'none', APRON_LINE, 2.2)
    cs = g.clip(skirt)
    folds = ''.join(f'<path d="{A.crescent(a, m, e, t)}" fill="{APRON_DD}" opacity=".45"/>' for a, m, e, t in (
        ((AX - 150, 840), (AX - 160, 1040), (AX - 150, 1230), 6), ((AX + 140, 840), (AX + 150, 1040), (AX + 146, 1230), -6),
        ((AX - 40, 880), (AX - 46, 1060), (AX - 40, 1240), 4)))
    s += A.path(skirt, fill) + (f'<g clip-path="{cs}">{folds}<path d="M{AX - 248} 1190 Q{AX} 1270 {AX + 248} 1190 L{AX + 248} 1260 L{AX - 248} 1260Z" '
                                f'fill="{APRON_D}" opacity=".5" filter="{b}"/>' + flour(g, ((AX - 120, 950, 13), (AX + 90, 1060, 11), (AX - 60, 1150, 9))) + '</g>'
                                ) + A.path(skirt, 'none', APRON_LINE, 2.2)
    # waist band and the bow (ties hanging down the front)
    s += A.path(f'M{AX - 226} 778 Q{AX} 792 {AX + 226} 778 L{AX + 228} 806 Q{AX} 820 {AX - 228} 806Z', APRON, APRON_LINE, 2.0)
    s += A.path(f'M{AX - 6} 800 L{AX - 22} 900 L{AX - 8} 960 L{AX + 2} 958 L{AX - 6} 900 L{AX + 6} 802Z', APRON_D, APRON_LINE, 1.8)
    s += A.path(f'M{AX + 6} 800 L{AX + 26} 890 L{AX + 22} 944 L{AX + 32} 944 L{AX + 36} 890 L{AX + 14} 800Z', APRON_D, APRON_LINE, 1.8)
    for sx in (-1, 1):
        s += A.path(f'M{AX} 796 Q{AX + sx * 30} 770 {AX + sx * 46} 784 Q{AX + sx * 50} 806 {AX + sx * 30} 816 Q{AX + sx * 12} 812 {AX} 800Z', APRON_L, APRON_LINE, 1.8)
    s += A.path(f'M{AX - 9} 788 H{AX + 9} V{810} H{AX - 9}Z', APRON, APRON_LINE, 1.8)
    g.add(s)
    return g


def hat():
    """白色廚師高帽：一圈帽帶＋上面五團蓬起來的布"""
    g = A.G('hat')
    # base v1: a wide mushroom cap (x 340-680) of big puffs over a band that arches up in the middle
    puffs = ((AX - 138, 120, 54), (AX + 136, 114, 54), (AX - 78, 64, 66), (AX + 74, 60, 66), (AX - 2, 30, 68))
    fill = g.lin(0, -30, 0, 170, [(0, '#ffffff'), (.6, '#f6f7fa'), (1, '#dfe3ea')])
    s = ''
    for x, y, r in puffs:                      # outlines first (so the overlaps read as one cloud), then the fills
        s += f'<circle cx="{x}" cy="{y}" r="{r + 1.6}" fill="#3e4250"/>'
    for x, y, r in puffs:
        s += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'
    s += ''.join(f'<path d="M{x - r * .5} {y + r * .55} Q{x} {y + r * .25} {x + r * .45} {y + r * .6}" fill="none" stroke="#c8ccd6" stroke-width="2.4" stroke-linecap="round"/>'
                 for x, y, r in puffs[:4])
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
