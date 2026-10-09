# tests/test_simulator.py
# Checks for the Deposit Recovery Simulator maths.

from core.schema import Clause, Deduction
from core.simulator import (
    DISCLAIMER,
    NEEDS_CLARIFICATION,
    REVIEW_FURTHER,
    SUPPORTED,
    simulate,
)


def make_clause(clause_id, text):
    """Build a small Clause for testing."""
    return Clause(
        clause_id=clause_id, heading=None, text=text,
        page=1, read_confidence="high", read_note=None,
    )


def make_deduction(label, category, amount, clause_id, proof):
    """Build a Deduction for testing."""
    return Deduction(
        label=label, category=category, amount=amount,
        linked_clause_id=clause_id, has_proof=proof,
    )


PAINT_CLAUSE = make_clause("C1", "Costs of painting and repairs may be deducted.")


def test_required_example():
    # Deposit 60000, deduction 12000, no clause, no proof => 48000 returned
    deduction = make_deduction("Painting", "painting_repairs", 12000, None, False)
    result = simulate(60000, 20000, [deduction], [])
    assert result["scenarios"]["as_proposed"]["amount_returned"] == 48000
    assert result["items"][0]["status"] == REVIEW_FURTHER
    # With nothing supported, the tenant-favourable scenario returns it all
    assert result["scenarios"]["tenant_favourable"]["amount_returned"] == 60000
    assert "scenario estimate" in DISCLAIMER


def test_supported():
    deduction = make_deduction("Painting", "painting_repairs", 5000, "C1", True)
    result = simulate(60000, 20000, [deduction], [PAINT_CLAUSE])
    assert result["items"][0]["status"] == SUPPORTED


def test_linked_without_proof_needs_clarification():
    deduction = make_deduction("Painting", "painting_repairs", 5000, "C1", False)
    result = simulate(60000, 20000, [deduction], [PAINT_CLAUSE])
    assert result["items"][0]["status"] == NEEDS_CLARIFICATION


def test_linked_clause_without_keyword_needs_clarification():
    deduction = make_deduction("Cleaning", "cleaning", 2000, "C1", True)
    result = simulate(60000, 20000, [deduction], [PAINT_CLAUSE])
    assert result["items"][0]["status"] == NEEDS_CLARIFICATION


def test_unlinked_with_proof_needs_clarification():
    deduction = make_deduction("Damage", "damage", 3000, None, True)
    result = simulate(60000, 20000, [deduction], [PAINT_CLAUSE])
    assert result["items"][0]["status"] == NEEDS_CLARIFICATION


def test_unknown_clause_id_is_treated_as_unlinked():
    deduction = make_deduction("Damage", "damage", 3000, "C99", False)
    result = simulate(60000, 20000, [deduction], [PAINT_CLAUSE])
    assert result["items"][0]["status"] == REVIEW_FURTHER


def test_amount_above_cap_needs_review():
    cap_clause = make_clause(
        "C2", "The Landlord may deduct up to Rs. 5,000 for painting and repairs."
    )
    deduction = make_deduction("Painting", "painting_repairs", 8000, "C2", True)
    result = simulate(60000, 20000, [deduction], [cap_clause])
    assert result["items"][0]["status"] == REVIEW_FURTHER


def test_amount_under_cap_is_supported():
    cap_clause = make_clause(
        "C2", "The Landlord may deduct up to Rs. 5,000 for painting and repairs."
    )
    deduction = make_deduction("Painting", "painting_repairs", 4000, "C2", True)
    result = simulate(60000, 20000, [deduction], [cap_clause])
    assert result["items"][0]["status"] == SUPPORTED


def test_three_scenarios_with_mixed_deductions():
    deductions = [
        make_deduction("Painting", "painting_repairs", 10000, "C1", True),
        make_deduction("Cleaning", "cleaning", 5000, "C1", True),
        make_deduction("Damage", "damage", 3000, None, False),
    ]
    result = simulate(100000, 20000, deductions, [PAINT_CLAUSE])
    statuses = [item["status"] for item in result["items"]]
    assert statuses == [SUPPORTED, NEEDS_CLARIFICATION, REVIEW_FURTHER]
    scenarios = result["scenarios"]
    assert scenarios["tenant_favourable"]["amount_returned"] == 90000
    assert scenarios["middle"]["amount_returned"] == 85000
    assert scenarios["as_proposed"]["amount_returned"] == 82000
    assert scenarios["as_proposed"]["total_deducted"] == 18000


def test_amount_returned_never_below_zero():
    deduction = make_deduction("Damage", "damage", 5000, None, False)
    result = simulate(1000, 500, [deduction], [])
    assert result["scenarios"]["as_proposed"]["amount_returned"] == 0


def test_deposit_months_of_rent():
    result = simulate(150000, 25000, [], [])
    assert result["deposit_months_of_rent"] == 6.0
    result = simulate(150000, 0, [], [])
    assert result["deposit_months_of_rent"] is None