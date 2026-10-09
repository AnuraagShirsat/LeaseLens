"""
eval/run_eval.py

Measures how well LeaseLens finds the issues we planted in the four mock agreements.

For every folder in eval/cases/ (case1, case2, ...) it:
  1. loads the page images (png or jpg) in file-name order,
  2. reads expected.txt (lines like:  topic | short description),
  3. runs the real analysis (core.pipeline.run_analysis),
  4. measures five things (see the results table),
  5. writes eval/results.md and prints the table.

How to run (Ollama app must be open, (.venv) showing, from the project folder):
    python eval/run_eval.py

This can take several minutes because Gemma reads every page.
"""

import io
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

# The project folder is the folder above eval/. We add it to Python's search
# path so "import core..." and "import config" work from here.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES_DIR = ROOT / "eval" / "cases"
RESULTS_FILE = ROOT / "eval" / "results.md"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
GAP_KINDS = ("conflict", "missing")  # expected "topics" that mean a gap, not a clause


class NamedBytes(io.BytesIO):
    """An in-memory file with a name, like the files Streamlit gives us on upload."""

    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


def natural_key(path):
    """Sort page2 before page10 (plain sorting would put page10 first)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def normalize(text):
    """Make text easy to compare: one space between words, ignore capital letters."""
    return " ".join(str(text).split()).casefold()


def percent(part, whole):
    """Turn two numbers into a friendly percentage, e.g. '75% (3/4)'."""
    if whole == 0:
        return "n/a (0)"
    return str(round(100 * part / whole)) + "% (" + str(part) + "/" + str(whole) + ")"


def read_expected(path):
    """Read expected.txt. Returns a list of (topic, description)."""
    issues = []
    text = path.read_text(encoding="utf-8-sig")  # utf-8-sig also copes with a Notepad BOM
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # The real file uses the bar character; a normal | is accepted too.
        if "\u2502" in line:
            parts = line.split("\u2502", 1)
        elif "|" in line:
            parts = line.split("|", 1)
        else:
            print("  Warning: ignoring a line without a bar in " + str(path.name) + ": " + line)
            continue
        issues.append((parts[0].strip().lower(), parts[1].strip()))
    return issues


def load_rule_ids(kb_path):
    """Read the knowledge base and return the set of all rule_id values."""
    with open(kb_path, encoding="utf-8") as f:
        data = json.load(f)
    return {rule["rule_id"] for rule in data["rules"] if "rule_id" in rule}


def get_page_images(image_paths, load_pages):
    """Turn image files into PNG bytes using Member 1's load_pages."""
    # First try giving it plain file paths.
    try:
        return load_pages([str(p) for p in image_paths])
    except Exception:
        pass
    # If that did not work, give it in-memory files (like a Streamlit upload).
    files = [NamedBytes(p.read_bytes(), p.name) for p in image_paths]
    return load_pages(files)


def evaluate_case(case_dir, kb_ids, run_analysis, load_pages):
    """Run one case. Returns a dictionary of results, or None if the case is unusable."""
    expected_file = case_dir / "expected.txt"
    image_paths = sorted(
        [p for p in case_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES],
        key=natural_key,
    )
    if not expected_file.exists():
        print("  Skipping " + case_dir.name + ": no expected.txt")
        return None
    if not image_paths:
        print("  Skipping " + case_dir.name + ": no page images (.png or .jpg)")
        return None

    expected = read_expected(expected_file)
    result = {"name": case_dir.name, "error": None, "expected_total": len(expected),
              "detected_total": 0, "missed": [], "quotes_total": 0, "quotes_ok": 0,
              "cites_total": 0, "cites_ok": 0, "unexpected_high": 0, "seconds": 0.0}

    print("  Reading " + str(len(image_paths)) + " page image(s) and analysing ...")
    start = time.perf_counter()
    try:
        pages = get_page_images(image_paths, load_pages)
        bundle = run_analysis(pages, progress_cb=None)
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        result["seconds"] = time.perf_counter() - start
        result["missed"] = [t + " | " + d + "  (analysis failed)" for t, d in expected]
        return result
    result["seconds"] = time.perf_counter() - start

    findings = list(bundle.findings)
    gaps = list(bundle.gaps)

    # 1. Planted issue detection.
    for topic, description in expected:
        if topic in GAP_KINDS:
            found = any(gap.kind == topic for gap in gaps)
        else:
            found = any(f.topic == topic and f.risk in ("medium", "high") for f in findings)
        if found:
            result["detected_total"] += 1
        else:
            result["missed"].append(topic + " | " + description)

    # 2. Quote accuracy: is each quote really inside the text that was read?
    full_text = normalize(bundle.extract.full_text)
    for f in findings:
        result["quotes_total"] += 1
        if normalize(f.quoted_text) and normalize(f.quoted_text) in full_text:
            result["quotes_ok"] += 1

    # 3. Citation validity: does every cited rule id exist in the knowledge base?
    for f in findings:
        for rule_id in f.rule_ids:
            result["cites_total"] += 1
            if rule_id in kb_ids:
                result["cites_ok"] += 1

    # 4. Unexpected high-risk findings (topics we did not plant an issue in).
    expected_topics = {t for t, _ in expected if t not in GAP_KINDS}
    for f in findings:
        if f.risk == "high" and f.topic not in expected_topics:
            result["unexpected_high"] += 1

    return result


def build_table(results):
    """Build the Markdown table text, one row per case plus an overall row."""
    lines = [
        "| Case | Planted issues found | Quote accuracy | Citation validity | Unexpected high-risk findings | Seconds |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    good = [r for r in results if r["error"] is None]
    for r in results:
        if r["error"] is not None:
            lines.append("| " + r["name"] + " | ERROR | ERROR | ERROR | ERROR | " + str(round(r["seconds"])) + " |")
        else:
            lines.append("| " + r["name"]
                         + " | " + str(r["detected_total"]) + "/" + str(r["expected_total"])
                         + " | " + percent(r["quotes_ok"], r["quotes_total"])
                         + " | " + percent(r["cites_ok"], r["cites_total"])
                         + " | " + str(r["unexpected_high"])
                         + " | " + str(round(r["seconds"])) + " |")

    # Overall row (only cases that ran without errors).
    det = sum(r["detected_total"] for r in good)
    exp = sum(r["expected_total"] for r in good)
    qok = sum(r["quotes_ok"] for r in good)
    qtot = sum(r["quotes_total"] for r in good)
    cok = sum(r["cites_ok"] for r in good)
    ctot = sum(r["cites_total"] for r in good)
    unexpected = sum(r["unexpected_high"] for r in good)
    average = round(sum(r["seconds"] for r in good) / len(good)) if good else 0
    lines.append("| **Overall** | **" + str(det) + "/" + str(exp) + "** | **" + percent(qok, qtot)
                 + "** | **" + percent(cok, ctot) + "** | **" + str(unexpected)
                 + "** | **" + str(average) + " (average)** |")
    return "\n".join(lines)


def main():
    # Import the team's code here so we can show a friendly message if it is missing.
    try:
        import config
        from core.pipeline import run_analysis
        from core.pdf_images import load_pages
    except ImportError as error:
        print("PROBLEM: I could not load the project code: " + str(error))
        print("Is core/pipeline.py merged into your branch yet? Use Branch > Update from main in")
        print("GitHub Desktop, make sure (.venv) shows, and run: pip install -r requirements.txt")
        return 1

    # Load the knowledge base rule ids.
    kb_path = Path(config.KB_PATH)
    if not kb_path.is_absolute():
        kb_path = ROOT / kb_path
    try:
        kb_ids = load_rule_ids(kb_path)
    except Exception as error:
        print("PROBLEM: I could not read the knowledge base at " + str(kb_path) + ": " + str(error))
        print("Run: python kb/validate_kb.py")
        return 1

    if not CASES_DIR.exists():
        print("PROBLEM: the folder " + str(CASES_DIR) + " does not exist.")
        return 1

    case_dirs = sorted([p for p in CASES_DIR.iterdir() if p.is_dir()], key=natural_key)
    if not case_dirs:
        print("PROBLEM: there are no case folders inside " + str(CASES_DIR))
        return 1

    print("Knowledge base has " + str(len(kb_ids)) + " rules. Found " + str(len(case_dirs)) + " case folder(s).")
    print("If Gemma is slow this can take several minutes.")
    print()

    results = []
    for case_dir in case_dirs:
        print("Case: " + case_dir.name)
        result = evaluate_case(case_dir, kb_ids, run_analysis, load_pages)
        if result is not None:
            results.append(result)
            if result["error"]:
                print("  FAILED: " + result["error"])
            else:
                print("  Done in " + str(round(result["seconds"])) + " seconds.")
        print()

    if not results:
        print("No usable cases were found, so there is nothing to measure.")
        return 1

    table = build_table(results)

    # List every missed issue (also saved in the results file).
    missed_lines = []
    for r in results:
        for item in r["missed"]:
            missed_lines.append("- " + r["name"] + ": " + item)

    text = "# LeaseLens evaluation results\n\n"
    text += "Run on " + date.today().isoformat() + " with " + str(len(results)) + " mock agreements.\n\n"
    text += table + "\n\n"
    text += "## Issues that were missed\n\n"
    text += ("\n".join(missed_lines) if missed_lines else "None.") + "\n\n"
    text += ("Notes: a planted issue counts as found when the AI gave a medium or high risk finding on that topic, "
             "or a gap of the same kind (conflict or missing). Quote accuracy ignores capital letters and extra spaces. "
             "Small test set: four fictional agreements.\n")
    RESULTS_FILE.write_text(text, encoding="utf-8")

    print(table)
    print()
    print("Issues that were missed:")
    print("\n".join(missed_lines) if missed_lines else "None.")
    print()
    print("Saved to " + str(RESULTS_FILE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
