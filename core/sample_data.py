# core/sample_data.py
# Fake (clearly fictional) results so we can build the screens
# without needing the AI. Nothing here is a real law or a real person.

from core.schema import (
    AgreementExtract,
    AnalysisBundle,
    Clause,
    Finding,
    GapFinding,
    KeyTerms,
    RuleEntry,
)

SAMPLE_MARKER = "SAMPLE - NOT A REAL RULE"


def _make_clauses() -> list[Clause]:
    """Eight made-up clauses, C1 to C8."""
    return [
        Clause(
            clause_id="C1", heading="Security Deposit", page=1,
            text=("The Tenant shall pay an interest-free security deposit of "
                  "Rs. 1,50,000 to the Landlord at the time of signing."),
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C2", heading="Deductions", page=1,
            text=("The Landlord may deduct from the deposit of Rs. 1,00,000 "
                  "any amount for painting, repairs and other charges as "
                  "decided by the Landlord at the time of vacating."),
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C3", heading="Lock-in Period", page=1,
            text=("The Tenant shall not vacate the premises during the first "
                  "6 months of the tenancy (lock-in period)."),
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C4", heading="Notice Period", page=2,
            text=("Either party must give 3 months written notice to end "
                  "this agreement."),
            read_confidence="medium",
            read_note="Part of the line was slightly blurry.",
        ),
        Clause(
            clause_id="C5", heading="Rent Increase", page=2,
            text="The monthly rent shall increase by 10% every year.",
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C6", heading="Maintenance", page=2,
            text=("The Tenant shall keep the premises in good condition and "
                  "carry out minor maintenance."),
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C7", heading="Inspection", page=3,
            text=("The Landlord or his representative may enter the premises "
                  "for inspection with prior notice."),
            read_confidence="high", read_note=None,
        ),
        Clause(
            clause_id="C8", heading="Subletting", page=3,
            text=("The Tenant shall not sublet or part with possession of "
                  "the premises without written consent of the Landlord."),
            read_confidence="low",
            read_note="This line was cut off at the edge of the photo.",
        ),
    ]


def _make_findings(clauses: list[Clause]) -> list[Finding]:
    """Six made-up findings: some high, medium, low; some with evidence."""
    text = {c.clause_id: c.text for c in clauses}
    return [
        Finding(
            clause_id="C2", quoted_text=text["C2"], topic="deductions",
            risk="high",
            risk_explanation=("The clause lets the Landlord decide any "
                              "deduction without naming items or amounts."),
            why_it_matters=("You may get back less deposit than expected, "
                            "and it may be hard to question the amount."),
            evidence_status="verified_rule", rule_ids=["SAMPLE-1"],
            applicability_note="Whether this applies may depend on the type of premises.",
            confidence="high",
            suggested_question=("Could the agreement list which deductions "
                                "are allowed and require bills as proof?"),
        ),
        Finding(
            clause_id="C1", quoted_text=text["C1"], topic="deposit",
            risk="medium",
            risk_explanation=("The deposit is 6 months of rent, which is a "
                              "large amount to keep with a landlord."),
            why_it_matters=("A large amount may be tied up for a long time "
                            "if there is a dispute."),
            evidence_status="verified_rule", rule_ids=["SAMPLE-2"],
            applicability_note=None, confidence="high",
            suggested_question=("Could the deposit be reduced, or could the "
                                "return date be written down?"),
        ),
        Finding(
            clause_id="C3", quoted_text=text["C3"], topic="lock_in",
            risk="medium",
            risk_explanation=("You may be unable to leave for 6 months "
                              "without paying."),
            why_it_matters=("If your plans change, you could owe rent for "
                            "months you do not use."),
            evidence_status="no_verified_rule_found", rule_ids=[],
            applicability_note=None, confidence="high",
            suggested_question=("Could the lock-in be shortened, or could "
                                "an early exit fee be agreed in writing?"),
        ),
        Finding(
            clause_id="C4", quoted_text=text["C4"], topic="termination_notice",
            risk="medium",
            risk_explanation=("A 3-month notice period is long compared "
                              "with the 11-month agreement."),
            why_it_matters=("You may have to pay rent during the whole "
                            "notice period."),
            evidence_status="verified_rule", rule_ids=["SAMPLE-3"],
            applicability_note="This may depend on the rent level.",
            confidence="medium",
            suggested_question="Could the notice period be 1 month for both sides?",
        ),
        Finding(
            clause_id="C5", quoted_text=text["C5"], topic="rent_escalation",
            risk="low",
            risk_explanation=("A fixed yearly increase is common and "
                              "clearly stated."),
            why_it_matters=("Your rent may be higher than you plan for in "
                            "later years."),
            evidence_status="no_verified_rule_found", rule_ids=[],
            applicability_note=None, confidence="high",
            suggested_question=("Is the 10% increase applied only after "
                                "the first 11 months?"),
        ),
        Finding(
            clause_id="C7", quoted_text=text["C7"], topic="entry_inspection",
            risk="low",
            risk_explanation=("Entry needs prior notice, but the amount of "
                              "notice is not stated."),
            why_it_matters=("Your privacy may be affected if visits are "
                            "frequent."),
            evidence_status="no_verified_rule_found", rule_ids=[],
            applicability_note=None, confidence="high",
            suggested_question=("Could the agreement say how many hours of "
                                "notice are given?"),
        ),
    ]


def _make_gaps() -> list[GapFinding]:
    """Three made-up gaps: one conflict, two missing."""
    return [
        GapFinding(
            kind="conflict",
            title="Two different deposit amounts",
            description=("Clause C1 mentions a deposit of Rs. 1,50,000 but "
                         "clause C2 mentions Rs. 1,00,000. You may want to "
                         "ask which amount is correct."),
            related_clause_ids=["C1", "C2"], severity="high",
        ),
        GapFinding(
            kind="missing",
            title="No deposit return timeline",
            description=("The agreement does not say how many days after "
                         "you leave the deposit will be returned. A missing "
                         "detail is not automatically a legal violation, "
                         "but you may want to ask for it to be written down."),
            related_clause_ids=["C1"], severity="medium",
        ),
        GapFinding(
            kind="missing",
            title="No inventory of fittings",
            description=("No list of furniture or fittings is attached. A "
                         "missing detail is not automatically a legal "
                         "violation, but you may want to ask for it to be "
                         "written down."),
            related_clause_ids=[], severity="low",
        ),
    ]


def get_sample_bundle() -> AnalysisBundle:
    """Return a complete fake AnalysisBundle for demo mode."""
    clauses = _make_clauses()
    key_terms = KeyTerms(
        monthly_rent=25000,
        security_deposit=150000,
        agreement_term_months=11,
        lock_in_months=6,
        notice_period_days=90,
        rent_escalation_percent=10,
        start_date="2026-11-01",
        landlord_name="Mr. Sample Landlord",
        tenant_name="Ms. Sample Tenant",
        deposit_mentions=[150000, 100000],
    )
    extract = AgreementExtract(
        clauses=clauses,
        key_terms=key_terms,
        full_text="\n".join(c.text for c in clauses),
        page_count=3,
    )
    return AnalysisBundle(
        extract=extract,
        findings=_make_findings(clauses),
        gaps=_make_gaps(),
        created_at="2026-10-09 10:00",
    )


def get_sample_rules() -> list[RuleEntry]:
    """Fake rules matching the rule ids used in the sample findings."""
    def make(rule_id, title, topics):
        return RuleEntry(
            rule_id=rule_id,
            title=f"{title} ({SAMPLE_MARKER})",
            rule_type="best_practice",
            source_name="Sample source (fictional)",
            source_url="https://example.com/sample",
            section="Sample section 1",
            summary="This is a fictional rule used only for demo screens.",
            applies_when=None,
            topics=topics,
            date_checked="2026-10-09",
        )

    return [
        make("SAMPLE-1", "Sample deductions rule", ["deductions"]),
        make("SAMPLE-2", "Sample deposit rule", ["deposit"]),
        make("SAMPLE-3", "Sample notice rule", ["termination_notice"]),
    ]