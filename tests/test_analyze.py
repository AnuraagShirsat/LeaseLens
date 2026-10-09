# tests/test_analyze.py
"""Tests for core.analyze with a mocked gemma layer."""

from __future__ import annotations

import json
import re

import pytest

from core import analyze, rules
from core.schema import AgreementExtract, Clause, KeyTerms


@pytest.fixture
def kb(monkeypatch, tmp_path):
    payload = {
        "rules": [
            {
                "rule_id": "R-DEP-1",
                "title": "Deposit must be refundable",
                "rule_type": "legal_requirement",
                "source_name": "Test Statute",
                "summary": "Security deposits must generally be refundable.",
                "topics": ["deposit"],
                "date_checked": "2024-01-01",
            },
            {
                "rule_id": "R-DEP-2",
                "title": "Deposit cap",
                "rule_type": "legal_requirement",
                "source_name": "Test Statute",
                "summary": "Deposit amounts may be capped by law.",
                "topics": ["deposit"],
                "date_checked": "2024-01-01",
            },
        ]
    }
    path = tmp_path / "kb.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    rules.load_rules(path)
    try:
        yield rules
    finally:
        rules._reset_cache()


@pytest.fixture
def extract_two_clauses():
    clauses = [
        Clause(
            clause_id="c1",
            text="The security deposit shall be non-refundable under all circumstances.",
            page=1,
            read_confidence="high",
        ),
        Clause(
            clause_id="c2",
            text="IN WITNESS WHEREOF the parties have signed below.",
            page=2,
            read_confidence="high",
        ),
    ]
    return AgreementExtract(
        clauses=clauses,
        key_terms=KeyTerms(security_deposit=100000),
        full_text="\n".join(c.text for c in clauses),
        page_count=2,
    )


_TOPIC_RE = re.compile(r"^TOPIC:\s*(\S+)\s*$", re.MULTILINE)


def _topic_from_prompt(prompt: str) -> str | None:
    m = _TOPIC_RE.search(prompt)
    return m.group(1) if m else None


def _make_fake_ask_json(classification, *, findings_by_topic=None, finding=None):
    calls: list[str] = []

    def fake(prompt, response_model, *args, **kwargs):
        name = response_model.__name__
        calls.append(name)

        if name == "_ClassificationResult":
            return response_model(classifications=classification)

        if name == "_FindingDraft":
            if findings_by_topic is not None:
                topic = _topic_from_prompt(prompt)
                if topic is not None and topic in findings_by_topic:
                    return response_model(**findings_by_topic[topic])
                if "_default" in findings_by_topic:
                    return response_model(**findings_by_topic["_default"])
                raise AssertionError(f"no finding draft for topic {topic!r}")
            if finding is not None:
                return response_model(**finding)
            raise AssertionError("no finding payload configured")

        raise AssertionError(f"unexpected response_model: {name}")

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


_DEPOSIT_DRAFT_HIGH = {
    "risk": "high",
    "risk_explanation": "You could lose the entire deposit.",
    "why_it_matters": "The deposit may never be returned.",
    "rule_ids": ["R-DEP-1"],
    "applicability_note": None,
    "confidence": "high",
    "suggested_question": "Could the deposit be made refundable?",
}

_OTHER_DRAFT_LOW = {
    "risk": "low",
    "risk_explanation": "Standard boilerplate clause.",
    "why_it_matters": "Nothing to worry about here.",
    "rule_ids": [],
    "applicability_note": None,
    "confidence": "high",
    "suggested_question": "…?",
}


def test_fake_rule_id_is_removed(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "deposit"},
        {"clause_id": "c2", "topic": "other"},
    ]
    deposit_draft = {**_DEPOSIT_DRAFT_HIGH, "rule_ids": ["R-DEP-1", "FAKE-RULE-999"]}
    fake = _make_fake_ask_json(
        classification,
        findings_by_topic={"deposit": deposit_draft, "other": _OTHER_DRAFT_LOW},
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract_two_clauses)

    assert len(findings) == 1
    f = findings[0]
    assert f.clause_id == "c1"
    assert f.topic == "deposit"
    assert f.quoted_text == extract_two_clauses.clauses[0].text
    assert f.rule_ids == ["R-DEP-1"]
    assert f.evidence_status == "verified_rule"


def test_only_fake_rule_ids_mark_no_verified_rule(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "deposit"},
        {"clause_id": "c2", "topic": "other"},
    ]
    deposit_draft = {
        **_DEPOSIT_DRAFT_HIGH,
        "risk": "medium",
        "confidence": "medium",
        "rule_ids": ["TOTALLY-FAKE", "ALSO-FAKE"],
    }
    fake = _make_fake_ask_json(
        classification,
        findings_by_topic={"deposit": deposit_draft, "other": _OTHER_DRAFT_LOW},
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract_two_clauses)

    assert len(findings) == 1
    assert findings[0].clause_id == "c1"
    assert findings[0].rule_ids == []
    assert findings[0].evidence_status == "no_verified_rule_found"


def test_rule_in_kb_but_not_in_candidates_is_removed(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "utilities"},
        {"clause_id": "c2", "topic": "other"},
    ]
    utilities_draft = {
        "risk": "medium",
        "risk_explanation": "…",
        "why_it_matters": "…",
        "rule_ids": ["R-DEP-1"],
        "applicability_note": None,
        "confidence": "medium",
        "suggested_question": "…?",
    }
    fake = _make_fake_ask_json(
        classification,
        findings_by_topic={"utilities": utilities_draft, "other": _OTHER_DRAFT_LOW},
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract_two_clauses)

    assert len(findings) == 1
    assert findings[0].clause_id == "c1"
    assert findings[0].topic == "utilities"
    assert findings[0].rule_ids == []
    assert findings[0].evidence_status == "no_verified_rule_found"


def test_confidence_is_lower_of_model_and_read(monkeypatch, kb):
    clause = Clause(
        clause_id="c1",
        text="The deposit is non-refundable.",
        page=1,
        read_confidence="low",
    )
    extract = AgreementExtract(
        clauses=[clause],
        key_terms=KeyTerms(),
        full_text=clause.text,
        page_count=1,
    )
    fake = _make_fake_ask_json(
        [{"clause_id": "c1", "topic": "deposit"}],
        findings_by_topic={
            "deposit": {**_DEPOSIT_DRAFT_HIGH, "risk": "medium", "confidence": "high"},
        },
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract)
    assert len(findings) == 1
    assert findings[0].confidence == "low"
    assert findings[0].evidence_status == "verified_rule"


def test_other_topic_low_risk_is_skipped(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "other"},
        {"clause_id": "c2", "topic": "other"},
    ]
    fake = _make_fake_ask_json(
        classification,
        finding={
            "risk": "low",
            "risk_explanation": "Standard boilerplate.",
            "why_it_matters": "Nothing to worry about.",
            "rule_ids": [],
            "applicability_note": None,
            "confidence": "high",
            "suggested_question": "…?",
        },
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract_two_clauses)
    assert findings == []


def test_other_topic_medium_risk_is_kept(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "other"},
        {"clause_id": "c2", "topic": "other"},
    ]
    fake = _make_fake_ask_json(
        classification,
        finding={
            "risk": "medium",
            "risk_explanation": "Unclear wording.",
            "why_it_matters": "You may want clarification.",
            "rule_ids": [],
            "applicability_note": "Depends on the premises type.",
            "confidence": "medium",
            "suggested_question": "Could you clarify this clause?",
        },
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    findings = analyze.analyze_clauses(extract_two_clauses)
    assert len(findings) == 2
    assert all(f.topic == "other" for f in findings)
    assert all(f.evidence_status == "no_verified_rule_found" for f in findings)


def test_classification_called_once_and_only_one_analysis_per_clause(
    monkeypatch, kb, extract_two_clauses
):
    classification = [
        {"clause_id": "c1", "topic": "deposit"},
        {"clause_id": "c2", "topic": "other"},
    ]
    fake = _make_fake_ask_json(
        classification,
        finding={
            "risk": "medium",
            "risk_explanation": "…",
            "why_it_matters": "…",
            "rule_ids": [],
            "applicability_note": None,
            "confidence": "medium",
            "suggested_question": "…?",
        },
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    analyze.analyze_clauses(extract_two_clauses)

    assert fake.calls.count("_ClassificationResult") == 1
    assert fake.calls.count("_FindingDraft") == len(extract_two_clauses.clauses)


def test_progress_cb_is_invoked(monkeypatch, kb, extract_two_clauses):
    classification = [
        {"clause_id": "c1", "topic": "deposit"},
        {"clause_id": "c2", "topic": "other"},
    ]
    fake = _make_fake_ask_json(
        classification,
        finding={
            "risk": "low",
            "risk_explanation": "…",
            "why_it_matters": "…",
            "rule_ids": [],
            "applicability_note": None,
            "confidence": "high",
            "suggested_question": "…?",
        },
    )
    monkeypatch.setattr(analyze.gemma, "ask_json", fake)

    events: list[str] = []
    analyze.analyze_clauses(extract_two_clauses, progress_cb=events.append)

    assert any("Classifying" in e for e in events)
    assert any("Analyzing" in e for e in events)