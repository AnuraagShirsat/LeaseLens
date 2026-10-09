# config.py
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

# Knowledge base file (validated by kb/validate_kb.py — 15 rules).
KB_PATH: Path = Path("kb/karnataka_rules.json")

# Encrypted vault where uploaded lease files are stored between sessions.
VAULT_DIR: Path = _CACHE_DIR / "vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Model / API settings  (Ollama)
# --------------------------------------------------------------------------- #
# gemma.py talks to Ollama, so MODEL_NAME must be a valid Ollama tag
# (see `ollama list`). Change to whatever is actually pulled on your machine,
# e.g. "gemma3:4b", "gemma3:12b", "gemma3:27b", "gemma2:9b".
MODEL_NAME: str = "gemma3:4b"

# Kept for callers that still reference GEMMA_MODEL (scripts, older code).
GEMMA_MODEL: str = MODEL_NAME

# Your client should read this from env if you ever switch off Ollama.
GEMMA_API_KEY: str | None = None

# Ollama generation parameters.
NUM_CTX: int = 8192         # context window (tokens). Drop to 4096 if OOM.
NUM_PREDICT: int = 2048     # max output tokens per response.
NUM_GPU: int = -1           # -1 = let Ollama offload as many layers as fit.
TEMPERATURE: float = 0.1    # low = more factual for legal text.
OLLAMA_HOST: str = "http://localhost:11434"
REQUEST_TIMEOUT: int = 300  # seconds; vision calls are slow.

# --------------------------------------------------------------------------- #
# Image handling
# --------------------------------------------------------------------------- #
# Longest side (px) of a rendered page or uploaded image. Kept under 2000 so
# vision models don't reject the image and token cost stays sane.
MAX_IMAGE_SIDE: int = 1600