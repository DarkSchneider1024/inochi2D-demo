# -*- coding: utf-8 -*-
"""一鍵將「卡洛兒姐姐 (aka_carol)」、「Aka×Gemini 巫女 (aka_gemini)」與「90° 九軸素體 (head90.html)」推送至 GitHub Pages (origin/main)。

執行方式（在終端機 / PowerShell 貼上即可）：
  cd "G:\我的雲端硬碟\carrot-entertainment\inochi2D-demo"
  python publish_head90.py --push
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def find_repo() -> Path:
    candidates = [
        Path(__file__).resolve().parent,
        Path.cwd(),
        Path(r"G:\我的雲端硬碟\carrot-entertainment\inochi2D-demo"),
        Path(r"H:\我的雲端硬碟\carrot-entertainment\inochi2D-demo"),
        Path(r"D:\Google Drive\carrot-entertainment\inochi2D-demo"),
        Path.home() / "Google Drive" / "carrot-entertainment" / "inochi2D-demo",
    ]
    for c in candidates:
        if (c / ".git").exists() and (c / "official.html").exists():
            return c
    raise FileNotFoundError(
        "找不到 inochi2D-demo Git 資料夾，請先 cd 到 inochi2D-demo 目錄後再執行此腳本。"
    )


FILES = [
    # 頁面與導覽列
    "head90.html",
    "official.html",
    "index.html",
    "gallery.html",
    "layers.html",
    "model3d.html",
    "secret.html",
    # 模型清單與版本表
    "models.json",
    "models/versions.json",
    "layers/models.json",
    # 1. 卡洛兒姐姐（Aka 九軸 × Gemini 純白底拆件換裝版）
    "models/aka_carol.inp",
    "models/aka_carol.inx",
    "thumbs/aka_carol.png",
    "downloads/aka_carol_psd_and_inp_pack.zip",
    # 2. 銀紫狐耳巫女（Aka 九軸 × Gemini 純白底拆件換裝版）
    "models/aka_gemini.inp",
    "models/aka_gemini.inx",
    "thumbs/aka_gemini.png",
    "downloads/aka_gemini_psd_and_inp_pack.zip",
    # 3. 90° 九軸可編輯素體與 Live2D 工程檔
    "models/base_head_90deg_9axis.inp",
    "models/base_head_90deg_9axis.inx",
    "thumbs/base_head_90deg_9axis.png",
    "downloads/kei_90deg_9axis_editable.cmo3",
    "downloads/blender_head9_90deg.json",
    "downloads/cmo3_kei_head9_90deg.json",
    "downloads/head90_9axis_pack.zip",
    # 發佈腳本本身
    "publish_head90.py",
]


def git(repo: Path, *args: str, env=None) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, env=env
    ).decode("utf-8", errors="replace").strip()


def main():
    repo = find_repo()
    print(f"[1/5] 找到儲存庫：{repo}")
    git(repo, "fetch", "origin")
    parent = git(repo, "rev-parse", "origin/main")
    print(f"[2/5] 遠端基準 origin/main = {parent}")

    # 使用系統暫存區建立 Git Index，避免 Google 雲端硬碟同步鎖定 .git 目錄
    idx_file = Path(tempfile.gettempdir()) / "inochi2d_demo_publish.index"
    if idx_file.exists():
        idx_file.unlink()
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = str(idx_file)

    try:
        git(repo, "read-tree", parent, env=env)
        all_files = list(FILES)
        layer_dir = repo / "layers" / "base_head_90deg_9axis"
        if layer_dir.is_dir():
            all_files += [
                p.relative_to(repo).as_posix()
                for p in sorted(layer_dir.iterdir())
                if p.is_file()
            ]

        existing = [f for f in all_files if (repo / f).is_file()]
        missing = [f for f in all_files if not (repo / f).is_file()]
        print(f"[3/5] 準備加入 {len(existing)} 個檔案（略過未同步檔案 {len(missing)} 個）")
        if missing:
            print("      尚未同步完成的檔案：", ", ".join(missing))

        git(repo, "add", "-f", "--", *existing, env=env)
        tree = git(repo, "write-tree", env=env)
        if tree == git(repo, "rev-parse", f"{parent}^{{tree}}"):
            print("遠端 origin/main 已是最新內容，無需重複推送。")
            return

        msg = (
            "feat(demo): 新增卡洛兒姐姐(aka_carol)、Aka×Gemini巫女(aka_gemini)至精緻展示作品與 90° 九軸素體頁籤"
        )
        commit = git(repo, "commit-tree", tree, "-p", parent, "-m", msg, env=env)
        print(git(repo, "diff", "--stat", parent, commit))
        print(f"[4/5] 建立 Commit：{commit}")

        print("[5/5] 正在推送至 GitHub (origin/main)...")
        print(git(repo, "push", "origin", f"{commit}:refs/heads/main"))
        git(repo, "fetch", "origin")
        git(repo, "update-ref", "refs/heads/main", commit)
        print("\n✅ 推送完成！請約等 30~60 秒讓 GitHub Pages 部署更新：")
        print("   👉 精緻展示作品（預設載入卡洛兒姐姐）：https://darkschneider1024.github.io/inochi2D-demo/official.html?model=aka_carol")
        print("   👉 銀紫狐耳巫女（Aka×Gemini）：https://darkschneider1024.github.io/inochi2D-demo/official.html?model=aka_gemini")
        print("   👉 90° 九軸可編輯素體頁籤：https://darkschneider1024.github.io/inochi2D-demo/head90.html")
        print("   👉 作品集總覽：https://darkschneider1024.github.io/inochi2D-demo/gallery.html")
    finally:
        if idx_file.exists():
            idx_file.unlink()


if __name__ == "__main__":
    main()
