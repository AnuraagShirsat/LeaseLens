"""
scripts/tilt_image.py

Makes clean page images look like a slightly tilted, imperfect phone photo.
It rotates each image a few degrees, puts it on a grey "table" background,
makes it a little darker and slightly soft, and saves it as page1.jpg, page2.jpg, ...

How to run (from the project folder, with (.venv) showing):
    python scripts/tilt_image.py scripts\\temp_case3 eval\\cases\\case3
"""

import sys
from pathlib import Path

# Pillow is imported under the name "PIL"
try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    print("PROBLEM: Pillow is not installed.")
    print("Make sure (.venv) shows in the terminal, then run: pip install -r requirements.txt")
    sys.exit(1)

TILT_DEGREES = 4          # how much to rotate (positive = anticlockwise)
BRIGHTNESS = 0.85         # 1.0 = unchanged, lower = darker
BLUR_RADIUS = 0.8         # a tiny softness, like a phone photo that is not perfectly sharp
TABLE_COLOUR = (95, 95, 95)  # grey background that shows in the corners after rotating
MAX_SIDE = 1600           # keep images a sensible size (same idea as MAX_IMAGE_SIDE in config.py)


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/tilt_image.py <folder with page images> <output folder>")
        return 1

    in_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])

    if not in_dir.exists():
        print("PROBLEM: I cannot find the folder: " + str(in_dir))
        return 1

    # Find the page images in file-name order (page1.png, page2.png, ...).
    # Sorting by length first keeps page2 before page10.
    pictures = sorted(in_dir.glob("*.png"), key=lambda p: (len(p.name), p.name))
    if not pictures:
        print("PROBLEM: no .png images found in " + str(in_dir))
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for number, path in enumerate(pictures, start=1):
        image = Image.open(path).convert("RGB")

        # 1. Rotate, make the canvas bigger so nothing is cut off, fill corners grey.
        image = image.rotate(TILT_DEGREES, expand=True, fillcolor=TABLE_COLOUR)

        # 2. Slightly darker and slightly soft.
        image = ImageEnhance.Brightness(image).enhance(BRIGHTNESS)
        image = image.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))

        # 3. Shrink if it is very large.
        image.thumbnail((MAX_SIDE, MAX_SIDE))

        # 4. Save as a JPG, like a phone photo.
        image.save(out_dir / ("page" + str(number) + ".jpg"), quality=80)
        count += 1

    print("Saved " + str(count) + " tilted photo-style image(s) into " + str(out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
