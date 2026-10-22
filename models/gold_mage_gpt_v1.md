# 金髮魔導學者 — GPT / Inochi2D v1

2026-10-23。依使用者提供的 1024×1536 全身角色圖，沿用專案 Live2D PSD / Inochi2D skills 製作。

線上互動：https://darkschneider1024.github.io/inochi2D-demo/?model=gold_mage_gpt_v1
下載：https://darkschneider1024.github.io/inochi2D-demo/downloads/gold_mage_gpt_v1.zip

## 交付

- 主 PSD：3072×4608，40 個圖層；表情 PSD：4 個圖層。兩檔均全圖層可見、通常混合、100% 不透明度，沒有圖層遮罩。原稿解析度為 1024×1536，PSD 放大不代表新增原畫細節。
- INP / INX：44 張材質，19 個參數。原生 Inochi2D 0.8 網格資料；不是 Cubism .moc3。
- 閉眼、左右單眼眨眼、兩種嘴型、視線、眉毛、呼吸、轉頭、歪頭、身體微轉、左右手臂、衣襬、墜飾、抬腳。
- 手拿書、另一手插口袋，因此手臂只做小幅動作，保留原姿勢；不包含換姿勢揮手或90度側身。

## 做法與重建

先以 imagegen 內建工具產生對齊素頭／遮擋補圖，以及無眼鏡差分。SAM 分部位，LaMa 補小範圍遮擋，原圖服裝與道具像素保留。素頭採完整單一來源，分離眼睛、眉毛、鼻子、嘴巴，眼鏡以量測路徑重描。表情以超採樣筆刷形狀製作。

在 carrot-entertainment 專案根目錄執行：

```
python psd-create/src/gpt_gold_mage/segment.py
python psd-create/src/gpt_gold_mage/build_character.py
python psd-create/src/gpt_gold_mage/qa_browser.py
```

依賴：Python、Pillow、numpy、OpenCV、psd-tools、onnxruntime、Playwright / Edge；沿用 src/claude5.5_live2d/build.py、girl.py、cv_models.py，以及本機 models_cv 的 SAM / LaMa。圖層資料與全部建置程式均保留，未覆寫既有角色。

## 驗證與限制

結構驗證、PSD round-trip、GIMP 第二讀取器、WebGL 1:1 合成、九宮格頭部姿勢、六種表情、全身極限姿勢與101格晃動掃描。實際數字見 qa_metrics.json 與 validation.txt。

與參考圖差異：臉底補繪後陰影及下巴線條有些微差異；眼鏡重描；閉眼和說話嘴型為新增動畫原畫。轉頭採近期技能對參考圖模型的 ±15° 設定。頭髮／領結使用播放器的阻尼擺近似；不宣稱完整 Inochi2D 物理引擎。尚未在 Live2D Cubism 或 Inochi Creator 桌面版實際開啟測試。

## Skills 共用

已在 C:/Users/gueiw/.codex/skills/ 下建立 live2d-psd、inochi2d-puppet、anime-girl-face、anime-girl-body 的 Junction，直接指向本專案 .claude/skills/ 同名目錄。原 .agents 副本保留，後續請優先讀取共用入口。
