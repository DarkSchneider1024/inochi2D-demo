# 🥕 Q版卡洛特先生 (Mr. Carrot Chibi) - Spine 2D 骨骼動畫專案

本專案將卡洛特同樂會的看板角色「Q版卡洛特先生」以正統 **Spine 2D (4.1.24)** 骨骼動畫架構進行高精度綁定與動作設計。

---

## 📂 檔案目錄結構

- **`index.html`**：網頁即時互動展示器（內建官方 Spine Web Player，支援滑鼠拖曳、縮放、骨架線檢視、動畫切換）。
- **`start_preview.bat`**：一鍵啟動本地 Web 伺服器並自動開啟瀏覽器。
- **`mr_carrot_chibi.json`**：Spine 標準骨骼、插槽、附件、皮膚與關鍵影格動畫數據檔。
- **`mr_carrot_chibi.atlas`**：LibGDX / Spine 標準圖集映射描述檔。
- **`mr_carrot_chibi.png`**：2048×2048 高解析度打包 Spritesheet 圖集。
- **`images/`**：33 個獨立切件的原始透明 PNG 圖檔（供 Spine Editor 散圖匯入使用）。
- **`spine-player.js` / `spine-player.css`**：官方 Spine 運行時離線檔案。

---

## 🦴 骨骼架構特點

1. **正統階層骨骼（32 根骨骼）**：
   - 核心軸：`root` → `hip`（骨盆） → `torso`（軀幹背心） → `neck` → `head`（頭部）。
   - 面部與頭部：`hair_back`（後髮）、`face`、`hair_side_r/l`（側髮）、`hair_bangs`（瀏海）、`hair_ahoge`（呆毛頂端子骨骼）。
   - 五官：`eye_r/l`（眼白、瞳孔、睫毛、閉眼笑線）、`eyebrow_r/l`、`glasses`（眼鏡與反光）、`mouth`、`blush_r/l`。
   - 右臂：`arm_r` → `forearm_r`（支援彎曲與大角度舉手揮手）。
   - 左臂與道具：`arm_l` → `prop_carrot`（胡蘿蔔主骨骼） → `hand_l`（左手掌緊扣胡蘿蔔）。
   - 下肢：`leg_r/l` → `foot_r/l`（工裝褲與短靴分層）。

2. **33 圖層插槽與差分切換（Slots & Attachments）**：
   - 眼睛插槽具備 **「睜眼圓瞳孔 ⇄ 閉眼瞇瞇笑線」** 差分替換，動畫時無縫切換，不會產生網格撕裂。
   - 所有圖層完全還原原始 1600×1600 畫布中的原畫座標，裝配姿態 100% 像素級對齊。

---

## 🎬 內建動畫列表

| 動畫名稱 | 描述 | 動態亮點 |
| :--- | :--- | :--- |
| **`idle`** | 待機呼吸 (2.4s 循環) | 軀幹起伏、頭部微點、綠色呆毛慣性延遲飄動、大胡蘿蔔微動、定時眨眼差分切換。 |
| **`wave`** | 活力揮手打招呼 (2.0s 循環) | 右臂高舉左右揮手、頭部微歪、雙眼切換為笑瞇瞇閉眼笑線、呆毛歡樂晃動。 |
| **`jump`** | 開心彈跳 (1.5s 循環) | 短腿屈膝下蹲蓄力（Squash）→ 向上騰空躍起（Stretch）→ 落地慣性擠壓回彈。 |
| **`walk`** | 探險小碎步 (1.0s 循環) | Q 版短腿左右交替邁步、骨盆左右重心晃動、右手配合擺臂、胡蘿蔔隨步伐輕快起伏。 |

---

## 💻 如何使用與預覽

### 1. 瀏覽器直接預覽
- **方式一（最快）**：直接雙擊點開 `index.html`（已內建 Blob / Base64 機制，受現代瀏覽器本機安全性保護亦可免伺服器直接觀看）。
- **方式二（本地伺服器）**：雙擊執行 `start_preview.bat`，將自動啟動 Python 本地伺服器並在瀏覽器中打開 `http://localhost:8080/index.html`。

### 2. 導入 Spine Editor 官方編輯器
1. 打開 Spine 軟體。
2. 點擊左上角菜單 `Spine` → `Import Data...`。
3. 選擇本目錄下的 `mr_carrot_chibi.json`。
4. Images 路徑指向本目錄下的 `images/` 資料夾。
5. 即可完整載入所有骨骼、圖層與 4 套動畫，自由進行二次編輯！

### 3. 導入 Unity (Spine-Unity Runtime)
1. 在 Unity 專案中安裝官方 Spine-Unity 插件（相容 Spine 4.1/4.2）。
2. 將 `mr_carrot_chibi.json`、`mr_carrot_chibi.atlas`、`mr_carrot_chibi.png` 三個檔案直接拖入 Unity 的 Assets 資料夾。
3. Unity 會自動生成 `SkeletonDataAsset`，即可掛載於 GameObject 或 UI Canvas 上播放！
