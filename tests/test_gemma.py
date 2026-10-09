"""Tests for core.gemma — fully mocked, no Ollama required."""

import json
from unittest.mock import patch

import pytest

from core import gemma
from core.gemma import GemmaError
from core.schema import AgreementExtract, Clause


MODEL = "gemma-test"


@pytest.fixture(autouse=True)
def fake_config(monkeypatch):
    monkeypatch.setattr(gemma.config, "MODEL_NAME", MODEL)


def _list_with_model():
    return {"models": [{"name": MODEL}]}


def _list_other_models():
    return {"models": [{"name": "some-other-model"}]}


def _clause_payload(**overrides):
    base = {
        "clause_id": "C1",
        "heading": "Security Deposit",
        "text": "Tenant shall pay a deposit of INR 100,000.",
        "page": 2,
        "read_confidence": "high",
        "read_note": None,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# is_ollama_running
# --------------------------------------------------------------------------- #

def test_is_ollama_running_true():
    with patch("core.gemma.ollama.list", return_value={"models": []}):
        assert gemma.is_ollama_running() is True


def test_is_ollama_running_false():
    with patch("core.gemma.ollama.list", side_effect=Exception("refused")):
        assert gemma.is_ollama_running() is False


# --------------------------------------------------------------------------- #
# ask_json — happy path
# --------------------------------------------------------------------------- #

def test_ask_json_success_returns_pydantic_object():
    payload = _clause_payload()
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": json.dumps(payload)}}):
        result = gemma.ask_json("Extract the deposit clause.", Clause)

    assert isinstance(result, Clause)
    assert result.clause_id == "C1"
    assert result.read_confidence == "high"


def test_ask_json_passes_expected_args():
    payload = _clause_payload()
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": json.dumps(payload)}}) as chat:
        gemma.ask_json("Extract the deposit clause.", Clause)

    kwargs = chat.call_args.kwargs
    assert kwargs["model"] == MODEL
    assert kwargs["format"] == Clause.model_json_schema()
    assert kwargs["options"]["temperature"] == 0.1
    assert kwargs["messages"][0]["content"] == "Extract the deposit clause."
    assert "images" not in kwargs["messages"][0]


def test_ask_json_with_images_includes_them():
    png = b"\x89PNG\r\n\x1a\n"
    payload = _clause_payload()
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": json.dumps(payload)}}) as chat:
        gemma.ask_json("Extract.", Clause, images=[png])

    assert chat.call_args.kwargs["messages"][0]["images"] == [png]


def test_ask_json_works_with_nested_schema():
    """AgreementExtract contains nested models — schema is passed through as-is."""
    payload = {
        "clauses": [_clause_payload()],
        "key_terms": {"monthly_rent": 50000},
        "full_text": "…",
        "page_count": 10,
    }
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": json.dumps(payload)}}) as chat:
        result = gemma.ask_json("Extract.", AgreementExtract)

    assert isinstance(result, AgreementExtract)
    assert result.clauses[0].clause_id == "C1"
    assert "$defs" in chat.call_args.kwargs["format"]


def test_ask_json_retries_on_invalid_then_succeeds():
    good = json.dumps(_clause_payload(clause_id="C2"))
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat", side_effect=[
             {"message": {"content": "not json"}},
             {"message": {"content": good}},
         ]) as chat:
        result = gemma.ask_json("Extract.", Clause)

    assert result.clause_id == "C2"
    assert chat.call_count == 2
    second_prompt = chat.call_args_list[1].kwargs["messages"][0]["content"]
    assert "valid JSON" in second_prompt


def test_ask_json_retries_on_schema_violation():
    """Valid JSON, invalid schema (unknown read_confidence) — should retry."""
    bad = json.dumps(_clause_payload(read_confidence="VERY_HIGH"))
    good = json.dumps(_clause_payload(read_confidence="low"))
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat", side_effect=[
             {"message": {"content": bad}},
             {"message": {"content": good}},
         ]) as chat:
        result = gemma.ask_json("Extract.", Clause)

    assert result.read_confidence == "low"
    assert chat.call_count == 2


def test_ask_json_strips_markdown_code_fences():
    """Some models wrap JSON in ```json ... ``` fences; we should still parse."""
    fenced = "```json\n" + json.dumps(_clause_payload()) + "\n```"
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": fenced}}):
        result = gemma.ask_json("Extract.", Clause)

    assert result.clause_id == "C1"


def test_ask_json_gives_up_after_retries():
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": "still bad"}}) as chat:
        with pytest.raises(GemmaError, match="invalid output"):
            gemma.ask_json("Extract.", Clause, retries=1)

    assert chat.call_count == 2  # initial + 1 retry


# --------------------------------------------------------------------------- #
# ask_json — error paths
# --------------------------------------------------------------------------- #

def test_ask_json_ollama_not_running():
    with patch("core.gemma.ollama.list", side_effect=Exception("conn refused")):
        with pytest.raises(GemmaError, match="Ollama isn't running"):
            gemma.ask_json("Extract.", Clause)


def test_ask_json_model_missing():
    with patch("core.gemma.ollama.list", return_value=_list_other_models()):
        with pytest.raises(GemmaError, match="isn't installed"):
            gemma.ask_json("Extract.", Clause)


def test_ask_json_timeout():
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               side_effect=Exception("request timed out")):
        with pytest.raises(GemmaError, match="timed out"):
            gemma.ask_json("Extract.", Clause)


def test_ask_json_generic_ollama_error():
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat", side_effect=Exception("kaboom")):
        with pytest.raises(GemmaError, match="Error talking to Ollama"):
            gemma.ask_json("Extract.", Clause)


# --------------------------------------------------------------------------- #
# ask_text
# --------------------------------------------------------------------------- #

def test_ask_text_success_and_temperature():
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": "hello"}}) as chat:
        out = gemma.ask_text("hi")

    assert out == "hello"
    kwargs = chat.call_args.kwargs
    assert kwargs["options"]["temperature"] == 0.3
    assert kwargs["format"] is None


def test_ask_text_with_images():
    png = b"\x89PNG\r\n\x1a\n"
    with patch("core.gemma.ollama.list", return_value=_list_with_model()), \
         patch("core.gemma.ollama.chat",
               return_value={"message": {"content": "ok"}}) as chat:
        gemma.ask_text("describe", images=[png])

    assert chat.call_args.kwargs["messages"][0]["images"] == [png]


def test_ask_text_ollama_not_running():
    with patch("core.gemma.ollama.list", side_effect=Exception("down")):
        with pytest.raises(GemmaError, match="Ollama isn't running"):
            gemma.ask_text("hi")
            