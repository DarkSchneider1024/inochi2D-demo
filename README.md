# inochi2D-demo

一個在瀏覽器裡即時播放的 [Inochi2D](https://inochi2d.com/) 角色 demo。

**線上版**：<https://darkschneider1024.github.io/inochi2D-demo/>

| 檔案 | 說明 |
| --- | --- |
| `index.html` | Demo 頁：可切換角色（`?model=<id>` 或下拉選單），有參數滑桿、視線跟著滑鼠或手指、自動眨眼、呼吸、頭髮物理、手臂自然擺動、說話 |
| `gallery.html` | 作品集頁：用卡片列出所有角色，點一下就在 Demo 裡開啟 |
| `official.html` | 精緻展示作品頁（原「公版範例」，`?model=aka` / `midori` / `carol_v2`）：Inochi2D 官方範例角色 Aka、Midori（seagetch，CC BY 4.0），視線跟隨、眨眼、呼吸、說話、晃動展示、全部參數滑桿、物理即時輸出 |
| `inochi-full.js` | 給 Inochi Creator 綁的模型用的 WebGL2 播放器：3D 節點變換、MeshGroup、遮罩、Composite、混合模式、Pendulum／SpringPendulum 物理 |
| `models/official/*.inp` | 官方範例模型，用 `tools/inx_to_inp.py` 從 `../example-models/*.inx` 把 TGA 貼圖轉成 PNG（瀏覽器不能解 TGA），JSON 未改 |
| `models.json` | 角色清單（兩個頁面共用）：id、名稱、說明、模型檔、縮圖 |
| `inochi-lite.js` | 自寫的精簡 WebGL 播放器，直接讀取 `.inp` 模型 |
| `models/*.inp`、`models/*.inx` | Inochi2D 模型：girl_v4（紫髮水手服少女）、red_hood（小紅帽）、wolf（大野狼） |
| `thumbs/*.png` | 作品集縮圖 |
| `model3d.html` | 3D 角色頁（`?model=<id>`）：VRM 角色用 three-vrm 播放（眨眼、表情、嘴型、視線、頭髮物理），另有程式建模的卡洛特女孩；邊緣光、Bloom、視角切換 |
| `models3d/*.vrm` | VRoid 範例角色：`vroid_girl`（VRM1_Constraint_Twist_Sample © pixiv Inc.，VRM Public License 1.0）、`avatar_a/b/c`（AvatarSample © VRoid Project）。皆允許修改與再散佈、可商用、不需標註 |
| `models3d/carrot_girl.glb` | 卡洛特女孩 3D 模型，由 `../Blender/build_carrot_girl.py` 以 Blender 5.2 產生 |

新增角色：把 `.inp` 放進 `models/`、縮圖放進 `thumbs/`，再在 `models.json` 加一筆就會出現在作品集。

## 本機執行

頁面要用 `fetch` 讀取模型，所以要透過本機伺服器開啟：

```bash
python -m http.server 8765
```

然後打開 <http://localhost:8765>。

## 模型參數

| 參數 | 範圍 | 效果 |
| --- | --- | --- |
| `Head:: Yaw-Pitch` | −1..1 × −1..1 | 轉頭：分層視差，遠側的眼睛會變窄（近大遠小） |
| `Head:: Roll` | −1..1 | 歪頭，以脖子為軸心 |
| `Eye:: Left/Right:: Blink` | 0..1（1 = 閉眼） | 眨眼 |
| `Mouth:: Open` | 0..1 | 張嘴 |
| `Body:: Breath` | 0..1 | 呼吸 |
| `Arm:: Right/Left:: Swing` | −1..1 | 手臂以肩膀為軸往外、往內擺（網格變形，越往下角度越大） |
| `Arm:: Right/Left:: Bend` | 0..1 | 以手肘為軸彎曲，只作用在手肘以下，並做平滑過渡 |
| `Hand:: Right/Left:: Wrist` | −1..1 | 以手腕為軸轉動手掌和手指 |
| `Basket:: Swing` / `Tail:: Sway` | −1..1 | 小紅帽的籃子、大野狼的尾巴擺動（只有該角色才有） |
| `Hair:: Sway` | −1..1 | 頭髮擺動（網格變形），由物理驅動 |

## 播放器支援範圍

`inochi-lite.js` 依照 Inochi2D 的官方實作（inochi2d v0.8.7 和 inox2d）撰寫，支援：
- 讀取 INP 容器
- 節點變換
- 數值綁定和網格變形（雙線性內插）
- 依 zsort 排序繪製，使用 Normal 混合

尚未實作：遮罩、Composite、MeshGroup、其他混合模式、動畫。頭髮物理是用阻尼擺近似的。

## 驗證

- 在預設參數下，WebGL 畫出的結果跟角色原始 PSD 的合成圖逐像素比對，最大誤差 2/255。
- 模型檔另外用驗證腳本檢查過結構和必填欄位。
- 還沒有在 Inochi Creator 裡實際開過。

角色、模型和播放器都是在本機的 gimp-test 專案裡用 Python 產生的：
- 繪圖程式：`src/claude5.5_live2d/girl_v4.py`
- 模型綁定：`src/inochi2d/make_puppet.py`

## 晃動檢核（找破圖、殘塊）

Demo 頁畫面左下角有兩個按鈕：

- **🌀 晃動**：約 10 秒的大晃動，像 VTuber 模型展示影片那樣：快速左右甩頭（身體慢半拍、頭髮甩起來）→ 大繞圈（上下左右轉到底）→ 歪頭＋點頭到極限 → **極限掃描**（頭髮、尾巴、籃子等所有擺動參數從 −1 掃到 +1，頭依序轉到四個角）→ 回正。晃動期間會接管頭部參數，其他時候不影響原本的滑桿。
- **📸 即時截圖**：在晃動過程中每 0.1 秒擷取一張（沒在晃動時按下會自動開始晃動，並先拍一張站姿當參考）。再按一次可以提早停止。結束後跳出檢核視窗：
  - 縮圖依時間排列，每張標出時間、頭髮擺動值、轉頭／俯仰／歪頭角度。
  - **紅框＝殘塊**：跟身體分離的碎片，或只剩細細一條連著（快斷開）的碎片，而且站姿裡沒有。
  - **黃框＝破洞**：頭和脖子附近比站姿多出來的封閉空洞。
  - 可以「只看疑點」、點縮圖放大（← → 換張、可下載原圖），或下載整張聯絡表 PNG。
  - 自動檢查只是幫忙找；碎片如果剛好疊在別的零件上（例如髮尾碎片疊在手套上）就抓不到，最後還是要用眼睛看。

在瀏覽器以外批次檢查時，`window.demo.shakeSnap` 可以拿到所有截圖（`list[i].c` 是 canvas）。
