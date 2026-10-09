"""Tests for core.rules — loads a tiny fake knowledge base."""

from pathlib import Path

import pytest

from core import rules
from core.rules import RulesError

SAMPLE = Path(__file__).parent.parent / "kb" / "sample_rules.json"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _fresh_cache():
    """Reset the module cache before each test so tests don't leak state."""
    rules._reset_cache()
    yield
    rules._reset_cache()


@pytest.fixture
def loaded():
    """Load the sample KB and yield the rule list."""
    return rules.load_rules(SAMPLE)


# --------------------------------------------------------------------------- #
# load_rules
# --------------------------------------------------------------------------- #

def test_load_rules_returns_entries(loaded):
    assert len(loaded) == 2
    assert {r.rule_id for r in loaded} == {"SAMPLE-001", "SAMPLE-002"}
    assert all(r.title.startswith("SAMPLE - NOT A REAL RULE") for r in loaded)


def test_load_rules_missing_file_raises_clear_error(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(RulesError, match="not found"):
        rules.load_rules(missing)


def test_load_rules_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(RulesError, match="not valid JSON"):
        rules.load_rules(bad)


def test_load_rules_missing_rules_key_raises(tmp_path):
    bad = tmp_path / "no_rules.json"
    bad.write_text('{"items": []}', encoding="utf-8")
    with pytest.raises(RulesError, match="'rules' key"):
        rules.load_rules(bad)


def test_load_rules_rules_not_a_list_raises(tmp_path):
    bad = tmp_path / "not_list.json"
    bad.write_text('{"rules": "oops"}', encoding="utf-8")
    with pytest.raises(RulesError, match="must be a list"):
        rules.load_rules(bad)


def test_load_rules_invalid_entry_names_the_rule_id(tmp_path):
    bad = tmp_path / "bad_entry.json"
    bad.write_text(
        '{"rules": [{"rule_id": "BROKEN-42", "title": "x"}]}',
        encoding="utf-8",
    )
    with pytest.raises(RulesError, match="BROKEN-42"):
        rules.load_rules(bad)


def test_load_rules_duplicate_rule_id_raises(tmp_path):
    dup = tmp_path / "dup.json"
    dup.write_text(
        """
        {"rules": [
          {"rule_id": "DUP", "title": "a", "rule_type": "best_practice",
           "source_name": "s", "summary": "x", "topics": ["deposit"],
           "date_checked": "2026-01-01"},
          {"rule_id": "DUP", "title": "b", "rule_type": "best_practice",
           "source_name": "s", "summary": "y", "topics": ["deposit"],
           "date_checked": "2026-01-01"}
        ]}
        """,
        encoding="utf-8",
    )
    with pytest.raises(RulesError, match="Duplicate rule_id 'DUP'"):
        rules.load_rules(dup)


# --------------------------------------------------------------------------- #
# rules_for_topic
# --------------------------------------------------------------------------- #

def test_rules_for_topic_matches(loaded):
    deposit_rules = rules.rules_for_topic("deposit")
    assert [r.rule_id for r in deposit_rules] == ["SAMPLE-001"]

    notice_rules = rules.rules_for_topic("termination_notice")
    assert [r.rule_id for r in notice_rules] == ["SAMPLE-002"]

    lock_in_rules = rules.rules_for_topic("lock_in")
    assert [r.rule_id for r in lock_in_rules] == ["SAMPLE-002"]


def test_rules_for_topic_unknown_returns_empty(loaded):
    assert rules.rules_for_topic("eviction") == []


def test_rules_for_topic_returns_a_copy(loaded):
    first = rules.rules_for_topic("deposit")
    first.clear()
    second = rules.rules_for_topic("deposit")
    assert len(second) == 1  # cache not mutated by caller


# --------------------------------------------------------------------------- #
# get_rule
# --------------------------------------------------------------------------- #

def test_get_rule_hit_and_miss(loaded):
    r = rules.get_rule("SAMPLE-001")
    assert r is not None
    assert r.title.startswith("SAMPLE - NOT A REAL RULE")
    assert rules.get_rule("NOPE-999") is None


# --------------------------------------------------------------------------- #
# validate_rule_ids
# --------------------------------------------------------------------------- #

def test_validate_rule_ids_filters_and_preserves_order(loaded):
    result = rules.validate_rule_ids(["SAMPLE-002", "MISSING", "SAMPLE-001"])
    assert result == ["SAMPLE-002", "SAMPLE-001"]


def test_validate_rule_ids_all_missing(loaded):
    assert rules.validate_rule_ids(["a", "b"]) == []


def test_validate_rule_ids_empty(loaded):
    assert rules.validate_rule_ids([]) == []


# --------------------------------------------------------------------------- #
# Lazy loading
# --------------------------------------------------------------------------- #

def test_lookup_lazily_loads_default_path(monkeypatch):
    """If the cache is empty, lookups load from config.KB_PATH automatically."""
    monkeypatch.setattr(rules.config, "KB_PATH", SAMPLE, raising=True)

    # No explicit load_rules() call:
    r = rules.get_rule("SAMPLE-001")
    assert r is not None
    assert rules.rules_for_topic("deposit")[0].rule_id == "SAMPLE-001"