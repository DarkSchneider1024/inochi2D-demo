# Carrot Inochi2D Demo

Carrot VTuber 的臉部角度展示與原生 Inochi2D 模型。

- `preview/`：免建置 HTML 九方向視覺比較。
- `models/carrot_vtuber_detailed_head.inx`：原生 Inochi2D 頭部模型。
- `assets/native_head_layers/`：獨立臉部透明圖層。
- `tools/build_detailed_native_head.py`：建立 9×9 ArtMesh 與 Angle X/Y 九點 deformation binding。

HTML 九方向圖只供瀏覽器比較；真正的 ArtMesh 與連續參數內插位於 `.inx`，請使用 Inochi Creator 開啟。

本機執行 `python -m http.server 8000`，再開啟 `http://localhost:8000/`。
