# core/analyze.py
"""Three-stage lease analysis: clause findings, deduction assessment,
negotiation drafting.

Every model output is treated as a draft. These rules are enforced in
Python, not left to the prompt:

* ``quoted_text`` is always copied from ``Clause.text``.
* ``rule_ids`` are intersected with the candidate ids we sent *and* with
  the knowledge base; when nothing survives, ``evidence_status`` becomes
  ``"no_verified_rule_found"``.
* ``confidence`` is the lower of the model's rating and the clause's
  ``read_confidence``.
"""

from __future__ import annotations

import json
from typing import Callable, Iterable, Optional

from pydantic import BaseModel, Field

import gemma
from core import rules
from core.schema import (
    AgreementExtract,
    Clause,
    Deduction,
    DeductionAssessment,
    EvidenceStatus,
    Finding,
    KeyTerms,
    NegotiationDrafts,
    ReadConfidence,
    Risk,
    RuleEntry,
    TOPICS,
    Topic,
)


ProgressCb = Optional[Callable[[str], None]]

_CONFIDENCE_LEVEL: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_MAX_PROMPT_CLAUSE_CHARS = 6000


# --------------------------------------------------------------------------- #
# Model-facing response schemas
# --------------------------------------------------------------------------- #

class _ClauseTopic(BaseModel):
    clause_id: str
    topic: Topic


class _ClassificationResult(BaseModel):
    classifications: list[_ClauseTopic]


class _FindingDraft(BaseModel):
    risk: Risk
    risk_explanation: str
    why_it_matters: str
    rule_ids: list[str] = Field(default_factory=list)
    applicability_note: str | None = None
    confidence: ReadConfidence
    suggested_question: str


class _DeductionAssessmentDraft(BaseModel):
    deduction_index: int
    risk: Risk
    reason: str
    rule_ids: list[str] = Field(default_factory=list)
    suggested_response: str


class _DeductionBatch(BaseModel):
    assessments: list[_DeductionAssessmentDraft] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

_CLASSIFY_PROMPT = """You are triaging clauses from a residential lease \
agreement.

For each clause below, choose exactly ONE topic from this list:
{topics}

Use "other" only when none of the specific topics fit (for example parties,
signatures, addresses, or general boilerplate).

Clauses:
{clauses}

Return JSON with a single key "classifications": a list with one object per
clause, each having "clause_id" and "topic". Include every clause exactly once.
"""

_ANALYZE_PROMPT = """You are helping a tenant understand one clause in their \
lease agreement.

TOPIC: {topic}

CLAUSE TEXT:
\"\"\"
{clause_text}
\"\"\"

KEY TERMS FROM THE AGREEMENT:
{key_terms}

CANDIDATE RULES (ids you may cite):
{rules_block}

Instructions:
- Rate risk using these definitions:
    high   = could cause significant financial loss or loss of housing at
             short notice
    medium = unfavourable or unclear, the tenant should ask for clarification
    low    = standard and balanced
  Unfairness alone is at most medium.
- Explain in plain language what the tenant could lose or be obliged to do.
- Pick rule ids ONLY from the list provided, and only if a rule really
  relates to this clause; otherwise return an empty list.
- Never state that a clause is illegal. Use words like "may" and "could".
- If the risk depends on facts (for example rent amount, or type of premises),
  say so in applicability_note.
- Add one polite question the tenant could ask the landlord in
  suggested_question.

Return JSON matching the schema.
"""

_DEDUCTION_PROMPT = """You are helping a tenant respond to deposit \
deductions their landlord has proposed.

AGREEMENT KEY TERMS:
{key_terms}

LEASE FINDINGS RELEVANT TO DEPOSIT OR DEDUCTIONS:
{findings_block}

PROPOSED DEDUCTIONS:
{deductions_block}

CANDIDATE RULES (ids you may cite):
{rules_block}

For EACH deduction (indexed from 0 in the order listed above), decide how
contestable it is and return an object with:

- deduction_index: the index from the list above
- risk: one of
    high   = the deduction may be unjustified or excessive
    medium = the deduction is unclear or only partly justified
    low    = the deduction looks reasonable and supported
- reason: plain-language explanation of why the tenant might contest it,
  or why it looks fair. Use words like "may" and "could". Never state that
  a deduction is illegal.
- rule_ids: ONLY ids from the candidate list above, and only if a rule
  really relates to this deduction. Empty list otherwise.
- suggested_response: one or two sentences the tenant could send back to
  the landlord, in a polite tone.

If a deduction has no proof and no matching lease clause, that is worth
noting but is not by itself proof of wrongdoing.

Return JSON with a single key "assessments", one entry per deduction, in
the same order as the input.
"""

_NEGOTIATION_PROMPT = """You are drafting negotiation messages for a tenant \
to send to their landlord about their lease.

AGREEMENT KEY TERMS:
{key_terms}

LEASE FINDINGS:
{findings_block}

DEPOSIT DEDUCTION ASSESSMENTS:
{deductions_block}

Write THREE versions of the SAME underlying message, in three tones:
- friendly:   warm, collaborative, assumes good faith
- firm:       professional, clearly states the tenant's position and the ask
- compromise: offers a middle path and signals flexibility

Every version must:
- Refer to specific issues in plain language, not clause ids.
- Never state that the lease is illegal. Use "may", "could", "I would like".
- Be 3–6 sentences.
- End with a clear ask or next step.

Return JSON with exactly three keys: "friendly", "firm", "compromise".
"""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _shorten(text: str, limit: int = _MAX_PROMPT_CLAUSE_CHARS) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " […]"


def _format_key_terms(key_terms: KeyTerms) -> str:
    return json.dumps(key_terms.model_dump(), indent=2, default=str)


def _format_rules(candidates: Iterable[RuleEntry]) -> str:
    lines: list[str] = []
    for rule in candidates:
        lines.append(
            f"- id: {rule.rule_id}\n"
            f"  title: {rule.title}\n"
            f"  summary: {rule.summary}\n"
            f"  applies_when: {rule.applies_when or 'n/a'}"
        )
    return "\n".join(lines) if lines else "(no candidate rules for this topic)"


def _lower_confidence(a: ReadConfidence, b: ReadConfidence) -> ReadConfidence:
    return a if _CONFIDENCE_LEVEL[a] <= _CONFIDENCE_LEVEL[b] else b


# --------------------------------------------------------------------------- #
# Stage 1 — clause classification
# --------------------------------------------------------------------------- #

def _classify_clauses(clauses: list[Clause]) -> dict[str, Topic]:
    blocks = [f"[{c.clause_id}] {_shorten(c.text)}" for c in clauses]
    prompt = _CLASSIFY_PROMPT.format(
        topics=", ".join(TOPICS),
        clauses="\n\n".join(blocks),
    )
    result = gemma.ask_json(prompt, _ClassificationResult)

    valid_ids = {c.clause_id for c in clauses}
    mapping: dict[str, Topic] = {}
    for item in result.classifications:
        if item.clause_id in valid_ids:
            mapping[item.clause_id] = item.topic

    for c in clauses:
        mapping.setdefault(c.clause_id, "other")
    return mapping


# --------------------------------------------------------------------------- #
# Stage 2 — per-clause analysis
# --------------------------------------------------------------------------- #

def _analyze_clause(
    clause: Clause,
    key_terms: KeyTerms,
    topic: Topic,
    candidates: list[RuleEntry],
) -> Finding:
    prompt = _ANALYZE_PROMPT.format(
        topic=topic,
        clause_text=_shorten(clause.text),
        key_terms=_format_key_terms(key_terms),
        rules_block=_format_rules(candidates),
    )
    draft = gemma.ask_json(prompt, _FindingDraft)

    candidate_ids = {r.rule_id for r in candidates}
    proposed = [rid for rid in draft.rule_ids if rid in candidate_ids]
    validated = rules.validate_rule_ids(proposed)

    evidence_status: EvidenceStatus = (
        "verified_rule" if validated else "no_verified_rule_found"
    )
    confidence = _lower_confidence(draft.confidence, clause.read_confidence)

    return Finding(
        clause_id=clause.clause_id,
        quoted_text=clause.text,
        topic=topic,
        risk=draft.risk,
        risk_explanation=draft.risk_explanation,
        why_it_matters=draft.why_it_matters,
        evidence_status=evidence_status,
        rule_ids=validated,
        applicability_note=draft.applicability_note,
        confidence=confidence,
        suggested_question=draft.suggested_question,
    )


def analyze_clauses(
    extract: AgreementExtract,
    progress_cb: ProgressCb = None,
) -> list[Finding]:
    """Classify and assess every clause. Returns the surviving findings."""
    clauses = extract.clauses
    if not clauses:
        return []

    if progress_cb:
        progress_cb(f"Classifying {len(clauses)} clause(s)…")
    topic_by_clause = _classify_clauses(clauses)

    findings: list[Finding] = []
    for clause in clauses:
        topic = topic_by_clause.get(clause.clause_id, "other")

        if progress_cb:
            progress_cb(f"Analyzing clause {clause.clause_id} [{topic}]…")

        candidates = [] if topic == "other" else rules.rules_for_topic(topic)
        finding = _analyze_clause(clause, extract.key_terms, topic, candidates)

        if topic == "other" and finding.risk == "low":
            continue

        findings.append(finding)

    return findings


# --------------------------------------------------------------------------- #
# Stage 3a — deposit deduction assessment
# --------------------------------------------------------------------------- #

def analyze_deductions(
    deductions: list[Deduction],
    extract: AgreementExtract,
    findings: list[Finding] | None = None,
    progress_cb: ProgressCb = None,
) -> list[DeductionAssessment]:
    """Assess a batch of proposed deposit deductions in one model call."""
    if not deductions:
        return []

    findings = findings or []

    deposit_rules = rules.rules_for_topic("deposit")
    deduction_rules = rules.rules_for_topic("deductions")
    seen_ids: set[str] = set()
    candidates: list[RuleEntry] = []
    for r in deposit_rules + deduction_rules:
        if r.rule_id not in seen_ids:
            seen_ids.add(r.rule_id)
            candidates.append(r)

    if progress_cb:
        progress_cb(f"Assessing {len(deductions)} deduction(s)…")

    findings_block = "\n".join(
        f"- [{f.topic}] {f.risk}: {f.risk_explanation}" for f in findings
    ) or "(none)"

    deductions_block = "\n".join(
        f"[{i}] {d.label} — category={d.category}, amount={d.amount}, "
        f"proof={'yes' if d.has_proof else 'no'}"
        + (f", linked_clause={d.linked_clause_id}" if d.linked_clause_id else "")
        for i, d in enumerate(deductions)
    )

    prompt = _DEDUCTION_PROMPT.format(
        key_terms=_format_key_terms(extract.key_terms),
        findings_block=findings_block,
        deductions_block=deductions_block,
        rules_block=_format_rules(candidates),
    )

    batch = gemma.ask_json(prompt, _DeductionBatch)

    candidate_ids = {r.rule_id for r in candidates}
    by_index: dict[int, _DeductionAssessmentDraft] = {}
    for item in batch.assessments:
        if 0 <= item.deduction_index < len(deductions):
            by_index[item.deduction_index] = item

    out: list[DeductionAssessment] = []
    for i, d in enumerate(deductions):
        draft = by_index.get(i)
        if draft is None:
            out.append(
                DeductionAssessment(
                    deduction=d,
                    risk="medium",
                    reason="The model did not return an assessment for this "
                           "deduction; review it manually.",
                    rule_ids=[],
                    evidence_status="no_verified_rule_found",
                    suggested_response=(
                        "Could you send the receipts and the lease clause "
                        "this deduction is based on?"
                    ),
                )
            )
            continue

        proposed = [rid for rid in draft.rule_ids if rid in candidate_ids]
        validated = rules.validate_rule_ids(proposed)
        out.append(
            DeductionAssessment(
                deduction=d,
                risk=draft.risk,
                reason=draft.reason,
                rule_ids=validated,
                evidence_status=(
                    "verified_rule" if validated else "no_verified_rule_found"
                ),
                suggested_response=draft.suggested_response,
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Stage 3b — negotiation drafts
# --------------------------------------------------------------------------- #

def draft_negotiation(
    extract: AgreementExtract,
    findings: list[Finding],
    deductions: list[DeductionAssessment] | None = None,
    progress_cb: ProgressCb = None,
) -> NegotiationDrafts:
    """Produce friendly / firm / compromise messages covering the findings."""
    if progress_cb:
        progress_cb("Drafting negotiation messages…")

    findings_block = "\n".join(
        f"- [{f.topic}, risk={f.risk}] {f.risk_explanation}"
        + (f" (rules: {', '.join(f.rule_ids)})" if f.rule_ids else "")
        for f in findings
    ) or "(no findings)"

    deductions_block = "(none)"
    if deductions:
        deductions_block = "\n".join(
            f"- {a.deduction.label}: risk={a.risk} — {a.reason}"
            for a in deductions
        )

    prompt = _NEGOTIATION_PROMPT.format(
        key_terms=_format_key_terms(extract.key_terms),
        findings_block=findings_block,
        deductions_block=deductions_block,
    )

    return gemma.ask_json(prompt, NegotiationDrafts)