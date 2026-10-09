# gemma.py
"""Thin wrapper around Ollama's chat API.

Provides two helpers:
  - ask_text: free-form text response
  - ask_json: response parsed and validated against a Pydantic model

All Ollama/network failures are surfaced as GemmaError with a friendly message.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional, Type, TypeVar

import ollama
from pydantic import BaseModel, ValidationError

import config


T = TypeVar("T", bound=BaseModel)


class GemmaError(Exception):
    """User-friendly error raised for any Gemma/Ollama failure."""


# --------------------------------------------------------------------------- #
# Health / availability
# --------------------------------------------------------------------------- #

def is_ollama_running() -> bool:
    """Return True if the local Ollama daemon answers, False otherwise."""
    try:
        ollama.list()
        return True
    except Exception:
        return False


def _installed_model_names() -> set[str]:
    """Best-effort extraction of installed model names from ollama.list()."""
    raw = ollama.list()
    names: set[str] = set()

    if isinstance(raw, dict):
        models: Iterable[Any] = raw.get("models", []) or []
    else:
        models = getattr(raw, "models", []) or []

    for m in models:
        if isinstance(m, dict):
            n = m.get("name") or m.get("model")
        else:
            n = getattr(m, "model", None) or getattr(m, "name", None)
        if n:
            names.add(n)
            names.add(n.split(":")[0])
    return names


def _ensure_ready() -> None:
    """Raise a friendly GemmaError if Ollama or the model is unavailable."""
    if not is_ollama_running():
        raise GemmaError(
            "Ollama isn't running. Start it (e.g. `ollama serve`) and try again."
        )

    try:
        names = _installed_model_names()
    except Exception as e:
        raise GemmaError(
            "Couldn't list models from Ollama. Is it running and reachable?"
        ) from e

    wanted = config.MODEL_NAME
    if wanted not in names and wanted.split(":")[0] not in names:
        raise GemmaError(
            f"Model '{wanted}' isn't installed. "
            f"Run `ollama pull {wanted}` and try again."
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #

def _chat(messages: list[dict], *, format: Any = None, temperature: float) -> str:
    """Call ollama.chat, translate failures into GemmaError, return content."""
    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=messages,
            format=format,
            options={
                "temperature": temperature,
                "num_ctx": config.NUM_CTX,
                "num_predict": config.NUM_PREDICT,
                "num_gpu": config.NUM_GPU,
            },
        )
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg or "timed out" in msg or "deadline" in msg:
            raise GemmaError(
                "Ollama timed out while generating a response. "
                "Try again, or use a smaller/faster model."
            ) from e
        if "not found" in msg or "no such model" in msg or "pull" in msg:
            raise GemmaError(
                f"Model '{config.MODEL_NAME}' not found. "
                f"Run `ollama pull {config.MODEL_NAME}` and try again."
            ) from e
        raise GemmaError(f"Error talking to Ollama: {e}") from e

    if isinstance(response, dict):
        return response["message"]["content"]
    return response.message.content


def _build_messages(prompt: str, images: Optional[list[bytes]]) -> list[dict]:
    message: dict[str, Any] = {"role": "user", "content": prompt}
    if images:
        message["images"] = list(images)
    return [message]


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences that some models emit around JSON."""
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    cleaned = cleaned.split("```", 1)[1]
    if "\n" in cleaned:
        first_line, rest = cleaned.split("\n", 1)
        if first_line.strip().lower() in {"json", "json5", "jsonc"}:
            cleaned = rest
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0]
    return cleaned.strip()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def ask_text(prompt: str, images: Optional[list[bytes]] = None) -> str:
    """Return a free-form text response from the configured model."""
    _ensure_ready()
    messages = _build_messages(prompt, images)
    return _chat(messages, temperature=0.3)


def ask_json(
    prompt: str,
    response_model: Type[T],
    images: Optional[list[bytes]] = None,
    retries: int = 2,
) -> T:
    """Ask the model and parse+validate the reply into `response_model`."""
    _ensure_ready()

    schema = response_model.model_json_schema()
    messages = _build_messages(prompt, images)
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        if attempt > 0:
            messages[0]["content"] = (
                f"{prompt}\n\n"
                "Return ONLY valid JSON that conforms exactly to the schema. "
                "No prose, no markdown, no code fences."
            )

        raw = _chat(messages, format=schema, temperature=0.1)

        try:
            cleaned = _strip_code_fences(raw)
            return response_model.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_error = e
            continue

    raise GemmaError(
        f"The model returned invalid output after {retries + 1} attempt(s). "
        f"Last error: {last_error}"
    )