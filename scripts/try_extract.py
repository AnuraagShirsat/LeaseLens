"""Manual smoke test: run extract_agreement on one or more page images.

Usage:
    python scripts/try_extract.py path/to/page.jpg
    python scripts/try_extract.py page1.jpg page2.jpg page3.jpg
    python scripts/try_extract.py lease.pdf           # PDF also works

Requires Ollama running with the model from config.MODEL_NAME pulled.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `core` importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.extract import (  # noqa: E402
    extract_agreement,
    render_pdf,
)
from core.gemma import GemmaError  # noqa: E402


def _load_images(paths: list[str]) -> list[bytes]:
    images: list[bytes] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        if path.suffix.lower() == ".pdf":
            images.extend(render_pdf(path))
        else:
            images.append(path.read_bytes())
    return images


def _progress(fraction: float, message: str) -> None:
    bar_len = 30
    filled = int(bar_len * fraction)
    bar = "█" * filled + "·" * (bar_len - filled)
    print(f"\r[{bar}] {fraction * 100:5.1f}%  {message}", end="", flush=True)
    if fraction >= 1.0:
        print()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2

    try:
        images = _load_images(argv[1:])
    except GemmaError as e:
        print(f"Error loading input: {e}")
        return 1

    print(f"Loaded {len(images)} page image(s). Running extraction...\n")

    try:
        result = extract_agreement(images, progress_cb=_progress)
    except GemmaError as e:
        print(f"\nGemmaError: {e}")
        return 1

    print("\n" + "=" * 70)
    print(f"PAGES: {result.page_count}    CLAUSES: {len(result.clauses)}")
    print("=" * 70)

    for clause in result.clauses:
        head = clause.heading or "(no heading)"
        conf = clause.read_confidence
        flag = "" if conf == "high" else f"  [{conf}]"
        print(f"\n{clause.clause_id}  p.{clause.page}  {head}{flag}")
        if clause.read_note:
            print(f"   note: {clause.read_note}")
        # Indent clause text for readability
        for line in clause.text.splitlines() or [""]:
            print(f"   {line}")

    kt = result.key_terms
    print("\n" + "-" * 70)
    print("KEY TERMS")
    print("-" * 70)
    for field in (
        "monthly_rent",
        "security_deposit",
        "agreement_term_months",
        "lock_in_months",
        "notice_period_days",
        "rent_escalation_percent",
        "start_date",
        "landlord_name",
        "tenant_name",
    ):
        print(f"  {field:26} {getattr(kt, field)}")
    print(f"  {'deposit_mentions':26} {kt.deposit_mentions}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))