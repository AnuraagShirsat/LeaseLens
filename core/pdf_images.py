# core/pdf_images.py
"""Convert uploaded PDFs and images into per-page PNG bytes."""

from __future__ import annotations

import io
import os
from typing import Iterable, List, Protocol

import pymupdf as fitz # PyMuPDF
from PIL import Image, ImageOps

import config

PDF_DPI = 150
MAX_PDF_PAGES = 12
SUPPORTED_IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
}


class UploadedFile(Protocol):
    """Minimal interface matching Streamlit's UploadedFile."""

    name: str

    def read(self) -> bytes:  # pragma: no cover - protocol
        ...


def _resize_to_limit(img: Image.Image) -> Image.Image:
    """Downscale so the longest side is at most config.MAX_IMAGE_SIDE."""
    longest = max(img.size)
    limit = int(config.MAX_IMAGE_SIDE)
    if longest > limit > 0:
        scale = limit / float(longest)
        new_size = (
            max(1, round(img.width * scale)),
            max(1, round(img.height * scale)),
        )
        img = img.resize(new_size, Image.LANCZOS)
    return img


def _to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_pdf(data: bytes) -> List[bytes]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read PDF file: file appears corrupted.") from exc

    pages: List[bytes] = []
    try:
        for page in doc:
            if len(pages) >= MAX_PDF_PAGES:
                break
            pix = page.get_pixmap(dpi=PDF_DPI)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img = _resize_to_limit(img)
            pages.append(_to_png_bytes(img))
    finally:
        doc.close()

    if not pages:
        raise ValueError("PDF contains no pages.")
    return pages


def _load_image(data: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = ImageOps.exif_transpose(img)  # apply EXIF rotation
        img = img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read image file: file appears corrupted.") from exc

    img = _resize_to_limit(img)
    return _to_png_bytes(img)


def load_pages(files: Iterable[UploadedFile]) -> List[bytes]:
    """Convert uploaded files into a list of PNG-encoded page bytes.

    PDFs are rendered at 150 DPI (up to MAX_PDF_PAGES pages). Images are
    EXIF-rotated, converted to RGB and downscaled so the longest side is at
    most ``config.MAX_IMAGE_SIDE`` pixels.
    """
    pages: List[bytes] = []

    for f in files:
        name = getattr(f, "name", "") or "<unnamed>"
        ext = os.path.splitext(name.lower())[1]

        try:
            data = f.read()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not read file '{name}'.") from exc

        if not data:
            raise ValueError(f"File '{name}' is empty.")

        if ext == ".pdf":
            pages.extend(_render_pdf(data))
        elif ext in SUPPORTED_IMAGE_EXTS:
            pages.append(_load_image(data))
        else:
            supported = ", ".join(sorted({".pdf", *SUPPORTED_IMAGE_EXTS}))
            raise ValueError(
                f"Unsupported file type '{ext or name}'. Supported types: {supported}."
            )

    if not pages:
        raise ValueError("No files provided.")

    return pages