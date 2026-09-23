# inochi2D-demo

一個在瀏覽器裡即時播放的 [Inochi2D](https://inochi2d.com/) 角色 demo。

**線上版**：<https://darkschneider1024.github.io/inochi2D-demo/>

| 檔案 | 說明 |
| --- | --- |
| `index.html` | demo 頁面：參數滑桿、視線跟著滑鼠或手指、自動眨眼、呼吸、頭髮物理、手臂自然擺動、說話 |
| `inochi-lite.js` | 自寫的精簡 WebGL 播放器，直接讀取 `.inp` 模型 |
| `girl_v4.inp` | Inochi2D 模型（INP 0.8 格式，1200×2000，83 個零件、13 個參數） |
| `girl_v4.inx` | 同一個模型，存成 Inochi Creator 專案的副檔名 |

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
