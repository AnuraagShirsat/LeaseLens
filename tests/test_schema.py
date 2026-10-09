# tests/test_schema.py
"""Tests for core.schema Pydantic models."""

from pathlib import Path

from core.schema import (
    TOPICS,
    AgreementExtract,
    AnalysisBundle,
    Clause,
    Deduction,
    Finding,
    GapFinding,
    KeyTerms,
    NegotiationDrafts,
    RuleEntry,
    from_json_file,
    to_json_file,
)


def test_build_models_and_round_trip_json(tmp_path: Path) -> None:
    """Build every model and round-trip an AnalysisBundle through JSON."""
    clause = Clause(
        clause_id="C1",
        heading="Deposit",
        text="Tenant shall pay a security deposit of 1000.",
        page=1,
        read_confidence="high",
        read_note=None,
    )

    key_terms = KeyTerms(
        monthly_rent=2000,
        security_deposit=1000,
        agreement_term_months=12,
        lock_in_months=6,
        notice_period_days=30,
        rent_escalation_percent=5.0,
        start_date="2025-01-01",
        landlord_name="Landlord LLC",
        tenant_name="Jane Doe",
        deposit_mentions=[1000],
    )

    extract = AgreementExtract(
        clauses=[clause],
        key_terms=key_terms,
        full_text="Full lease text",
        page_count=1,
    )

    rule = RuleEntry(
        rule_id="R1",
        title="Deposit cap",
        rule_type="legal_requirement",
        source_name="State law",
        source_url="https://example.com/law",
        section="12.3",
        summary="Security deposits are capped.",
        applies_when="Residential lease",
        topics=["deposit"],
        date_checked="2025-01-01",
    )

    finding = Finding(
        clause_id="C1",
        quoted_text="security deposit of 1000",
        topic="deposit",
        risk="medium",
        risk_explanation="May exceed the legal cap.",
        why_it_matters="Tenant may owe less than stated.",
        evidence_status="verified_rule",
        rule_ids=["R1"],
        applicability_note=None,
        confidence="high",
        suggested_question="Is this deposit above the legal cap?",
    )

    gap = GapFinding(
        kind="missing",
        title="Missing notice clause",
        description="No notice period was found.",
        related_clause_ids=["C1"],
        severity="medium",
    )

    bundle = AnalysisBundle(
        extract=extract,
        findings=[finding],
        gaps=[gap],
        created_at="2025-01-01T00:00:00Z",
    )

    deduction = Deduction(
        label="Cleaning",
        category="cleaning",
        amount=150,
        linked_clause_id="C1",
        has_proof=False,
    )

    drafts = NegotiationDrafts(
        friendly="Could we discuss the deduction?",
        firm="Please provide proof for the deduction.",
        compromise="Let's split the difference.",
    )

    assert TOPICS[0] == "deposit"
    assert clause.clause_id == "C1"
    assert key_terms.deposit_mentions == [1000]
    assert rule.topics == ["deposit"]
    assert finding.rule_ids == ["R1"]
    assert gap.related_clause_ids == ["C1"]
    assert deduction.amount == 150
    assert drafts.friendly.startswith("Could")

    path = tmp_path / "analysis_bundle.json"
    to_json_file(bundle, path)
    loaded = from_json_file(path)

    assert loaded == bundle