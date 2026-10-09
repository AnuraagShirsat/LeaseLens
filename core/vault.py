# core/vault.py
# Move-in Evidence Vault: a checklist, notes and photos saved ONLY on
# this computer, plus a PDF "Move-in Condition Report".
# No AI and no network are used here.

import json
import re
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageOps

import config

# Photos are shrunk so that their longest side is at most this many pixels.
MAX_PHOTO_SIDE = 1600

# A session id may only use letters, digits, minus and underscore.
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")

# Extra checklist items that depend on the agreement.
AGREEMENT_AREA = "From this agreement"
ITEM_WALLS = (
    "Photograph every wall surface and ceiling in each room "
    "before moving in"
)
ITEM_INVENTORY = (
    "Make a written inventory and ask the landlord to sign and date it"
)
ITEM_DEPOSIT_RECEIPT = (
    "Record the date and mode of deposit payment and keep the receipt"
)
ITEM_LOCK_IN = "Note the lock-in end date in your calendar"

# Friendly names for the agreed terms shown in the report.
TERM_LABELS = {
    "monthly_rent": "Monthly rent",
    "security_deposit": "Security deposit",
    "maintenance_responsibility": "Who pays maintenance and repairs",
    "keys_handed_over": "Keys handed over",
    "electricity_meter": "Electricity meter reading",
    "water_meter": "Water meter reading",
}


# ---------------------------------------------------------------
# Checklists
# ---------------------------------------------------------------
def base_checklist():
    """The standard move-in checklist: a list of {"area", "item"}."""
    rows = [
        ("Walls and paint",
         "Photograph each wall and note any marks, cracks or damp patches"),
        ("Ceiling",
         "Photograph the ceiling in each room and note any stains"),
        ("Flooring",
         "Photograph the floor in each room and note any chips or cracks"),
        ("Windows and grills",
         "Check that windows open and close and photograph any damage"),
        ("Doors and locks",
         "Check every door and lock and photograph any damage"),
        ("Bathroom fittings",
         "Test taps, flush and drains and photograph any leaks or stains"),
        ("Kitchen fittings and sink",
         "Test the sink and taps and photograph the counter and cupboards"),
        ("Electrical points and switches",
         "Check that switches and sockets work and note any that do not"),
        ("Fans and lights",
         "Check every fan and light and note any that do not work"),
        ("Appliances",
         "List each appliance you were given and photograph its condition"),
        ("Furniture",
         "List each piece of furniture and photograph its condition"),
        ("Balcony",
         "Photograph the balcony floor, railings and any drainage"),
        ("Keys handed over (count)",
         "Write down how many keys of each kind you received"),
        ("Electricity meter reading",
         "Photograph the meter and write down the reading and the date"),
        ("Water meter reading",
         "Photograph the meter and write down the reading and the date"),
        ("Gas connection",
         "Note if there is a gas connection and photograph the stove "
         "and the cylinder or meter"),
    ]
    return [{"area": area, "item": item} for area, item in rows]


def agreement_checklist(bundle):
    """Extra checklist items made from this agreement's results.

    Plain Python rules only (no AI). Returns a list of {"area", "item"}.
    """
    extra = []
    topics = {finding.topic for finding in bundle.findings}

    if topics & {"deductions", "maintenance_repairs"}:
        extra.append(ITEM_WALLS)

    gap_text = " ".join(
        gap.title + " " + gap.description for gap in bundle.gaps
    ).lower()
    if "inventory" in gap_text:
        extra.append(ITEM_INVENTORY)

    if "deposit" in topics:
        extra.append(ITEM_DEPOSIT_RECEIPT)

    if "lock_in" in topics:
        extra.append(ITEM_LOCK_IN)

    return [{"area": AGREEMENT_AREA, "item": text} for text in extra]


# ---------------------------------------------------------------
# Saving and reading entries (everything stays on this computer)
# ---------------------------------------------------------------
def _session_dir(session_id):
    """The folder for one session. Rejects unsafe session ids."""
    if not isinstance(session_id, str):
        raise ValueError("The session id must be text.")
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(
            "The session id may only use letters, numbers, - and _."
        )
    return Path(config.VAULT_DIR) / session_id


def _prepare_photo(photo_bytes):
    """Straighten, shrink and convert a photo to JPEG bytes."""
    try:
        image = Image.open(BytesIO(photo_bytes))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except Exception:
        raise ValueError(
            "That photo could not be read. Please try a different picture."
        )
    image.thumbnail((MAX_PHOTO_SIDE, MAX_PHOTO_SIDE))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def save_entry(session_id, area, item, note, photo_bytes=None):
    """Save one note (and an optional photo) with the date and time.

    Returns the saved entry as a dictionary.
    """
    folder = _session_dir(session_id)

    # Check the photo first, so a bad photo leaves nothing half-saved.
    photo_data = None
    if photo_bytes:
        photo_data = _prepare_photo(photo_bytes)

    folder.mkdir(parents=True, exist_ok=True)

    # Make a unique id from the current time.
    now = datetime.now()
    base_id = now.strftime("%Y%m%d_%H%M%S_%f")
    entry_id = base_id
    counter = 1
    while (folder / ("entry_" + entry_id + ".json")).exists():
        counter += 1
        entry_id = base_id + "_" + format(counter, "02d")

    photo_file = None
    if photo_data is not None:
        photo_file = "entry_" + entry_id + ".jpg"
        (folder / photo_file).write_bytes(photo_data)

    entry = {
        "entry_id": entry_id,
        "saved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "area": area,
        "item": item,
        "note": note or "",
        "photo_file": photo_file,
    }
    json_path = folder / ("entry_" + entry_id + ".json")
    json_path.write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return entry


def list_entries(session_id):
    """All saved entries for a session, oldest first."""
    folder = _session_dir(session_id)
    if not folder.exists():
        return []

    entries = []
    for json_path in sorted(folder.glob("entry_*.json")):
        try:
            entry = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue  # skip a damaged file instead of crashing
        photo_path = None
        if entry.get("photo_file"):
            candidate = folder / entry["photo_file"]
            if candidate.exists():
                photo_path = str(candidate)
        entry["photo_path"] = photo_path
        entries.append(entry)
    return entries


def delete_all(session_id):
    """Delete everything saved for this session.

    Returns True if something was deleted, False if there was nothing.
    """
    folder = _session_dir(session_id)
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True


# ---------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------
def _latin(text):
    """Make text safe for the PDF's built-in font (Latin letters only)."""
    text = str(text).replace("\u20b9", "Rs. ")
    return text.encode("latin-1", "replace").decode("latin-1")


def _term_text(key, value):
    """Turn an agreed term into the text shown in the report."""
    if value is None or value == "":
        return "Not recorded"
    if key in ("monthly_rent", "security_deposit"):
        if isinstance(value, (int, float)):
            return "Rs. " + format(value, ",.0f")
    return str(value)


def _write_text(pdf, text, size=11, bold=False):
    """Write one block of text on its own line(s)."""
    style = "B" if bold else ""
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(0, 6, _latin(text), new_x="LMARGIN", new_y="NEXT")


def _add_photo(pdf, photo_path):
    """Put a photo in the PDF, scaled to fit."""
    try:
        with Image.open(photo_path) as image:
            width_px, height_px = image.size
    except Exception:
        return
    max_width = min(pdf.epw, 100.0)
    max_height = 80.0
    scale = min(max_width / width_px, max_height / height_px)
    width = width_px * scale
    height = height_px * scale
    if pdf.get_y() + height > pdf.page_break_trigger:
        pdf.add_page()
    pdf.image(str(photo_path), x=pdf.l_margin, y=pdf.get_y(),
              w=width, h=height)
    pdf.set_y(pdf.get_y() + height + 3)


def export_report(session_id, agreed_terms):
    """Make the Move-in Condition Report and return it as PDF bytes."""
    entries = list_entries(session_id)
    terms = agreed_terms or {}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _write_text(pdf, "Move-in Condition Report", size=18, bold=True)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    _write_text(pdf, "Generated on: " + generated)
    pdf.ln(3)

    _write_text(pdf, "Agreed details", size=13, bold=True)
    for key, label in TERM_LABELS.items():
        _write_text(pdf, label + ": " + _term_text(key, terms.get(key)))
    for key, value in terms.items():
        if key not in TERM_LABELS:
            _write_text(pdf, str(key) + ": " + _term_text(key, value))
    pdf.ln(3)

    _write_text(pdf, "Recorded condition", size=13, bold=True)
    if not entries:
        _write_text(pdf, "No entries have been recorded yet.")

    for entry in entries:
        pdf.ln(2)
        heading = entry.get("saved_at", "") + " - " + entry.get("area", "")
        _write_text(pdf, heading, bold=True)
        _write_text(pdf, "Item: " + entry.get("item", ""))
        if entry.get("note"):
            _write_text(pdf, "Note: " + entry["note"])
        if entry.get("photo_path"):
            _add_photo(pdf, entry["photo_path"])
        else:
            _write_text(pdf, "(no photo)", size=9)

    pdf.ln(4)
    _write_text(
        pdf,
        "This report is a personal record kept by the tenant. "
        "It is not legal advice.",
        size=9,
    )
    return bytes(pdf.output())