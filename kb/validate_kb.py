"""
kb/validate_kb.py

Checks kb/karnataka_rules.json for mistakes before the app uses it.

How to run (from the project folder, with (.venv) showing):
    python kb/validate_kb.py

Exit code: 0 = no problems found, 1 = problems found (or the file could not be read).

NOTE: this program checks the FORMAT of the rules. It cannot check that a rule
is TRUE. You still have to compare each rule with the official page yourself.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# The rules file sits in the same folder as this script, so this works
# no matter which folder you run the command from.
KB_FILE = Path(__file__).resolve().parent / "karnataka_rules.json"

# Every rule must have all of these fields.
REQUIRED_FIELDS = [
    "rule_id",
    "title",
    "rule_type",
    "source_name",
    "source_url",
    "section",
    "summary",
    "applies_when",
    "topics",
    "date_checked",
]

# Text fields that must not be empty. (source_url may be empty for best practices.)
NON_EMPTY_TEXT_FIELDS = [
    "rule_id",
    "title",
    "source_name",
    "section",
    "summary",
    "applies_when",
]

ALLOWED_RULE_TYPES = ["legal_requirement", "contract_guidance", "best_practice"]

ALLOWED_TOPICS = [
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

# These rule types must always have an official link.
TYPES_NEEDING_URL = ["legal_requirement", "contract_guidance"]

MAX_SUMMARY_WORDS = 80


def looks_like_date(text):
    """True if text is a real date written like 2026-10-09 (year-month-day)."""
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def check_rule(rule, position):
    """Check ONE rule. Returns (label, list_of_problem_texts)."""
    problems = []

    # The rule must be a JSON object (curly braces), not something else.
    if not isinstance(rule, dict):
        return "entry number " + str(position), ["this entry is not a { ... } object"]

    # Use the rule_id as the label so each problem is easy to find.
    rule_id = rule.get("rule_id")
    if isinstance(rule_id, str) and rule_id.strip():
        label = rule_id.strip()
    else:
        label = "entry number " + str(position)

    # 1. All fields present.
    for field in REQUIRED_FIELDS:
        if field not in rule:
            problems.append("missing field '" + field + "'")

    # 2. Text fields must be text, and most must not be empty.
    for field in NON_EMPTY_TEXT_FIELDS + ["rule_type", "source_url", "date_checked"]:
        if field in rule and not isinstance(rule[field], str):
            problems.append("field '" + field + "' must be text in quotes")
    for field in NON_EMPTY_TEXT_FIELDS:
        value = rule.get(field)
        if isinstance(value, str) and not value.strip():
            problems.append("field '" + field + "' is empty")

    # 3. rule_type must be one of the three allowed values.
    rule_type = rule.get("rule_type")
    if isinstance(rule_type, str) and rule_type not in ALLOWED_RULE_TYPES:
        problems.append(
            "rule_type '" + rule_type + "' is not allowed (use one of: "
            + ", ".join(ALLOWED_RULE_TYPES) + ")"
        )

    # 4. topics must be a non-empty list, and every topic must be allowed.
    topics = rule.get("topics")
    if "topics" in rule:
        if not isinstance(topics, list) or len(topics) == 0:
            problems.append("topics must be a list with at least one topic")
        else:
            for topic in topics:
                if topic not in ALLOWED_TOPICS:
                    problems.append("topic '" + str(topic) + "' is not an allowed topic")

    # 5. date_checked must be filled in and look like a date.
    date_checked = rule.get("date_checked")
    if isinstance(date_checked, str):
        if date_checked.strip().upper() == "FILL IN":
            problems.append(
                "date_checked is still \"FILL IN\" (type the date you checked it, like 2026-10-09)"
            )
        elif not looks_like_date(date_checked.strip()):
            problems.append(
                "date_checked '" + date_checked + "' does not look like a date (use 2026-10-09 style)"
            )

    # 6. source_url: if present it must start with https://
    #    and legal_requirement / contract_guidance rules must have one.
    source_url = rule.get("source_url")
    if isinstance(source_url, str):
        url = source_url.strip()
        if url and not url.startswith("https://"):
            problems.append("source_url must start with https://")
        if not url and rule_type in TYPES_NEEDING_URL:
            problems.append("source_url is required for rule_type '" + rule_type + "'")

    # 7. Summary must not be longer than 80 words.
    summary = rule.get("summary")
    if isinstance(summary, str):
        word_count = len(summary.split())
        if word_count > MAX_SUMMARY_WORDS:
            problems.append(
                "summary has " + str(word_count) + " words (maximum is " + str(MAX_SUMMARY_WORDS) + ")"
            )

    return label, problems


def main():
    print("Checking " + KB_FILE.name + " ...")
    print()

    # Load the file, with friendly messages if something is wrong.
    if not KB_FILE.exists():
        print("PROBLEM: the file " + str(KB_FILE) + " was not found.")
        return 1
    try:
        with open(KB_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as error:
        print("PROBLEM: the file is not valid JSON.")
        print("  The computer got confused at line " + str(error.lineno)
              + ", column " + str(error.colno) + ": " + error.msg)
        print("  Usual causes: a missing comma between two rules, an extra comma")
        print("  after the last rule, or a missing quote mark.")
        return 1

    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        print('PROBLEM: the file must look like {"rules": [ ... ]}.')
        return 1

    rules = data["rules"]
    all_problems = []  # list of (label, text)
    seen_ids = {}      # rule_id -> how many times we saw it
    topics_covered = set()

    for position, rule in enumerate(rules, start=1):
        label, problems = check_rule(rule, position)
        for text in problems:
            all_problems.append((label, text))

        # Count rule_ids so we can find duplicates.
        if isinstance(rule, dict) and isinstance(rule.get("rule_id"), str):
            rid = rule["rule_id"].strip()
            seen_ids[rid] = seen_ids.get(rid, 0) + 1

        # Remember which topics have at least one rule.
        if isinstance(rule, dict) and isinstance(rule.get("topics"), list):
            for topic in rule["topics"]:
                if topic in ALLOWED_TOPICS:
                    topics_covered.add(topic)

    # 8. rule_id must be unique.
    for rid, count in seen_ids.items():
        if count > 1:
            all_problems.append((rid, "rule_id is used " + str(count) + " times (it must be unique)"))

    # Print every problem with its rule_id.
    if all_problems:
        print("PROBLEMS FOUND:")
        for label, text in all_problems:
            print("  [" + label + "] " + text)
        print()

    # Topics with no rule at all.
    missing_topics = [t for t in ALLOWED_TOPICS if t not in topics_covered]

    print("Rules checked: " + str(len(rules)))
    print("Problems found: " + str(len(all_problems)))
    if missing_topics:
        print("Topics with no rule at all: " + ", ".join(missing_topics))
    else:
        print("Topics with no rule at all: none")
    print()

    if all_problems:
        print("RESULT: FAILED - fix the problems above and run this again.")
        return 1

    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
