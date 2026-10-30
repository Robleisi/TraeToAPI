"""生成 assets/traetoapi.ico（TraeToAPI 托盘/应用图标）。

设计对应 docs/logo.svg：紫色渐变圆角方块 + 两行白色 "Trae / ToAPI"。
仅在图标源文件变更时运行：python scripts/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "traetoapi.ico"
SIZE = 256
TOP = (0x6A, 0x5C, 0xFF)
BOTTOM = (0x2F, 0x2A, 0x6B)


def _font(size: int):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # 垂直渐变 + 圆角蒙版
    gradient = Image.new("RGBA", (SIZE, SIZE))
    gd = ImageDraw.Draw(gradient)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)) + (255,)
        gd.line([(0, y), (SIZE, y)], fill=color)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=52, fill=255)
    img.paste(gradient, (0, 0), mask)
    # 两行主文字：Trae / ToAPI（小尺寸下仍可辨认）
    draw = ImageDraw.Draw(img)
    font = _font(72)
    for i, text in enumerate(("Trae", "ToAPI")):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        draw.text(((SIZE - (right - left)) / 2 - left, 52 + i * 84 - top),
                  text, font=font, fill=(255, 255, 255, 255))
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = build()
    img.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    main()
