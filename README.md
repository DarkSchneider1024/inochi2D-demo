# Lily Inochi2D Demo

Lily VTuber v1 全身分層模型展示。素材由「同比例炸開圖」pipeline 產出:
agy(Nano Banana)生成炸開圖 → Python manifest 切圖(flood 去背,格狀多點種子)→ layout 對齊 → pytoshop 組 PSD。

- `preview/`:分層動態預覽(滑鼠視差、呼吸、自動眨眼)
- `assets/lily_v1/layers/`:26 張全畫布圖層 PNG(由後到前)
- `assets/lily_v1/extras/`:眨眼用閉眼圖層
- `models/lily_v1.psd`:rig-ready 26 層 PSD,可匯入 Inochi Creator / Live2D

本機預覽:`python -m http.server 8000`,開啟 `http://localhost:8000/`。

線上版:https://darkschneider1024.github.io/inochi2D-demo/preview/
