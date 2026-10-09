# core/rules.py
"""Knowledge base loader for lease rules and guidance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

import config
from core.schema import RuleEntry


class RulesError(Exception):
    """Raised when the knowledge base can't be loaded or is invalid."""


_RULES: list[RuleEntry] = []
_BY_ID: dict[str, RuleEntry] = {}
_BY_TOPIC: dict[str, list[RuleEntry]] = {}
_LOADED: bool = False


def _reset_cache() -> None:
    global _RULES, _BY_ID, _BY_TOPIC, _LOADED
    _RULES = []
    _BY_ID = {}
    _BY_TOPIC = {}
    _LOADED = False


def load_rules(path: str | Path | None = None) -> list[RuleEntry]:
    if path is None:
        path = config.KB_PATH
    p = Path(path)

    if not p.exists():
        raise RulesError(f"Knowledge base not found: {p}")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RulesError(f"Knowledge base is not valid JSON ({p}): {e}") from e

    if not isinstance(raw, dict) or "rules" not in raw:
        raise RulesError(
            f"Knowledge base must be a JSON object with a 'rules' key: {p}"
        )

    entries = raw["rules"]
    if not isinstance(entries, list):
        raise RulesError(f"'rules' must be a list in {p}")

    rules: list[RuleEntry] = []
    seen: set[str] = set()

    for i, entry in enumerate(entries):
        rule_id_hint: str | None = None
        if isinstance(entry, dict):
            raw_id = entry.get("rule_id")
            if isinstance(raw_id, str):
                rule_id_hint = raw_id

        try:
            rule = RuleEntry.model_validate(entry)
        except ValidationError as e:
            label = rule_id_hint or f"index {i}"
            raise RulesError(
                f"Invalid rule entry ({label}) in {p}: {e}"
            ) from e

        if rule.rule_id in seen:
            raise RulesError(f"Duplicate rule_id '{rule.rule_id}' in {p}")
        seen.add(rule.rule_id)
        rules.append(rule)

    global _RULES, _BY_ID, _BY_TOPIC, _LOADED
    _RULES = rules
    _BY_ID = {r.rule_id: r for r in rules}

    by_topic: dict[str, list[RuleEntry]] = {}
    for r in rules:
        for t in r.topics:
            by_topic.setdefault(t, []).append(r)
    _BY_TOPIC = by_topic
    _LOADED = True

    return rules


def _ensure_loaded() -> None:
    if not _LOADED:
        load_rules()


def rules_for_topic(topic: str) -> list[RuleEntry]:
    _ensure_loaded()
    return list(_BY_TOPIC.get(topic, []))


def get_rule(rule_id: str) -> RuleEntry | None:
    _ensure_loaded()
    return _BY_ID.get(rule_id)


def validate_rule_ids(ids: Iterable[str]) -> list[str]:
    _ensure_loaded()
    return [i for i in ids if i in _BY_ID]


def all_rules() -> list[RuleEntry]:
    _ensure_loaded()
    return list(_RULES)