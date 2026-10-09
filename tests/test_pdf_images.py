# tests/test_pdf_images.py
"""Tests for core.pdf_images.load_pages."""

from __future__ import annotations

import io

import pytest
from PIL import Image

import config
from core import pdf_images


class FakeUpload:
    """Mimics Streamlit's UploadedFile: .name + .read()."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def read(self) -> bytes:
        return self._data


def _png_bytes(size=(100, 60), color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_image_returns_png_bytes():
    upload = FakeUpload("photo.png", _png_bytes(size=(80, 40)))

    pages = pdf_images.load_pages([upload])

    assert isinstance(pages, list)
    assert len(pages) == 1
    assert isinstance(pages[0], bytes)
    # PNG magic number
    assert pages[0].startswith(b"\x89PNG\r\n\x1a\n")

    # Output is a valid, readable RGB PNG.
    with Image.open(io.BytesIO(pages[0])) as img:
        assert img.format == "PNG"
        assert img.mode == "RGB"


def test_jpeg_is_converted_and_resized():
    buf = io.BytesIO()
    Image.new("RGB", (4000, 100), (0, 128, 255)).save(buf, format="JPEG")
    upload = FakeUpload("big.jpg", buf.getvalue())

    pages = pdf_images.load_pages([upload])

    assert len(pages) == 1
    with Image.open(io.BytesIO(pages[0])) as img:
        assert img.format == "PNG"
        assert max(img.size) <= config.MAX_IMAGE_SIDE


def test_empty_file_raises():
    upload = FakeUpload("empty.png", b"")
    with pytest.raises(ValueError, match="empty"):
        pdf_images.load_pages([upload])


def test_unsupported_extension_raises():
    upload = FakeUpload("notes.txt", b"hello world")
    with pytest.raises(ValueError, match="Unsupported file type"):
        pdf_images.load_pages([upload])