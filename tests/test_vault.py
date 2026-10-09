# tests/test_vault.py
# Checks for the Move-in Evidence Vault. Everything is saved into a
# temporary folder, so your real vault_data folder is never touched.

from io import BytesIO

import fitz  # pymupdf, used here to read the PDF text back
import pytest
from PIL import Image

import config
from core import vault
from core.sample_data import get_sample_bundle


@pytest.fixture(autouse=True)
def temp_vault(tmp_path, monkeypatch):
    """Point the vault at a temporary folder for every test."""
    monkeypatch.setattr(config, "VAULT_DIR", str(tmp_path))


def make_photo_bytes(colour="red"):
    """A tiny fake photo (PNG bytes)."""
    image = Image.new("RGB", (60, 40), colour)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_base_checklist_has_16_items():
    items = vault.base_checklist()
    assert len(items) == 16
    for entry in items:
        assert entry["area"]
        assert entry["item"]


def test_agreement_checklist_from_sample_bundle():
    bundle = get_sample_bundle()
    texts = [entry["item"] for entry in vault.agreement_checklist(bundle)]
    assert vault.ITEM_WALLS in texts
    assert vault.ITEM_INVENTORY in texts
    assert vault.ITEM_DEPOSIT_RECEIPT in texts
    assert vault.ITEM_LOCK_IN in texts


def test_agreement_checklist_empty_when_nothing_found():
    bundle = get_sample_bundle().model_copy(
        update={"findings": [], "gaps": []}
    )
    assert vault.agreement_checklist(bundle) == []


def test_save_and_list_entry_without_photo():
    vault.save_entry("s1", "Walls and paint", "Check walls", "Small crack")
    entries = vault.list_entries("s1")
    assert len(entries) == 1
    assert entries[0]["area"] == "Walls and paint"
    assert entries[0]["note"] == "Small crack"
    assert entries[0]["photo_path"] is None


def test_save_entry_with_photo():
    vault.save_entry("s1", "Ceiling", "Check ceiling", "Stain",
                     photo_bytes=make_photo_bytes())
    entries = vault.list_entries("s1")
    assert entries[0]["photo_path"].endswith(".jpg")


def test_entries_are_listed_in_saved_order():
    vault.save_entry("s1", "Area A", "Item A", "first")
    vault.save_entry("s1", "Area B", "Item B", "second")
    vault.save_entry("s1", "Area C", "Item C", "third")
    notes = [entry["note"] for entry in vault.list_entries("s1")]
    assert notes == ["first", "second", "third"]


def test_unreadable_photo_is_rejected():
    with pytest.raises(ValueError):
        vault.save_entry("s1", "Ceiling", "Check", "x",
                         photo_bytes=b"this is not a picture")
    assert vault.list_entries("s1") == []


def test_bad_session_ids_are_rejected():
    for bad in ["../evil", "", "a/b", "a b"]:
        with pytest.raises(ValueError):
            vault.save_entry(bad, "Area", "Item", "note")


def test_delete_all_removes_only_that_session():
    vault.save_entry("s1", "Area", "Item", "one")
    vault.save_entry("s2", "Area", "Item", "two")
    assert vault.delete_all("s1") is True
    assert vault.list_entries("s1") == []
    assert len(vault.list_entries("s2")) == 1
    assert vault.delete_all("s1") is False


def test_export_report_makes_a_pdf():
    vault.save_entry("s1", "Walls and paint", "Check walls",
                     "Small crack near window",
                     photo_bytes=make_photo_bytes())
    terms = {
        "monthly_rent": 25000,
        "security_deposit": 150000,
        "maintenance_responsibility": "Tenant pays minor repairs",
    }
    pdf_bytes = vault.export_report("s1", terms)
    assert pdf_bytes.startswith(b"%PDF")

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in document)
    assert "Move-in Condition Report" in text
    assert "25,000" in text
    assert "Small crack near window" in text
    assert len(document[0].get_images()) >= 1


def test_export_report_with_no_entries():
    pdf_bytes = vault.export_report("empty-session", {})
    assert pdf_bytes.startswith(b"%PDF")


def test_export_report_handles_non_latin_text():
    vault.save_entry("s1", "Walls", "Check", "Price \u20b9500 and \u0c95\u0ca8\u0ccd\u0ca8\u0ca1")
    pdf_bytes = vault.export_report("s1", {"monthly_rent": "\u20b925000"})
    assert pdf_bytes.startswith(b"%PDF")