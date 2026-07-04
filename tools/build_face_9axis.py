from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "face_9axis_sheet_alpha.png"
OUT = ROOT / "assets" / "face_9axis"
NAMES = [
    ["up_left", "up_center", "up_right"],
    ["center_left", "center", "center_right"],
    ["down_left", "down_center", "down_right"],
]


def main():
    image = Image.open(SOURCE).convert("RGBA")
    if image.width % 3 or image.height % 3:
        raise SystemExit(f"Expected a 3x3 sheet, got {image.size}")
    cell_w, cell_h = image.width // 3, image.height // 3
    OUT.mkdir(parents=True, exist_ok=True)
    for row in range(3):
        for col in range(3):
            # Remove the generated separator line while retaining equal canvas sizes.
            left, top = col * cell_w + 2, row * cell_h + 2
            cell = image.crop((left, top, (col + 1) * cell_w - 2, (row + 1) * cell_h - 2))
            cell.save(OUT / f"{NAMES[row][col]}.png")
    print(f"Wrote nine {cell_w-4}x{cell_h-4} angle cells to {OUT}")


if __name__ == "__main__":
    main()
