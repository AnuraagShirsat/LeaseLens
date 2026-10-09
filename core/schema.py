# core/schema.py
"""Pydantic v2 schemas for lease analysis and negotiation data."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

TOPICS = [
    "deposit",
    "deductions",
    "lock_in",
    "termination_notice",
    "rent_escalation",
    "maintenance_repairs",
    "entry_inspection",
    "subletting",
    "registration_stamp",
    "utilities",
    "eviction",
    "renewal",
    "other",
]

Topic = Literal[
    "deposit",
    "deductions",
    "lock_in",
    "termination_notice",
    "rent_escalation",
    "maintenance_repairs",
    "entry_inspection",
    "subletting",
    "registration_stamp",
    "utilities",
    "eviction",
    "renewal",
    "other",
]

Number = int | float
ReadConfidence = Literal["high", "medium", "low"]
Risk = Literal["high", "medium", "low"]
RuleType = Literal["legal_requirement", "contract_guidance", "best_practice"]
EvidenceStatus = Literal["verified_rule", "no_verified_rule_found"]
GapKind = Literal["conflict", "missing"]


class Clause(BaseModel):
    """A single extracted lease clause."""

    clause_id: str
    heading: str | None = None
    text: str
    page: int
    read_confidence: ReadConfidence
    read_note: str | None = None


class KeyTerms(BaseModel):
    """Important numeric and named terms from the agreement."""

    monthly_rent: Number | None = None
    security_deposit: Number | None = None
    agreement_term_months: Number | None = None
    lock_in_months: Number | None = None
    notice_period_days: Number | None = None
    rent_escalation_percent: Number | None = None
    start_date: str | None = None
    landlord_name: str | None = None
    tenant_name: str | None = None
    deposit_mentions: list[Number] = Field(default_factory=list)


class AgreementExtract(BaseModel):
    """Full structured extraction from a lease agreement."""

    clauses: list[Clause]
    key_terms: KeyTerms
    full_text: str
    page_count: int


class RuleEntry(BaseModel):
    """A rule or guidance entry used to evaluate lease clauses."""

    rule_id: str
    title: str
    rule_type: RuleType
    source_name: str
    source_url: str | None = None
    section: str | None = None
    summary: str
    applies_when: str | None = None
    topics: list[Topic]
    date_checked: str


class Finding(BaseModel):
    """A risk or issue found in a clause."""

    clause_id: str
    quoted_text: str
    topic: Topic
    risk: Risk
    risk_explanation: str
    why_it_matters: str
    evidence_status: EvidenceStatus
    rule_ids: list[str] = Field(default_factory=list)
    applicability_note: str | None = None
    confidence: ReadConfidence
    suggested_question: str


class GapFinding(BaseModel):
    """A conflict or missing item across the agreement."""

    kind: GapKind
    title: str
    description: str
    related_clause_ids: list[str] = Field(default_factory=list)
    severity: Risk


class AnalysisBundle(BaseModel):
    """Bundle containing extraction, findings, and gaps."""

    extract: AgreementExtract
    findings: list[Finding]
    gaps: list[GapFinding]
    created_at: str


class Deduction(BaseModel):
    """A proposed or observed deposit deduction."""

    label: str
    category: str
    amount: Number
    linked_clause_id: str | None = None
    has_proof: bool


class NegotiationDrafts(BaseModel):
    """Three tones of negotiation message."""

    friendly: str
    firm: str
    compromise: str


def to_json_file(bundle: AnalysisBundle, path: str | Path) -> None:
    """Write an AnalysisBundle to a JSON file."""
    Path(path).write_text(bundle.model_dump_json(indent=2), encoding="utf-8")


def from_json_file(path: str | Path) -> AnalysisBundle:
    """Read an AnalysisBundle from a JSON file."""
    return AnalysisBundle.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )