# tests/test_negotiator.py
# Checks for the Clause Negotiator. The AI is replaced by a fake,
# so these tests run without Ollama.

import pytest

from core import negotiator
from core.sample_data import get_sample_bundle
from core.schema import NegotiationDrafts

FINDINGS = get_sample_bundle().findings
VERIFIED_FINDING = FINDINGS[0]    # C2 deductions, has a (sample) rule id
PLAIN_FINDING = FINDINGS[2]       # C3 lock-in, no verified rule


def fake_model(friendly, firm, compromise):
    """Build a fake _call_model that returns the given drafts."""
    def fake(prompt):
        return NegotiationDrafts(
            friendly=friendly, firm=firm, compromise=compromise
        )
    return fake


def test_generate_drafts_returns_three_messages(monkeypatch):
    monkeypatch.setattr(
        negotiator, "_call_model",
        fake_model("Hello, could you clarify clause C3?",
                   "Please change clause C3.",
                   "How about 3 months for clause C3?"),
    )
    drafts = negotiator.generate_drafts(PLAIN_FINDING)
    assert drafts.friendly.startswith("Hello")
    assert drafts.firm.startswith("Please")
    assert drafts.compromise.startswith("How about")


def test_prompt_has_clause_and_placeholders():
    prompt = negotiator.build_prompt(PLAIN_FINDING, None, None, [])
    assert "C3" in prompt
    assert PLAIN_FINDING.quoted_text in prompt
    assert "[Landlord Name]" in prompt
    assert "[Tenant Name]" in prompt
    assert negotiator.NO_LAW_RULE in prompt


def test_prompt_uses_names_when_given():
    prompt = negotiator.build_prompt(PLAIN_FINDING, "Anita", "Ravi", [])
    assert "Anita" in prompt
    assert "Ravi" in prompt
    assert "[Landlord Name]" not in prompt


def test_prompt_mentions_rule_when_found():
    notes = ["Example rule title: Example summary."]
    prompt = negotiator.build_prompt(VERIFIED_FINDING, None, None, notes)
    assert "Example rule title: Example summary." in prompt
    assert "as I understand it" in prompt
    assert negotiator.NO_LAW_RULE not in prompt


def test_banned_words_are_removed(monkeypatch):
    monkeypatch.setattr(
        negotiator, "_call_model",
        fake_model("This is Illegal and I am unhappy.",
                   "This clause is unlawful, please change it.",
                   "Acting illegally is not what we want, so let us agree."),
    )
    drafts = negotiator.generate_drafts(PLAIN_FINDING)
    for message in (drafts.friendly, drafts.firm, drafts.compromise):
        lowered = message.lower()
        assert "illegal" not in lowered
        assert "unlawful" not in lowered


def test_long_message_is_trimmed(monkeypatch):
    long_text = "This is a sentence. " * 100
    monkeypatch.setattr(
        negotiator, "_call_model", fake_model(long_text, "Short.", "Short.")
    )
    drafts = negotiator.generate_drafts(PLAIN_FINDING)
    assert len(drafts.friendly.split()) <= 120
    assert drafts.friendly.endswith(".")


def test_empty_answer_raises_friendly_error(monkeypatch):
    monkeypatch.setattr(
        negotiator, "_call_model", fake_model("", "Firm.", "Compromise.")
    )
    with pytest.raises(RuntimeError):
        negotiator.generate_drafts(PLAIN_FINDING)


def test_rule_notes_empty_without_verified_rule():
    assert negotiator._rule_notes(PLAIN_FINDING) == []