# core/pipeline.py
"""End-to-end lease analysis pipeline.

Ties together extraction, clause analysis and gap detection, writes the
result to ``config.LAST_RESULT_PATH`` and returns the bundle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import config
from . import schema
from .analyze import analyze_clauses
from .completeness import find_gaps
from .extract import extract_agreement

try:  # pragma: no cover - import location may vary between deployments
    from .gemma import GemmaError
except ImportError:  # pragma: no cover
    class GemmaError(Exception):
        """Fallback so the pipeline module always imports."""


ProgressCb = Callable[[float, str], None]


# Share of the overall progress bar each stage owns.  Must sum to 1.0.
EXTRACT_SHARE = 0.40
ANALYZE_SHARE = 0.45
GAPS_SHARE = 0.15

_EXTRACT_END = EXTRACT_SHARE
_ANALYZE_END = EXTRACT_SHARE + ANALYZE_SHARE
_GAPS_END = _EXTRACT_END + ANALYZE_SHARE + GAPS_SHARE  # == 1.0


class PipelineError(RuntimeError):
    """Raised when the analysis pipeline cannot complete.

    Carries a message that is safe (and useful) to show to an end user.
    """


# --------------------------------------------------------------------------- #
# Progress helpers
# --------------------------------------------------------------------------- #
def _notify(progress_cb: ProgressCb | None, fraction: float, message: str) -> None:
    """Fire ``progress_cb`` tolerating both 1-arg and 2-arg callbacks."""
    if progress_cb is None:
        return
    fraction = max(0.0, min(1.0, float(fraction)))
    try:
        progress_cb(fraction, message)
    except TypeError:
        # Callback only accepts the fraction.
        try:
            progress_cb(fraction)  # type: ignore[misc]
        except TypeError:
            pass


def _scaled_cb(progress_cb: ProgressCb | None, start: float, end: float):
    """Wrap a 0..1 stage callback so it reports ``start..end`` overall."""
    if progress_cb is None:
        return None

    def cb(fraction: float, message: str = "") -> None:
        try:
            frac = float(fraction)
        except (TypeError, ValueError):
            frac = 0.0
        frac = max(0.0, min(1.0, frac))
        _notify(progress_cb, start + (end - start) * frac, message)

    return cb


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def run_analysis(
    page_images: Iterable[Any],
    progress_cb: ProgressCb | None = None,
) -> schema.AnalysisBundle:
    """Run the full pipeline over ``page_images`` and return the bundle.

    Progress is split as:

    * extraction  ->   0% .. 40%
    * analysis    ->  40% .. 85%
    * gap finding ->  85% .. 100%

    Any :class:`GemmaError` raised by the underlying model calls is turned
    into a :class:`PipelineError` with a user-friendly message.
    """
    try:
        _notify(progress_cb, 0.0, "Reading the agreementâ€¦")
        extract = extract_agreement(
            page_images,
            _scaled_cb(progress_cb, 0.0, _EXTRACT_END),
        )

        _notify(progress_cb, _EXTRACT_END, "Checking clauses against the rulesâ€¦")
        findings = analyze_clauses(
            extract,
            _scaled_cb(progress_cb, _EXTRACT_END, _ANALYZE_END),
        )

        _notify(progress_cb, _ANALYZE_END, "Looking for gaps and conflictsâ€¦")
        gaps = find_gaps(extract)
        _notify(progress_cb, _GAPS_END, "Finishing upâ€¦")

        bundle = schema.AnalysisBundle(
            extract=extract,
            findings=findings,
            gaps=gaps,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        schema.to_json_file(bundle, config.LAST_RESULT_PATH)
        _notify(progress_cb, 1.0, "Done.")
        return bundle

    except GemmaError as exc:
        raise PipelineError(
            "We couldn't read this lease automatically. Please try again, or "
            "upload a clearer scan of the agreement."
        ) from exc
    except PipelineError:
        raise
    except Exception as exc:  # defensive: never leak a raw traceback upward
        raise PipelineError(
            f"Something went wrong while analysing the lease: {exc}"
        ) from exc


def load_last_result() -> schema.AnalysisBundle | None:
    """Return the most recent analysis bundle, or ``None`` if unavailable."""
    path = Path(config.LAST_RESULT_PATH)
    if not path.exists():
        return None
    try:
        return schema.from_json_file(path)
    except (OSError, ValueError):
        # Corrupt / incompatible cache: treat as "nothing saved yet".
        return None
