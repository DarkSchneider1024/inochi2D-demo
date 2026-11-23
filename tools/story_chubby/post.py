# -*- coding: utf-8 -*-
"""胖大叔（chubby_hand_v3 與換裝 baker_chubby_v3）建模後的動作補件（2026-11-23，照 story_passerby/finish.py 的順序；共用工具只匯入、不修改）。

    python -X utf8 inochi2D-demo/tools/story_chubby/post.py <id> [<id> ...]

story_explain.add_explain（講解手）→ story_think.add_think（思考）→ story_burly/arm_rigid.apply（揮手剛性、講解臂）
→ 2026-11-21 規則：`動作/講解` 只舉比 1 的那隻手（拿掉另一手 Reach／Reach Swap 軌道），兩手版另存 `動作/指揮講解`。
只套正面模型（側面沒有講解、思考）。
"""
import os
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'story_burly'))
os.environ['STORY_SQUAT70'] = '0'

from build_story_trio import Model  # noqa: E402
import story_explain  # noqa: E402
import story_think  # noqa: E402
import arm_rigid  # noqa: E402


def single_hand_explain(M):
    clip = M.clips.get('動作/講解')
    if not clip:
        return
    M.clips['動作/指揮講解'] = deepcopy(clip)
    meta = M.json['meta'].get('storyExplain', {})
    up = 'Left' if 'Left' in meta else 'Right'
    other = 'Right' if up == 'Left' else 'Left'
    drop = {M.params[n]['uuid'] for n in (f'Arm:: {other}:: Reach', f'Arm:: {other}:: Reach Swap') if n in M.params}
    clip['lanes'] = [l for l in clip['lanes'] if l['uuid'] not in drop]
    print(f'  動作/講解 單手（{up}），另存 動作/指揮講解；拿掉 {len(drop)} 條另一手軌道')


def main(ids):
    for mid in ids:
        M = Model(mid)
        print(mid)
        story_explain.add_explain(M)
        story_think.add_think(M)
        arm_rigid.apply(M)
        single_hand_explain(M)
        M.save()


if __name__ == '__main__':
    main(sys.argv[1:] or ['chubby_hand_v3'])
