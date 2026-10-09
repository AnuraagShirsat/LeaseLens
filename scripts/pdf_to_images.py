"""
scripts/pdf_to_images.py

Turns every page of a PDF into a PNG picture: page1.png, page2.png, ...

How to run (from the project folder, with (.venv) showing):
    python scripts/pdf_to_images.py eval\\cases\\case1\\case1.pdf eval\\cases\\case1
"""

import sys
from pathlib import Path

# pymupdf is imported under the name "fitz"
try:
    import fitz
except ImportError:
    print("PROBLEM: pymupdf is not installed.")
    print("Make sure (.venv) shows in the terminal, then run: pip install -r requirements.txt")
    sys.exit(1)


def main():
    # We need exactly two things: the PDF path and the output folder.
    if len(sys.argv) != 3:
        print("Usage: python scripts/pdf_to_images.py <pdf file> <output folder>")
        return 1

    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])

    if not pdf_path.exists():
        print("PROBLEM: I cannot find the PDF: " + str(pdf_path))
        return 1

    # Make the output folder if it does not exist yet.
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as error:
        print("PROBLEM: I could not open that PDF: " + str(error))
        return 1

    # A zoom of 2 gives a sharp, readable picture (about 144 dots per inch).
    zoom = fitz.Matrix(2, 2)

    count = 0
    for page_number, page in enumerate(doc, start=1):
        picture = page.get_pixmap(matrix=zoom)
        picture.save(str(out_dir / ("page" + str(page_number) + ".png")))
        count += 1

    print("Saved " + str(count) + " page image(s) into " + str(out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
