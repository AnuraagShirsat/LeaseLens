# core/simulator.py
# Deposit Recovery Simulator: plain arithmetic and simple rules.
# No AI and no network are used here, so results are predictable.

import re

DISCLAIMER = (
    "This is a scenario estimate to help you prepare questions. "
    "It is not a prediction of what a court or authority would decide, "
    "and it does not say any deduction is lawful or unlawful."
)

# Words we look for in a clause for each kind of deduction.
KEYWORDS = {
    "painting_repairs": ["paint", "whitewash", "repair"],
    "damage": ["damage", "breakage"],
    "cleaning": ["clean"],
    "unpaid_rent": ["rent", "arrears"],
    "utility_dues": ["electricity", "water", "bill", "utility"],
    "other": [],
}

# The three possible results for each deduction.
SUPPORTED = "supported"
NEEDS_CLARIFICATION = "needs_clarification"
REVIEW_FURTHER = "review_further"

# Finds amounts such as Rs. 5,000 or Rs 5000 or INR 5,000 or ₹5,000.
AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE
)

# Words that suggest an amount is a limit (a cap) on deductions.
CAP_WORDS = re.compile(
    r"\b(maximum|up to|not exceed|not more than|at most|"
    r"limited to|limit|cap|capped)\b",
    re.IGNORECASE,
)


def find_cap(clause_text):
    """Return the rupee cap written in a clause, or None.

    A cap counts only if the clause has a rupee amount AND a limit word.
    If there are several amounts, the smallest one is used.
    """
    if not CAP_WORDS.search(clause_text):
        return None
    amounts = []
    for found in AMOUNT_PATTERN.findall(clause_text):
        try:
            amounts.append(float(found.replace(",", "")))
        except ValueError:
            pass  # ignore anything that is not a number
    if not amounts:
        return None
    return min(amounts)


def has_keyword(category, clause_text):
    """True if the clause text contains a keyword for this category."""
    text = clause_text.lower()
    for word in KEYWORDS.get(category, []):
        if word in text:
            return True
    return False


def classify(deduction, clause_by_id):
    """Return (status, reason) for one deduction."""
    clause = None
    if deduction.linked_clause_id:
        clause = clause_by_id.get(deduction.linked_clause_id)

    # Case 1: no clause is linked.
    if clause is None:
        if deduction.has_proof:
            return (
                NEEDS_CLARIFICATION,
                "You have proof, but no agreement clause is linked to this "
                "deduction. You may want to ask which clause allows it.",
            )
        return (
            REVIEW_FURTHER,
            "No agreement clause is linked and there is no proof. "
            "You may want to ask for both.",
        )

    # Case 2: the clause mentions a limit and the amount is above it.
    cap = find_cap(clause.text)
    if cap is not None and deduction.amount > cap:
        return (
            REVIEW_FURTHER,
            "The linked clause mentions a limit of Rs. "
            + format(cap, ",.0f")
            + " and this amount is higher. "
            "You may want to ask how the amount was worked out.",
        )

    # Case 3: a clause is linked. Check wording and proof.
    keyword_found = has_keyword(deduction.category, clause.text)
    if keyword_found and deduction.has_proof:
        return (
            SUPPORTED,
            "The linked clause mentions this kind of cost and you have "
            "proof such as bills or photos.",
        )
    if keyword_found:
        return (
            NEEDS_CLARIFICATION,
            "The linked clause mentions this kind of cost, but you have "
            "no proof yet. You may want to collect bills or photos.",
        )
    if deduction.has_proof:
        return (
            NEEDS_CLARIFICATION,
            "You have proof, but the linked clause does not clearly "
            "mention this kind of cost. You may want to ask about it.",
        )
    return (
        NEEDS_CLARIFICATION,
        "The linked clause does not clearly mention this kind of cost "
        "and there is no proof yet. You may want to ask about both.",
    )


def make_scenario(deposit, amounts):
    """Add up deductions and work out the amount returned (never below 0)."""
    total = sum(amounts)
    returned = max(0, deposit - total)
    return {"total_deducted": total, "amount_returned": returned}


def simulate(deposit, monthly_rent, deductions, clauses):
    """Run the three scenarios and return everything as a dictionary."""
    clause_by_id = {clause.clause_id: clause for clause in clauses}

    items = []
    for deduction in deductions:
        status, reason = classify(deduction, clause_by_id)
        items.append({
            "label": deduction.label,
            "category": deduction.category,
            "amount": deduction.amount,
            "linked_clause_id": deduction.linked_clause_id,
            "has_proof": deduction.has_proof,
            "status": status,
            "reason": reason,
        })

    supported = [i["amount"] for i in items if i["status"] == SUPPORTED]
    unclear = [
        i["amount"] for i in items if i["status"] == NEEDS_CLARIFICATION
    ]
    everything = [i["amount"] for i in items]

    if monthly_rent and monthly_rent > 0:
        months = round(deposit / monthly_rent, 1)
    else:
        months = None

    return {
        "deposit": deposit,
        "monthly_rent": monthly_rent,
        "deposit_months_of_rent": months,
        "items": items,
        "scenarios": {
            "tenant_favourable": make_scenario(deposit, supported),
            "middle": make_scenario(deposit, supported + unclear),
            "as_proposed": make_scenario(deposit, everything),
        },
    }