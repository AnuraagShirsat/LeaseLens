# smoke_extract.py
"""End-to-end smoke test: extract → analyze → assess deductions → negotiate."""

from __future__ import annotations

from core import analyze, extract, rules
from core.schema import Deduction


# --------------------------------------------------------------------------- #
# 1. Extract
# --------------------------------------------------------------------------- #

# Adjust to whichever entry-point your extract module exposes, e.g.
#   extract.extract_from_pdf("path/to/lease.pdf")
# The block below assumes a zero-arg demo helper lives in core.extract.
agreement = extract.run_demo()   # <-- change this call to match your code

print(f"Done. {len(agreement.clauses)} clauses, {agreement.page_count} pages.")
print(f"Rent:    {agreement.key_terms.monthly_rent}")
print(f"Deposit: {agreement.key_terms.security_deposit}")


# --------------------------------------------------------------------------- #
# 2. Load the knowledge base
# --------------------------------------------------------------------------- #

rules.load_rules()   # uses config.KB_PATH
print(f"Loaded {len(rules.all_rules())} rule(s) from {rules.config.KB_PATH}")


# --------------------------------------------------------------------------- #
# 3. Clause analysis
# --------------------------------------------------------------------------- #

print("\n--- Clause analysis ---")
findings = analyze.analyze_clauses(
    agreement,
    progress_cb=lambda m: print(f"  {m}"),
)

print(f"\n{len(findings)} finding(s):")
for f in findings:
    print(f"  [{f.risk.upper():6}] {f.clause_id} ({f.topic})  evidence={f.evidence_status}")
    print(f"          {f.risk_explanation}")
    if f.why_it_matters:
        print(f"          Why it matters: {f.why_it_matters}")
    if f.rule_ids:
        print(f"          rules: {', '.join(f.rule_ids)}")
    if f.applicability_note:
        print(f"          note: {f.applicability_note}")
    print(f"          Q: {f.suggested_question}")
    print()


# --------------------------------------------------------------------------- #
# 4. Sample deductions (in the real app these come from the user)
# --------------------------------------------------------------------------- #

sample_deductions = [
    Deduction(
        label="Wall repainting",
        category="wear_and_tear",
        amount=8000,
        linked_clause_id=None,
        has_proof=False,
    ),
    Deduction(
        label="Broken window latch",
        category="damage",
        amount=1500,
        linked_clause_id=None,
        has_proof=True,
    ),
]


# --------------------------------------------------------------------------- #
# 5. Deduction assessment
# --------------------------------------------------------------------------- #

print("\n--- Deduction assessment ---")
assessments = analyze.analyze_deductions(
    sample_deductions,
    agreement,
    findings=findings,
    progress_cb=lambda m: print(f"  {m}"),
)

for a in assessments:
    print(f"  [{a.risk.upper():6}] {a.deduction.label} ({a.deduction.amount})  "
          f"evidence={a.evidence_status}")
    print(f"          {a.reason}")
    if a.rule_ids:
        print(f"          rules: {', '.join(a.rule_ids)}")
    print(f"          Response: {a.suggested_response}")
    print()


# --------------------------------------------------------------------------- #
# 6. Negotiation drafts
# --------------------------------------------------------------------------- #

print("--- Negotiation drafts ---")
drafts = analyze.draft_negotiation(
    agreement,
    findings,
    deductions=assessments,
    progress_cb=lambda m: print(f"  {m}"),
)

print("\n[FRIENDLY]\n" + drafts.friendly)
print("\n[FIRM]\n" + drafts.firm)
print("\n[COMPROMISE]\n" + drafts.compromise)