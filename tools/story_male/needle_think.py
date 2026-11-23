"""針先生 needle_nc_m2v3 的思考手臂：照 Gemini 比對圖手繪（沿用 shoe_think_draw.py 的做法與程式，不改它，2026-11-23）。
story_think.py 轉出來的握拳只到胸口、碰不到下巴（香皮尼系前臂短），改用手繪的思考手臂／思考拳兩層。
比對圖 carrot-youtube/人物形象/32_國王的新衣V6換裝/needle_nc_m2v3_思考比對圖_Gemini.png（放大到 1024x1536，和底圖同畫布）。
重跑：先 story_think.py needle_nc_m2v3，再跑這支。
    python -X utf8 inochi2D-demo/tools/story_male/needle_think.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import shoe_m2 as SM                 # noqa: E402
import shoe_think_draw as TD         # noqa: E402
import needle_nc as NC               # noqa: E402
from build_story_trio import Model   # noqa: E402

# joints measured on the Gemini picture (base px - (2, 26)); the chin arm is the character's right = picture left
TD.POSE['needle'] = dict(ER=(366, 552), WR=(486, 349), EL=(666, 574), WL=(493, 574))
SM.configure = lambda who: NC.configure()
SM.scene = NC.scene
TD.pal = lambda who: NC.SKIN          # bare hands
TD.main('needle')
m = Model(NC.MID)
m.json['meta']['storyThinkDrawn']['ref'] = f'carrot-youtube/人物形象/32_國王的新衣V6換裝/{NC.MID}_思考比對圖_Gemini.png'
m.save()
