"""《國王的新衣》V6 線先生、小朵上架 Demo 的準備（照 shoe_v7/publish.py）：把自己的檔放進 sparse clone，只在線上最新版的
official.html／models/versions.json／layers/models.json 加改自己那幾筆。不 commit、不 push（呼叫的人看過 git diff 再做）。

    python -X utf8 tools/story_nc6/publish.py <clone 目錄> [build] [只更新的 id,逗號分隔]
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
TAG = '【測試版・未回歸】'
CRLF, LF = chr(13) + chr(10), chr(10)
INFO = {
    'thread_nc_burlyv3': ('線先生（國王的新衣，柏達克臉模）',
                          '國王的新衣 V6：柏達克臉模換裝，騙子裁縫線先生（圓潤矮壯：圓肚子、腿短粗）：米色捲袖襯衫、綠條紋背心、皮帶掛腰包與線軸、棕褲棕靴；講解；思考是照 Gemini 比對圖手繪的托下巴手臂'),
    'thread_nc_burlyv3_side': ('線先生（國王的新衣・側面）', '側面走路（V1 式 3/4 側身＋九軸正臉）'),
    'duo_nc_carolv3': ('小朵（國王的新衣，卡洛兒 v3）',
                       '國王的新衣 V6：卡洛兒 v3 換裝成 6～7 歲小女孩（臉不變、身體縮成約 4 頭身）：金髮雙丸子頭、到胸口的兩側長髮、粉色上身奶油前襟的黃色圓領短袖洋裝、白短襪黑娃娃鞋；講解；思考是照 Gemini 比對圖手繪的托下巴手臂'),
    'duo_nc_carolv3_side': ('小朵（國王的新衣・側面）', '側面走路（V1 式 3/4 側身＋九軸正臉，黑娃娃鞋白短襪）'),
}
ORDER = list(INFO)
ANCHORS = ('king_undies_m2v3_side', 'king_nc_m2v3_side', 'shoe_kid_boyv3_side', 'shoe_farmer_burlyv3_side', 'red_hood_carolv3_side')


def main(clone, build='20261123-nc6-td2', only=''):
    clone = Path(clone)
    order = [m for m in ORDER if not only or m in only.split(',')]
    for mid in order:
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
    after = next(a for a in ANCHORS if any(f"{{ id: '{a}'," in ln for ln in lines))
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
    crlf = CRLF in s
    s = s.replace(CRLF, LF)
    data = json.loads(s)
    indent = 2 if s.startswith('{' + LF + '  "') else 1
    for mid in order:
        note = '測試版，未回歸：' + INFO[mid][1]
        hist = (data.get(mid) or {}).get('history', [])
        data[mid] = dict(version='2026-11-23', build=build, note=note, history=[dict(version='2026-11-23', build=build, note=note)] + hist)
    s = json.dumps(data, ensure_ascii=False, indent=indent) + LF
    p.write_text(s.replace(LF, CRLF) if crlf else s, encoding='utf-8', newline='')
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
    main(*sys.argv[1:4])
