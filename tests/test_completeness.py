# tests/test_completeness.py
"""Tests for the Part A (plain Python) gap checks in core.completeness.

Part B (the model call) is stubbed out with an autouse fixture so these
tests are deterministic and never touch Ollama.
"""

from __future__ import annotations

import pytest

from core import completeness
from core.completeness import MISSING_NOTE, find_gaps
from core.schema import AgreementExtract, Clause, KeyTerms


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def stub_model(monkeypatch):
    """Part A tests must not reach Part B (no Ollama, no network)."""
    monkeypatch.setattr(
        completeness,
        "_find_model_contradictions",
        lambda extract: [],
    )


def make_extract(clauses=(), full_text=None, **terms) -> AgreementExtract:
    """Build a minimal AgreementExtract for a test.

    ``clauses`` is an iterable of ``(clause_id, text)`` pairs.  Remaining
    keyword arguments are passed straight to ``KeyTerms``.
    """
    clause_models = [
        Clause(
            clause_id=cid,
            text=text,
            page=1,
            read_confidence="high",
        )
        for cid, text in clauses
    ]
    if full_text is None:
        full_text = "\n".join(text for _, text in clauses)
    return AgreementExtract(
        clauses=clause_models,
        key_terms=KeyTerms(**terms),
        full_text=full_text,
        page_count=1,
    )


def titles(gaps) -> list[str]:
    return [gap.title for gap in gaps]


def by_kind(gaps, kind: str):
    return [gap for gap in gaps if gap.kind == kind]


# A lease where every Part A check is satisfied.
COMPLETE_TERMS = {
    "monthly_rent": 25000,
    "security_deposit": 100000,
    "agreement_term_months": 11,
    "lock_in_months": 6,
    "notice_period_days": 30,
    "rent_escalation_percent": 5,
    "deposit_mentions": [100000],
}

COMPLETE_CLAUSES = [
    ("c1", "The monthly rent is 25,000 per month."),
    ("c2", "The security deposit shall be refunded within 30 days of vacating."),
    ("c3", "The tenancy is for a period of 11 months with a lock-in period of 6 months."),
    ("c4", "Either party may give 30 days notice."),
    ("c5", "The rent shall escalate by 5 percent annually."),
    ("c6", "The tenant shall be responsible for maintenance and repairs."),
    ("c7", "An inventory of fittings is attached as an annexure."),
    ("c8", "This agreement is subject to registration and stamp duty."),
]


def without(*clause_ids: str):
    """COMPLETE_CLAUSES minus the clauses with the given ids."""
    return [c for c in COMPLETE_CLAUSES if c[0] not in clause_ids]


# --------------------------------------------------------------------------- #
# Baseline
# --------------------------------------------------------------------------- #

def test_complete_extract_has_no_gaps():
    extract = make_extract(clauses=COMPLETE_CLAUSES, **COMPLETE_TERMS)
    assert find_gaps(extract) == []


EXPECTED_MISSING_TITLES = {
    "Monthly rent amount is not stated",
    "Security deposit amount is not stated",
    "Agreement term is not stated",
    "Lock-in period is not stated",
    "Notice period is not stated",
    "Rent escalation is not stated",
    "Who pays for maintenance and repairs is not stated",
    "Deposit return timeline is not stated",
    "Inventory or annexure of fittings is not mentioned",
    "Registration or stamp duty is not mentioned",
}


def test_empty_extract_flags_every_expected_missing_item():
    gaps = find_gaps(make_extract())
    assert all(gap.kind == "missing" for gap in gaps)
    assert set(titles(gaps)) == EXPECTED_MISSING_TITLES


# --------------------------------------------------------------------------- #
# Part A conflicts
# --------------------------------------------------------------------------- #

def test_two_different_deposit_amounts_are_a_conflict():
    extract = make_extract(
        clauses=[
            ("c1", "The deposit is 40,000."),
            ("c2", "The deposit is 50,000."),
        ],
        deposit_mentions=[40000, 50000],
    )
    conflicts = by_kind(find_gaps(extract), "conflict")
    assert len(conflicts) == 1
    assert "deposit" in conflicts[0].title.lower()

    description = conflicts[0].description
    assert "40,000" in description
    assert "50,000" in description
    # Both clauses that mention the amounts should be linked.
    assert set(conflicts[0].related_clause_ids) == {"c1", "c2"}


def test_repeated_deposit_amount_is_not_a_conflict():
    extract = make_extract(deposit_mentions=[40000, 40000])
    assert by_kind(find_gaps(extract), "conflict") == []


def test_lock_in_longer_than_term_is_a_conflict():
    extract = make_extract(
        lock_in_months=12,
        agreement_term_months=11,
    )
    conflicts = by_kind(find_gaps(extract), "conflict")
    assert any("lock-in" in gap.title.lower() for gap in conflicts)


def test_lock_in_equal_to_term_is_not_a_conflict():
    extract = make_extract(lock_in_months=11, agreement_term_months=11)
    assert by_kind(find_gaps(extract), "conflict") == []


def test_lock_in_longer_than_term_is_not_checked_when_term_is_missing():
    # If the term is unknown we cannot call it a conflict.
    extract = make_extract(lock_in_months=12, agreement_term_months=None)
    assert by_kind(find_gaps(extract), "conflict") == []


# --------------------------------------------------------------------------- #
# Part A missing items, one at a time
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "expected_title, clauses, term_overrides",
    [
        (
            "Monthly rent amount is not stated",
            without("c1"),
            {"monthly_rent": None},
        ),
        (
            "Security deposit amount is not stated",
            without("c2"),
            {"security_deposit": None, "deposit_mentions": []},
        ),
        (
            "Agreement term is not stated",
            without("c3"),
            {"agreement_term_months": None, "lock_in_months": None},
        ),
        (
            "Lock-in period is not stated",
            without("c3"),
            {"lock_in_months": None, "agreement_term_months": None},
        ),
        (
            "Notice period is not stated",
            without("c4"),
            {"notice_period_days": None},
        ),
        (
            "Rent escalation is not stated",
            without("c5"),
            {"rent_escalation_percent": None},
        ),
        (
            "Who pays for maintenance and repairs is not stated",
            without("c6"),
            {},
        ),
        (
            "Inventory or annexure of fittings is not mentioned",
            without("c7"),
            {},
        ),
        (
            "Registration or stamp duty is not mentioned",
            without("c8"),
            {},
        ),
    ],
)
def test_each_missing_item_is_flagged(expected_title, clauses, term_overrides):
    merged = {**COMPLETE_TERMS, **term_overrides}
    extract = make_extract(clauses=clauses, **merged)
    assert expected_title in titles(find_gaps(extract))


def test_deposit_return_timeline_missing_when_only_payment_is_mentioned():
    # A clause that talks about the deposit but never says when it is refunded
    # should still leave the refund timeline flagged as missing.
    clauses = without("c2") + [
        ("c2", "The security deposit shall be paid by the tenant on signing."),
    ]
    extract = make_extract(clauses=clauses, **COMPLETE_TERMS)
    gaps = find_gaps(extract)

    assert "Deposit return timeline is not stated" in titles(gaps)
    # The deposit amount itself *is* covered by that clause, so it should not
    # be flagged as missing.
    assert "Security deposit amount is not stated" not in titles(gaps)


# --------------------------------------------------------------------------- #
# Neutral wording
# --------------------------------------------------------------------------- #

def test_missing_note_is_appended_only_to_missing_gaps():
    extract = make_extract(
        clauses=[
            ("c1", "The deposit is 40,000."),
            ("c2", "The deposit is 50,000."),
        ],
        deposit_mentions=[40000, 50000],
        lock_in_months=12,
        agreement_term_months=11,
    )
    gaps = find_gaps(extract)

    missing = by_kind(gaps, "missing")
    conflicts = by_kind(gaps, "conflict")

    assert missing and conflicts
    assert all(MISSING_NOTE in gap.description for gap in missing)
    assert all(MISSING_NOTE not in gap.description for gap in conflicts)