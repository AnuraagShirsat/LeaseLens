# core/config.py
"""Central configuration for LeaseLens.

This module must not import from any other ``core`` module, so that every
other module can safely do ``from . import config`` at import time without
creating an import cycle.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# Where the most recent AnalysisBundle is cached so the UI can show a result
# instantly on startup (see core.pipeline.load_last_result).
_CACHE_DIR = Path("data")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

LAST_RESULT_PATH: Path = _CACHE_DIR / "last_result.json"

# --------------------------------------------------------------------------- #
# Model / API settings
# --------------------------------------------------------------------------- #
# Placeholders so that everything imports cleanly. The tests in
# tests/test_pipeline.py mock the model calls entirely, so no real credentials
# are needed to run them.
GEMMA_MODEL: str = "gemma-3-27b-it"
GEMMA_API_KEY: str | None = None  # your client should read this from env