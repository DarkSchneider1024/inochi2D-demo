"""《鞋匠與小矮人》V7 太太、農夫、小弟弟上架 Demo 的準備（照 story_mix/publish.py）：把自己的檔放進 sparse clone，只在線上最新版的
official.html／models/versions.json／layers/models.json 加改自己那幾筆。不 commit、不 push（呼叫的人看過 git diff 再做）。

    python -X utf8 tools/shoe_v7/publish.py <clone 目錄> [build]
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
TAG = '【測試版・未回歸】'
INFO = {
    'shoe_lady_aubv3': ('買鞋太太（鞋匠與小矮人，茄子小姐臉模）',
                        '鞋匠與小矮人 V7：茄子小姐 v3 換裝，深紫捲盤髮、玫瑰紅長袖長洋裝、白蕾絲 V 領、深色鞋；講解；思考是照 Gemini 比對圖手繪的托下巴手臂'),
    'shoe_lady_aubv3_side': ('買鞋太太（鞋匠與小矮人・側面）', '側面走路（V1 式 3/4 側身＋九軸正臉）'),
    'shoe_farmer_burlyv3': ('農夫（鞋匠與小矮人，柏達克臉模）',
                            '鞋匠與小矮人 V7：柏達克臉模換裝，草帽（獨立一層跟頭走）、紅格子捲袖襯衫、麻布背心、皮帶、工作褲、泥巴靴；講解、思考'),
    'shoe_farmer_burlyv3_side': ('農夫（鞋匠與小矮人・側面）', '側面走路（V1 式 3/4 側身＋九軸正臉）'),
    'shoe_kid_boyv3': ('小弟弟（鞋匠與小矮人，少年亞瑟小孩模）',
                       '鞋匠與小矮人 V7：少年亞瑟小孩模換裝，淡紫亂髮、紅鼻子、米色粗布短袖、吊帶、補丁深灰七分褲、赤腳；講解、思考'),
    'shoe_kid_boyv3_side': ('小弟弟（鞋匠與小矮人・側面）', '側面走路（V1 式 3/4 側身＋九軸正臉，赤腳、步幅較小）'),
}
ORDER = list(INFO)
ANCHOR = 'shoe_wife_elderfv3_side'


def main(clone, build='20261122-v7shoe-lfk'):
    clone = Path(clone)
    for mid in ORDER:
        for suf in ('.inp', '.inx') + (('.joints.json',) if mid.endswith('_side') else ()):
            src = DEMO / 'models' / f'{mid}{suf}'
            if src.exists():
                (clone / 'models').mkdir(exist_ok=True)
                shutil.copy2(src, clone / 'models' / src.name)
        dst = clone / 'layers' / mid
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(DEMO / 'layers' / mid, dst)
        th = DEMO / 'thumbs' / f'{mid}.png'
        if th.exists():
            (clone / 'thumbs').mkdir(exist_ok=True)
            shutil.copy2(th, clone / 'thumbs' / th.name)
    # official.html: rows after the anchor, ids in the 卡洛兒說故事 group after the anchor
    p = clone / 'official.html'
    s = p.read_text(encoding='utf-8')
    nl = '\r\n' if '\r\n' in s else '\n'
    lines = s.split(nl)
    after = ANCHOR
    for mid in ORDER:
        name, desc = INFO[mid]
        row = f"  {{ id: '{mid}', name: '{name}', desc: '{TAG}{desc}', file: 'models/{mid}.inp' }},"
        have = [k for k, ln in enumerate(lines) if f"{{ id: '{mid}'," in ln]
        if have:
            lines[have[0]] = row
        else:
            i = next(k for k, ln in enumerate(lines) if f"{{ id: '{after}'," in ln)
            lines.insert(i + 1, row)
        g = next(k for k, ln in enumerate(lines) if ln.lstrip().startswith("['卡洛兒說故事', ["))
        if f"'{mid}'" not in lines[g]:
            assert f"'{after}'" in lines[g], '分組裡找不到插入點'
            lines[g] = lines[g].replace(f"'{after}'", f"'{after}', '{mid}'", 1)
        after = mid
    p.write_text(nl.join(lines), encoding='utf-8', newline='')
    # versions.json
    p = clone / 'models/versions.json'
    s = p.read_text(encoding='utf-8')
    for mid in ORDER:
        data = json.loads(s)
        note = '測試版，未回歸：' + INFO[mid][1]
        hist = (data.get(mid) or {}).get('history', [])
        entry = dict(version='2026-11-22', build=build, note=note, history=[dict(version='2026-11-22', build=build, note=note)] + hist)
        block = json.dumps({mid: entry}, ensure_ascii=False, indent=1)[1:-1].strip('\n')
        if mid in data:
            a = s.index(f'\n "{mid}": {{')
            b = s.index('\n }', a) + 3
            s = s[:a] + '\n' + block + s[b:]
        else:
            end = s.rstrip().rindex('}')
            s = s[:end].rstrip() + ',\n' + block + '\n}' + s[end + 1:]
        json.loads(s)
    p.write_text(s, encoding='utf-8', newline='')
    # layers/models.json
    p = clone / 'layers/models.json'
    s = p.read_text(encoding='utf-8')
    for mid in ORDER:
        if not any(m['id'] == mid for m in json.loads(s)):
            end = s.rstrip().rindex(']')
            item = json.dumps([dict(id=mid, name=mid, build='1.0-alpha', private=False, category='story')], ensure_ascii=False, indent=1)[1:-1].strip('\n')
            s = s[:end].rstrip() + ',\n' + item + '\n]' + s[end + 1:]
            json.loads(s)
    p.write_text(s, encoding='utf-8', newline='')
    print('prepared', ORDER, build)


if __name__ == '__main__':
    main(*sys.argv[1:3])
