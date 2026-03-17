"""
Generate the Notion Auto-Meet app icon (icon.ico).
Requires: pip install Pillow
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def create_icon():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded rectangle background (Notion-blue)
        radius = max(size // 5, 2)
        draw.rounded_rectangle(
            [0, 0, size - 1, size - 1],
            radius=radius,
            fill=(80, 170, 230, 255),
        )

        # White "N" letter centered
        font_size = int(size * 0.55)
        font = None
        for font_name in [
            "arialbd.ttf", "arial.ttf", "calibrib.ttf",
            "segoeui.ttf", "verdanab.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except (OSError, IOError):
                continue

        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), "N", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1]
        draw.text((tx, ty), "N", fill=(255, 255, 255, 255), font=font)

        images.append(img)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    # Save with all sizes embedded
    images[-1].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )
    print(f"Icon saved to: {out_path}")


if __name__ == "__main__":
    create_icon()
