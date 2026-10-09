"""Tests for core.extract — all LLM calls mocked."""

from unittest.mock import patch

import pytest

from core import extract, gemma
from core.schema import AgreementExtract


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

def _clause_payload(cid: str, page: int = 1, heading: str | None = None):
    return {
        "clause_id": cid,
        "heading": heading,
        "text": f"Text of clause {cid}.",
        "page": page,
        "read_confidence": "high",
        "read_note": None,
    }


def _core_payload(clauses, key_terms=None):
    return {
        "clauses": clauses,
        "key_terms": key_terms or {
            "monthly_rent": 50000,
            "security_deposit": 100000,
            "agreement_term_months": 11,
            "lock_in_months": 6,
            "notice_period_days": 60,
            "rent_escalation_percent": 5,
            "start_date": "2024-06-01",
            "landlord_name": "Alice",
            "tenant_name": "Bob",
            "deposit_mentions": [100000],
        },
    }


PNG = b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# Stage 1: transcription
# --------------------------------------------------------------------------- #

def test_transcribe_page_calls_ask_text_with_image():
    with patch("core.extract.gemma.ask_text", return_value="  page text  ") as at:
        out = extract.transcribe_page(PNG, page_number=3)

    assert out == "page text"  # stripped
    args, kwargs = at.call_args
    prompt = args[0]
    assert "Page 3" in prompt
    assert "Transcribe" in prompt
    assert kwargs["images"] == [PNG]


def test_transcribe_pages_numbers_in_order():
    with patch("core.extract.gemma.ask_text",
               side_effect=["one", "two", "three"]) as at:
        out = extract.transcribe_pages([PNG, PNG, PNG])

    assert out == ["one", "two", "three"]
    prompts = [c.args[0] for c in at.call_args_list]
    assert "Page 1" in prompts[0]
    assert "Page 2" in prompts[1]
    assert "Page 3" in prompts[2]


# --------------------------------------------------------------------------- #
# Stage 2: structured extraction
# --------------------------------------------------------------------------- #

def test_extract_from_text_fills_full_text_and_page_count():
    core = _core_payload([_clause_payload("C1"), _clause_payload("C2", page=2)])
    with patch("core.extract.gemma.ask_json",
               return_value=extract._AgreementCore.model_validate(core)) as aj:
        result = extract.extract_agreement_from_text("THE FULL TEXT", page_count=5)

    assert isinstance(result, AgreementExtract)
    assert result.full_text == "THE FULL TEXT"
    assert result.page_count == 5
    assert [c.clause_id for c in result.clauses] == ["C1", "C2"]
    assert result.key_terms.monthly_rent == 50000

    # Confirm we asked for the trimmed schema, not AgreementExtract
    requested_model = aj.call_args.args[1]
    assert requested_model is extract._AgreementCore
    assert "full_text" not in requested_model.model_json_schema()["properties"]


def test_extract_from_text_prompt_includes_full_text():
    core = _core_payload([_clause_payload("C1")])
    with patch("core.extract.gemma.ask_json",
               return_value=extract._AgreementCore.model_validate(core)) as aj:
        extract.extract_agreement_from_text("SENTINEL TEXT", page_count=1)

    prompt = aj.call_args.args[0]
    assert "SENTINEL TEXT" in prompt


# --------------------------------------------------------------------------- #
# Full pipeline
# --------------------------------------------------------------------------- #

def test_extract_agreement_end_to_end():
    page_texts = ["Page one text.", "Page two text."]
    core = _core_payload([
        _clause_payload("C1", page=1),
        _clause_payload("C2", page=2),
    ])

    with patch("core.extract.gemma.ask_text", side_effect=page_texts), \
         patch("core.extract.gemma.ask_json",
               return_value=extract._AgreementCore.model_validate(core)) as aj:
        result = extract.extract_agreement([PNG, PNG])

    assert result.page_count == 2
    assert "<<<PAGE 1>>>" in result.full_text
    assert "<<<PAGE 2>>>" in result.full_text
    assert "Page one text." in result.full_text
    assert "Page two text." in result.full_text
    assert len(result.clauses) == 2

    # Structured prompt should contain the page-marked full text
    prompt = aj.call_args.args[0]
    assert "<<<PAGE 1>>>" in prompt
    assert "<<<PAGE 2>>>" in prompt


def test_extract_agreement_rejects_empty_input():
    with pytest.raises(gemma.GemmaError, match="No pages"):
        extract.extract_agreement([])


# --------------------------------------------------------------------------- #
# PDF rendering
# --------------------------------------------------------------------------- #

def test_render_pdf_missing_dependency_raises_friendly_error(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pypdfium2":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(gemma.GemmaError, match="pypdfium2"):
        extract.render_pdf("nonexistent.pdf")