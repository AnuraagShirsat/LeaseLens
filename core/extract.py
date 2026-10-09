"""Two-stage lease extraction pipeline using Gemma.

Stage 1 (vision):  each PDF page image → raw transcription (ask_text, no schema).
Stage 2 (structured): concatenated text → clauses + key_terms (ask_json).

Splitting the stages keeps the vision call free of JSON-schema constraints
(which trip a known Ollama bug with Gemma) and keeps the structured call
text-only, which is the most reliable path for complex nested schemas.

We deliberately do NOT ask the model for `full_text` or `page_count` — we
already have both, and asking for them wastes tokens and invites truncation.

Deposit amounts are also detected with a Python regex on the final text so
`key_terms.deposit_mentions` reflects what is actually written, not what the
model thinks it saw.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Callable, Optional, Sequence

from pydantic import BaseModel

from core import gemma
from core.schema import AgreementExtract, Clause, KeyTerms


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

PAGE_TRANSCRIBE_PROMPT = """\
You are transcribing one page of a residential lease agreement.

Transcribe ALL visible text verbatim, preserving:
- headings and numbered clauses
- dates, amounts, and names exactly as written
- section numbering and layout order

Mark non-text content inline:
- stamps / seals as [STAMP: <what it says>]
- handwritten notes as [HANDWRITTEN: <what it says>]
- signatures as [SIGNATURE: <name if readable>]
- images / diagrams as [FIGURE: <brief description>]

Do NOT summarize, interpret, translate, or add commentary.
If a region is unreadable, write [UNREADABLE].

Output only the transcription, nothing else.
"""

STRUCTURED_EXTRACT_PROMPT = """\
You are analyzing a residential lease agreement. Below is the full transcription
of the document. Page breaks are marked with <<<PAGE n>>>.

Produce a structured extraction with these rules:

CLAUSES
- Split the agreement into distinct clauses in reading order.
- Assign clause_id sequentially: "C1", "C2", "C3", ...
- `heading` is the clause heading if present, else null.
- `text` is the clause text verbatim (do not paraphrase).
- `page` is the page number the clause starts on (from <<<PAGE n>>> markers).
- `read_confidence` is "high" if clearly transcribed, "medium" if some
  ambiguity, "low" if mostly unclear.
- `read_note` is a short note when read_confidence is not "high", else null.

KEY_TERMS
- Extract numeric and named terms.
- Use null for any term not clearly stated — do NOT guess.
- monthly_rent, security_deposit, agreement_term_months, lock_in_months,
  notice_period_days, rent_escalation_percent: numbers or null.
- start_date: ISO-ish date string as written, or null.
- landlord_name, tenant_name: strings, or null.
- deposit_mentions: every deposit amount mentioned anywhere in the document.

--- AGREEMENT TEXT ---
{text}
--- END AGREEMENT TEXT ---
"""


class _AgreementCore(BaseModel):
    """What we ask the model for. full_text / page_count are filled in by us."""

    clauses: list[Clause]
    key_terms: KeyTerms


# --------------------------------------------------------------------------- #
# Deposit-amount detection
# --------------------------------------------------------------------------- #

# Matches "Rs. 60,000", "Rs 60000", "INR 60,000", "₹60,000", "Rs.60,000" etc.
_AMOUNT_RE = re.compile(
    r"(?:(?:Rs|INR|₹)\.?\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)


def _parse_amount(raw: str) -> int | float:
    cleaned = raw.replace(",", "").strip()
    return float(cleaned) if "." in cleaned else int(cleaned)


def _find_deposit_mentions(full_text: str) -> list[int | float]:
    """Find rupee amounts on any line that mentions 'deposit'."""
    mentions: list[int | float] = []
    for line in full_text.splitlines():
        if "deposit" not in line.lower():
            continue
        for match in _AMOUNT_RE.finditer(line):
            mentions.append(_parse_amount(match.group(1)))
    return mentions


# --------------------------------------------------------------------------- #
# Stage 1: transcription
# --------------------------------------------------------------------------- #

def transcribe_page(image: bytes, page_number: int) -> str:
    """Transcribe a single page image to text. `page_number` is 1-indexed."""
    prompt = f"Page {page_number}.\n\n{PAGE_TRANSCRIBE_PROMPT}"
    text = gemma.ask_text(prompt, images=[image])
    return text.strip()


def transcribe_pages(images: Sequence[bytes]) -> list[str]:
    """Transcribe each page image in order."""
    return [transcribe_page(img, i + 1) for i, img in enumerate(images)]


# --------------------------------------------------------------------------- #
# Stage 2: structured extraction
# --------------------------------------------------------------------------- #

def _join_pages(page_texts: Sequence[str]) -> str:
    """Join per-page transcriptions with page markers the model can key off."""
    parts = [
        f"<<<PAGE {i + 1}>>>\n{text}"
        for i, text in enumerate(page_texts)
    ]
    return "\n\n".join(parts)


def extract_agreement_from_text(
    full_text: str,
    page_count: int,
) -> AgreementExtract:
    """Turn a full transcription into a validated AgreementExtract."""
    prompt = STRUCTURED_EXTRACT_PROMPT.format(text=full_text)
    core = gemma.ask_json(prompt, _AgreementCore)

    # Override the model's deposit_mentions with regex-derived values so the
    # list reflects what is actually written in the document.
    core.key_terms.deposit_mentions = _find_deposit_mentions(full_text)

    return AgreementExtract(
        clauses=core.clauses,
        key_terms=core.key_terms,
        full_text=full_text,
        page_count=page_count,
    )


def extract_agreement(
    page_images: Sequence[bytes],
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> AgreementExtract:
    """Full pipeline: page images → transcription → structured AgreementExtract.

    `progress_cb`, if given, is called after each page as
    `progress_cb(fraction, message)` with fraction in [0.0, 1.0].
    """
    if not page_images:
        raise gemma.GemmaError(
            "No pages to extract. Provide at least one rendered page image."
        )

    total = len(page_images)
    page_texts: list[str] = []
    for i, img in enumerate(page_images):
        page_texts.append(transcribe_page(img, i + 1))
        if progress_cb is not None:
            progress_cb((i + 1) / total, f"Transcribed page {i + 1}/{total}")

    full_text = _join_pages(page_texts)
    return extract_agreement_from_text(full_text, page_count=total)


# --------------------------------------------------------------------------- #
# Optional: PDF rendering
# --------------------------------------------------------------------------- #

def render_pdf(path: str | Path, dpi: int = 150) -> list[bytes]:
    """Render a PDF to a list of PNG page images.

    Requires `pypdfium2` (pip installable, no external binaries).
    150 DPI is a good default for lease documents — enough to read small print
    and stamps without blowing up token counts.
    """
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError as e:
        raise gemma.GemmaError(
            "PDF rendering requires pypdfium2. "
            "Install it with `pip install pypdfium2`."
        ) from e

    scale = dpi / 72.0  # pypdfium2 renders at 72 DPI by default
    pdf = pdfium.PdfDocument(str(path))
    images: list[bytes] = []
    for page in pdf:
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        images.append(buf.getvalue())
    return images


def extract_agreement_from_pdf(
    path: str | Path,
    dpi: int = 150,
) -> AgreementExtract:
    """Convenience wrapper: PDF path → AgreementExtract."""
    images = render_pdf(path, dpi=dpi)
    return extract_agreement(images)