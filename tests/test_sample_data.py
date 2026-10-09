# tests/test_sample_data.py
# Simple checks that the fake demo data is complete and well formed.

from core.sample_data import SAMPLE_MARKER, get_sample_bundle, get_sample_rules
from core.schema import AnalysisBundle


def test_bundle_shape():
    bundle = get_sample_bundle()
    assert len(bundle.extract.clauses) == 8
    assert bundle.extract.clauses[0].clause_id == "C1"
    assert bundle.extract.clauses[-1].clause_id == "C8"
    assert len(bundle.findings) == 6
    assert len(bundle.gaps) == 3
    # The bundle should survive being turned into data and back again
    again = AnalysisBundle.model_validate(bundle.model_dump())
    assert again.extract.key_terms.security_deposit == 150000


def test_findings_have_all_risks_and_both_evidence_types():
    findings = get_sample_bundle().findings
    assert {f.risk for f in findings} == {"high", "medium", "low"}
    assert {f.evidence_status for f in findings} == {
        "verified_rule", "no_verified_rule_found"}
    for f in findings:
        if f.evidence_status == "no_verified_rule_found":
            assert f.rule_ids == []


def test_gaps_have_one_conflict_and_two_missing():
    gaps = get_sample_bundle().gaps
    kinds = [g.kind for g in gaps]
    assert kinds.count("conflict") == 1
    assert kinds.count("missing") == 2


def test_sample_rules_are_marked_fake():
    rules = get_sample_rules()
    ids = {r.rule_id for r in rules}
    assert ids == {"SAMPLE-1", "SAMPLE-2", "SAMPLE-3"}
    for rule in rules:
        assert SAMPLE_MARKER in rule.title