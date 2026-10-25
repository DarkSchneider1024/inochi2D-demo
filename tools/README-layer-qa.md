# 圖層檢查資料匯出

安裝 Python 依賴：`pip install numpy opencv-python pillow`。
在網站儲存庫執行：

```sh
python tools/export_layer_qa.py --all
```

掃描 `models/*.inp`，涵蓋正面、側面、舊版本與不同造型，角色名稱優先讀取 `models.json`。
重新匯出單一角色：`python tools/export_layer_qa.py mr_carrot_v3`，保留其他角色的清單。
`--all --missing` 只補缺少 index.json 的角色；模型有更新時請使用完整匯出。

產物為 `layers/<角色 id>/` 下的逐層 WebP、合成圖與疑點資料，以及 `layers/models.json`。
疑點是候選標記，仍需人工確認。匯出採用現有模型的靜止位置，並非動態姿勢模擬。

圖層頁支援搜尋角色、全選目前清單、全取消所有圖層、還原預設，以及框選／畫筆標記。
標記會跟著角色縮放／平移，切換角色暫存於本次頁面工作階段，重新整理後不保留。
「儲存畫面 PNG」輸出目前畫布的可視範圍，包含顯示中的圖層、疑點框與手動標記；不包含旁邊的操作介面。

專屬區的 6 個角色沿用 secret.html 的工作階段密碼驗證，解鎖後回到此頁即可使用。

角色分類：故事角色 34 個（含側面／坐姿）、精緻角色 11 個、卡洛特實驗室 4 個、專屬區 6 個。分類儲存在 `layers/models.json` 的 `category` 欄位；單角重建保留既有分類，新角色由 `category_of` 給預設分類。
