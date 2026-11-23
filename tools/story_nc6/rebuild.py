"""《國王的新衣》V6 線先生、小朵：從頭重建正面＋側面的完整順序（2026-11-23）。

    python -X utf8 tools/story_nc6/rebuild.py [thread] [duo]      （在 inochi2D-demo 下跑；不給＝兩個都重建）

thread：thread.py → thread.py --side → body.py（側面、正面：矮胖＋圓肚子）→ story_explain → story_burly/arm_rigid（講解臂雙胞胎重新同步）
        → story_think → think_draw thread
duo   ：duo.py → duo.py --side → body.py（側面、正面：小孩頭身）→ story_explain → story_think → think_draw duo
（側面一律從還沒改體型的正面產生，再各自套同一組體型數字，同 story_mix/variants.py。）
（arm_rigid 會在 models/ 留 .bak_20261122_rigid，這裡跑完刪掉。）
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1]
ROOT = DEMO.parent
PY = [sys.executable, '-X', 'utf8']


def run(*args, cwd=DEMO):
    print('>>', ' '.join(map(str, args)), flush=True)
    subprocess.run(PY + list(map(str, args)), cwd=cwd, check=True)


def thread():
    mid = 'thread_nc_burlyv3'
    run('tools/story_nc6/thread.py')
    run('tools/story_nc6/thread.py', '--side')
    run('tools/story_nc6/body.py', mid, '--side')
    run('tools/story_nc6/body.py', mid)
    run('inochi2D-demo/tools/story_explain.py', mid, cwd=ROOT)
    run('tools/story_burly/arm_rigid.py', mid)
    for f in (DEMO / 'models').glob(f'{mid}.in?.bak_20261122_rigid'):
        f.unlink()
    run('inochi2D-demo/tools/story_think.py', mid, cwd=ROOT)
    run('tools/story_nc6/think_draw.py', 'thread')


def duo():
    mid = 'duo_nc_carolv3'
    run('tools/story_nc6/duo.py')
    run('tools/story_nc6/duo.py', '--side')
    run('tools/story_nc6/body.py', mid, '--side')
    run('tools/story_nc6/body.py', mid)
    run('inochi2D-demo/tools/story_explain.py', mid, cwd=ROOT)
    run('inochi2D-demo/tools/story_think.py', mid, cwd=ROOT)
    run('tools/story_nc6/think_draw.py', 'duo')


if __name__ == '__main__':
    todo = sys.argv[1:] or ['thread', 'duo']
    for t in todo:
        {'thread': thread, 'duo': duo}[t]()
