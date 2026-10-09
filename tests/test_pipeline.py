# tests/test_pipeline.py
"""Tests for core.pipeline with all model calls mocked out."""

from __future__ import annotations

import json

import pytest

from core import pipeline, schema


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
def _sample_extract() -> schema.AgreementExtract:
    return schema.AgreementExtract(
        clauses=[
            schema.Clause(
                clause_id="c1",
                heading="Security Deposit",
                text="Tenant shall pay a security deposit of Rs 100,000.",
                page=1,
                read_confidence="high",
            )
        ],
        key_terms=schema.KeyTerms(monthly_rent=20000, security_deposit=100000),
        full_text="Tenant shall pay a security deposit of Rs 100,000.",
        page_count=1,
    )


def _sample_finding() -> schema.Finding:
    return schema.Finding(
        clause_id="c1",
        quoted_text="security deposit of Rs 100,000",
        topic="deposit",
        risk="medium",
        risk_explanation="Deposit exceeds the usual ceiling.",
        why_it_matters="You may struggle to recover the full amount.",
        evidence_status="verified_rule",
        rule_ids=["r1"],
        confidence="high",
        suggested_question="Can the deposit be reduced?",
    )


def _sample_gap() -> schema.GapFinding:
    return schema.GapFinding(
        kind="missing",
        title="No notice period stated",
        description="The agreement does not state a termination notice period.",
        severity="medium",
    )


@pytest.fixture
def isolated_result_path(tmp_path, monkeypatch):
    """Point config.LAST_RESULT_PATH at a tmp file."""
    target = tmp_path / "last_result.json"
    monkeypatch.setattr(pipeline.config, "LAST_RESULT_PATH", target)
    return target


@pytest.fixture
def fake_stages(monkeypatch):
    """Replace the three stage functions with recording mocks."""
    calls: dict[str, list] = {"extract": [], "analyze": [], "gaps": []}

    def fake_extract(page_images, progress_cb):
        calls["extract"].append((list(page_images), progress_cb))
        if progress_cb is not None:
            progress_cb(0.5, "extract half")
            progress_cb(1.0, "extract done")
        return _sample_extract()

    def fake_analyze(extract, progress_cb):
        calls["analyze"].append((extract, progress_cb))
        if progress_cb is not None:
            progress_cb(0.5, "analyze half")
            progress_cb(1.0, "analyze done")
        return [_sample_finding()]

    def fake_find_gaps(extract):
        calls["gaps"].append(extract)
        return [_sample_gap()]

    monkeypatch.setattr(pipeline, "extract_agreement", fake_extract)
    monkeypatch.setattr(pipeline, "analyze_clauses", fake_analyze)
    monkeypatch.setattr(pipeline, "find_gaps", fake_find_gaps)
    return calls


# --------------------------------------------------------------------------- #
# run_analysis
# --------------------------------------------------------------------------- #
def test_run_analysis_happy_path(isolated_result_path, fake_stages):
    bundle = pipeline.run_analysis(["page1.png"])

    assert isinstance(bundle, schema.AnalysisBundle)
    assert bundle.extract.clauses[0].clause_id == "c1"
    assert len(bundle.findings) == 1
    assert len(bundle.gaps) == 1
    assert isinstance(bundle.created_at, str) and bundle.created_at

    # Saved to disk and reloadable.
    assert isolated_result_path.exists()
    reloaded = schema.from_json_file(isolated_result_path)
    assert reloaded == bundle

    # Each stage was called once with the expected arguments.
    assert len(fake_stages["extract"]) == 1
    assert fake_stages["extract"][0][0] == ["page1.png"]
    assert len(fake_stages["analyze"]) == 1
    assert len(fake_stages["gaps"]) == 1


def test_run_analysis_reports_progress_in_order(isolated_result_path, fake_stages):
    events: list[tuple[float, str]] = []

    def cb(fraction, message):
        events.append((float(fraction), message))

    pipeline.run_analysis(["page1.png"], progress_cb=cb)

    fractions = [f for f, _ in events]

    # Monotonic, starts at 0, ends at 1.
    assert fractions[0] == pytest.approx(0.0)
    assert fractions[-1] == pytest.approx(1.0)
    assert fractions == sorted(fractions)

    # Exact stage boundaries with the mocked 0.5/1.0 stage callbacks.
    expected = [
        0.0,      # start
        0.20,     # extract  @ 0.5
        0.40,     # extract  @ 1.0  (also the boundary _notify)
        0.40,     # "Checking clauses…"
        0.625,    # analyze  @ 0.5
        0.85,     # analyze  @ 1.0  (also the boundary _notify)
        0.85,     # "Looking for gaps…"
        1.0,      # "Finishing up…"
        1.0,      # "Done."
    ]
    assert fractions == pytest.approx(expected)

    # And per-stage ranges, if you prefer range checks over exact values.
    # A small tolerance absorbs floating-point drift from
    # ``EXTRACT_SHARE + ANALYZE_SHARE`` landing a hair above the literal 0.85.
    tol = 1e-9
    extract_cbs = [fractions[1], fractions[2]]
    analyze_cbs = [fractions[4], fractions[5]]
    assert all(0.0 - tol <= f <= 0.40 + tol for f in extract_cbs)
    assert all(0.40 - tol <= f <= 0.85 + tol for f in analyze_cbs)
    assert fractions[-1] == pytest.approx(1.0)


def test_run_analysis_progress_is_optional(isolated_result_path, fake_stages):
    # No callback at all -> should still work.
    bundle = pipeline.run_analysis(["page1.png"], progress_cb=None)
    assert bundle.extract.page_count == 1


def test_run_analysis_progress_callback_with_single_arg(isolated_result_path, fake_stages):
    seen: list[float] = []

    def cb(fraction):  # only one positional argument
        seen.append(fraction)

    pipeline.run_analysis(["page1.png"], progress_cb=cb)
    assert seen and seen[-1] == 1.0


def test_run_analysis_wraps_gemma_error(isolated_result_path, monkeypatch):
    def boom(page_images, progress_cb):
        raise pipeline.GemmaError("model exploded")

    monkeypatch.setattr(pipeline, "extract_agreement", boom)

    with pytest.raises(pipeline.PipelineError) as excinfo:
        pipeline.run_analysis(["page1.png"])

    message = str(excinfo.value)
    assert "clearer scan" in message or "couldn't read" in message
    # The original exception is chained for debugging.
    assert isinstance(excinfo.value.__cause__, pipeline.GemmaError)

    # Nothing was written on failure.
    assert not isolated_result_path.exists()


def test_run_analysis_wraps_unexpected_errors(isolated_result_path, monkeypatch):
    def boom(page_images, progress_cb):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(pipeline, "extract_agreement", boom)

    with pytest.raises(pipeline.PipelineError):
        pipeline.run_analysis(["page1.png"])


# --------------------------------------------------------------------------- #
# load_last_result
# --------------------------------------------------------------------------- #
def test_load_last_result_missing_file(isolated_result_path):
    assert not isolated_result_path.exists()
    assert pipeline.load_last_result() is None


def test_load_last_result_roundtrip(isolated_result_path, fake_stages):
    written = pipeline.run_analysis(["page1.png"])
    loaded = pipeline.load_last_result()
    assert loaded == written


def test_load_last_result_corrupt_json(isolated_result_path):
    isolated_result_path.write_text("{not valid json", encoding="utf-8")
    assert pipeline.load_last_result() is None


def test_load_last_result_valid_json_wrong_shape(isolated_result_path):
    isolated_result_path.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
    assert pipeline.load_last_result() is None