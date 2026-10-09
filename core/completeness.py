# core/completeness.py
"""Completeness and internal-consistency checks for a lease extract.

``find_gaps`` combines two kinds of checks:

Part A - plain Python, no model involved:
  * conflicts inside the extracted key terms (two different deposit amounts,
    a lock-in period that outlasts the agreement term), and
  * details the agreement never spells out (rent, deposit, notice period,
    maintenance, deposit refund timeline, inventory, registration, ...).

Part B - one model call over the clause texts that asks only for
contradictions the model can support by naming clause ids.  The model is
never allowed to break the deterministic results: if Ollama is missing or
unhappy, Part B simply returns nothing.

Every description uses neutral language.  Missing-item descriptions end with
``MISSING_NOTE``.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional, Sequence

from pydantic import BaseModel, Field

from core.schema import AgreementExtract, GapFinding, Risk

__all__ = ["find_gaps", "MISSING_NOTE"]

MISSING_NOTE = (
    "A missing detail is not automatically a legal violation, but you may "
    "want to ask for it to be written down."
)

_DEPOSIT_REFUND_HINTS = (
    "refund",
    "return",
    "repay",
    "reimburse",
    "within",
    "days",
    "deduct",
    "adjust",
)


# --------------------------------------------------------------------------- #
# Small formatting / text helpers
# --------------------------------------------------------------------------- #

def _fmt(value: Any) -> str:
    """Human-readable number for messages, e.g. 40000 -> '40,000'."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _plain(value: Any) -> str:
    """Same as ``_fmt`` but without separators, for text matching."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _distinct_amounts(values: Iterable[Any]) -> list[float]:
    """Return the distinct numeric values in ``values``, preserving order."""
    distinct: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not any(abs(number - seen) < 1e-9 for seen in distinct):
            distinct.append(number)
    return distinct


def _clause_texts(extract: AgreementExtract) -> list[str]:
    """Clause texts, falling back to full_text when nothing was extracted."""
    texts = [c.text for c in extract.clauses if c.text]
    if not texts and extract.full_text:
        texts = [extract.full_text]
    return texts


def _covers(extract: AgreementExtract, *keywords: str) -> bool:
    """True when any keyword appears (case-insensitively) in any clause."""
    if not keywords:
        return False
    for text in _clause_texts(extract):
        lowered = text.lower()
        if any(keyword in lowered for keyword in keywords):
            return True
    return False


def _clause_ids_with(extract: AgreementExtract, *keywords: str) -> list[str]:
    """Ids of the clauses whose text contains at least one keyword."""
    ids: list[str] = []
    for clause in extract.clauses:
        lowered = (clause.text or "").lower()
        if any(keyword in lowered for keyword in keywords):
            ids.append(clause.clause_id)
    return ids


def _clause_ids_mentioning(extract: AgreementExtract, amounts: Iterable[Any]) -> list[str]:
    """Ids of the clauses that literally mention one of the given amounts."""
    wanted = [_plain(amount) for amount in amounts]
    ids: list[str] = []
    for clause in extract.clauses:
        squashed = re.sub(r"[\s,]", "", clause.text or "")
        if any(value and value in squashed for value in wanted):
            ids.append(clause.clause_id)
    return ids


def _is_missing(
    value: Any,
    extract: AgreementExtract,
    keywords: Sequence[str] = (),
) -> bool:
    """A detail is missing when the extracted key term is absent, or when no
    clause text appears to cover it.

    ``keywords`` are the words that would show the agreement addresses the
    topic.  When no keywords are supplied, only the key term is checked.
    """
    if value is None:
        return True
    if not keywords:
        return False
    return not _covers(extract, *keywords)


def _has_deposit_return_timeline(extract: AgreementExtract) -> bool:
    """True when a sentence talks about returning/refunding the deposit."""
    for text in _clause_texts(extract):
        for sentence in re.split(r"[.;\n]", text.lower()):
            if "deposit" not in sentence:
                continue
            if any(hint in sentence for hint in _DEPOSIT_REFUND_HINTS):
                return True
    return False


# --------------------------------------------------------------------------- #
# Part A - conflicts between extracted key terms
# --------------------------------------------------------------------------- #

def _find_conflicts(extract: AgreementExtract) -> list[GapFinding]:
    gaps: list[GapFinding] = []
    terms = extract.key_terms

    amounts = _distinct_amounts(terms.deposit_mentions)
    if len(amounts) >= 2:
        listed = ", ".join(_fmt(amount) for amount in amounts)
        gaps.append(
            GapFinding(
                kind="conflict",
                title="More than one deposit amount is stated",
                description=(
                    f"The agreement mentions different deposit amounts "
                    f"({listed}). It is not clear from the text which figure "
                    f"applies."
                ),
                related_clause_ids=_clause_ids_mentioning(extract, amounts),
                severity="high",
            )
        )

    lock_in = terms.lock_in_months
    term = terms.agreement_term_months
    if lock_in is not None and term is not None and lock_in > term:
        gaps.append(
            GapFinding(
                kind="conflict",
                title="Lock-in period is longer than the agreement term",
                description=(
                    f"The lock-in period ({_fmt(lock_in)} months) is longer "
                    f"than the whole agreement term ({_fmt(term)} months). "
                    f"Both figures appear in the agreement, so one of them is "
                    f"likely to be wrong."
                ),
                related_clause_ids=_clause_ids_with(extract, "lock-in", "lock in"),
                severity="high",
            )
        )

    return gaps


# --------------------------------------------------------------------------- #
# Part A - missing details
# --------------------------------------------------------------------------- #

def _find_missing(extract: AgreementExtract) -> list[GapFinding]:
    terms = extract.key_terms
    gaps: list[GapFinding] = []

    def add(title: str, reason: str, clause_ids: Iterable[str] = ()) -> None:
        gaps.append(
            GapFinding(
                kind="missing",
                title=title,
                description=f"{reason} {MISSING_NOTE}",
                related_clause_ids=list(clause_ids),
                severity="medium",
            )
        )

    if _is_missing(
        terms.monthly_rent,
        extract,
        ("monthly rent", "rent payable", "per month", "rent of", "rent for"),
    ):
        add(
            "Monthly rent amount is not stated",
            "The agreement does not state a monthly rent amount.",
        )

    if _is_missing(terms.security_deposit, extract, ("security deposit", "deposit")):
        add(
            "Security deposit amount is not stated",
            "The agreement does not state a security deposit amount.",
        )

    if _is_missing(
        terms.agreement_term_months,
        extract,
        ("agreement term", "term of", "tenancy period", "lease period", "for a period of", "months"),
    ):
        add(
            "Agreement term is not stated",
            "The agreement does not state how long the tenancy is meant to last.",
        )

    if _is_missing(terms.lock_in_months, extract, ("lock-in", "lock in", "lockin")):
        add(
            "Lock-in period is not stated",
            "The agreement does not state a lock-in period.",
        )

    if _is_missing(terms.notice_period_days, extract, ("notice",)):
        add(
            "Notice period is not stated",
            "The agreement does not state how much notice either side must give.",
        )

    if _is_missing(
        terms.rent_escalation_percent,
        extract,
        ("escalat", "increase", "revision", "hike"),
    ):
        add(
            "Rent escalation is not stated",
            "The agreement does not state whether or how the rent increases.",
        )

    if not _covers(extract, "maintenance", "repair"):
        add(
            "Who pays for maintenance and repairs is not stated",
            "The agreement does not say who is responsible for maintenance and repairs.",
        )

    if not _has_deposit_return_timeline(extract):
        add(
            "Deposit return timeline is not stated",
            "The agreement does not say when or how the security deposit will "
            "be returned after the tenancy ends.",
        )

    if not _covers(extract, "inventory", "annexure", "annex", "fixtures", "fittings", "schedule of"):
        add(
            "Inventory or annexure of fittings is not mentioned",
            "The agreement does not refer to an inventory or annexure listing "
            "the fittings and items handed over.",
        )

    if not _covers(
        extract,
        "registration",
        "stamp duty",
        "stamp-duty",
        "stamped",
        "notaris",
        "notariz",
    ):
        add(
            "Registration or stamp duty is not mentioned",
            "The agreement does not mention registration or stamp duty.",
        )

    return gaps


# --------------------------------------------------------------------------- #
# Part B - one model call for clause-to-clause contradictions
# --------------------------------------------------------------------------- #

class _Contradiction(BaseModel):
    """One contradiction the model claims to have found."""

    title: str = ""
    description: str = ""
    related_clause_ids: list[str] = Field(default_factory=list)
    severity: str = "medium"


class _ContradictionReport(BaseModel):
    """Wrapper so the model always answers with a list."""

    contradictions: list[_Contradiction] = Field(default_factory=list)


_CONTRADICTION_PROMPT = """\
You are reviewing a single rental agreement for internal contradictions.

Each clause below is labelled with its clause id.

Report only contradictions that the clause text itself supports, for example
a notice period that cannot be reconciled with a lock-in period, or two
different dates, periods or amounts given for the same thing.

Rules:
1. Every contradiction must name the clause ids involved.
2. Do not report missing information, general risks, or legal opinions.
3. If you find no contradictions, return an empty list.

Clauses:
{clauses}
"""


def _clauses_block(extract: AgreementExtract) -> str:
    lines: list[str] = []
    for clause in extract.clauses:
        heading = f" - {clause.heading}" if clause.heading else ""
        lines.append(f"[{clause.clause_id}]{heading}\n{(clause.text or '').strip()}")
    return "\n\n".join(lines) or "(no clauses were extracted)"


def _normalise_severity(value: Any) -> Risk:
    text = str(value or "").strip().lower()
    if text == "high":
        return "high"
    if text == "low":
        return "low"
    return "medium"


def _find_model_contradictions(extract: AgreementExtract) -> list[GapFinding]:
    """Ask the model once whether any clauses contradict each other."""
    if not extract.clauses:
        return []

    try:
        import gemma  # imported lazily: Part A must not need Ollama
    except ImportError:
        return []

    prompt = _CONTRADICTION_PROMPT.format(clauses=_clauses_block(extract))

    try:
        report = gemma.ask_json(prompt, _ContradictionReport)
    except Exception:
        # A model/network problem must never hide the deterministic findings.
        return []

    known_ids = {clause.clause_id for clause in extract.clauses}
    gaps: list[GapFinding] = []
    for item in report.contradictions:
        clause_ids = [cid for cid in item.related_clause_ids if cid in known_ids]
        if not clause_ids:
            # Not supported by named clauses -> ignore it.
            continue

        title = item.title.strip() or "Clauses appear to contradict each other"
        description = item.description.strip() or (
            "The clauses named below appear to contradict each other."
        )
        gaps.append(
            GapFinding(
                kind="conflict",
                title=title,
                description=description,
                related_clause_ids=clause_ids,
                severity=_normalise_severity(item.severity),
            )
        )
    return gaps


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def find_gaps(extract: AgreementExtract) -> list[GapFinding]:
    """Return the conflicts and missing details found in ``extract``."""
    gaps: list[GapFinding] = []
    gaps.extend(_find_conflicts(extract))
    gaps.extend(_find_missing(extract))
    gaps.extend(_find_model_contradictions(extract))
    return gaps