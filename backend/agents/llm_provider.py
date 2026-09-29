"""
LLM provider abstraction.

The agent graph only ever talks to `LLMProvider.extract()`. Swapping the
provider (Gemini <-> Ollama <-> mock) never touches agent/graph code —
only `core.config.Settings.LLM_PROVIDER` changes. This is the seam the
README's "Gemini vs Ollama" trade-off discussion refers to.

`extract()` returns a plain dict matching a requested JSON shape. We ask
each real provider for JSON-mode / schema-constrained output where the API
supports it, and validate the result before ever trusting it (never assume
the LLM produced perfectly well-formed JSON).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.logging import get_logger, log_event

logger = get_logger("llm")


class LLMProviderError(Exception):
    def __init__(self, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.retriable = retriable


class LLMProvider(Protocol):
    def extract(self, system_prompt: str, user_message: str) -> tuple[dict[str, Any], dict]:
        """Returns (parsed_json, token_usage_dict)."""
        ...


class GeminiLLMProvider:
    def __init__(self):
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise LLMProviderError("GEMINI_API_KEY is not set", retriable=False)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
    )
    def _call(self, system_prompt: str, user_message: str) -> httpx.Response:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(url, json=payload)

    def extract(self, system_prompt: str, user_message: str) -> tuple[dict[str, Any], dict]:
        start = time.perf_counter()
        try:
            resp = self._call(system_prompt, user_message)
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMProviderError("Gemini request timed out", retriable=True) from exc
        except httpx.HTTPStatusError as exc:
            retriable = exc.response.status_code >= 500
            raise LLMProviderError(f"Gemini HTTP error: {exc}", retriable=retriable) from exc
        latency_ms = (time.perf_counter() - start) * 1000

        body = resp.json()
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"Malformed Gemini response: {exc}", retriable=False) from exc

        usage = body.get("usageMetadata", {})
        log_event(
            logger,
            logging.INFO,
            "llm_call_completed",
            provider="gemini",
            latency_ms=round(latency_ms, 2),
        )
        return parsed, {"latency_ms": latency_ms, **usage}


class OllamaLLMProvider:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def extract(self, system_prompt: str, user_message: str) -> tuple[dict[str, Any], dict]:
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "system": system_prompt,
                        "prompt": user_message,
                        "format": "json",
                        "stream": False,
                    },
                )
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMProviderError("Ollama request timed out", retriable=True) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama error: {exc}", retriable=True) from exc
        latency_ms = (time.perf_counter() - start) * 1000

        body = resp.json()
        try:
            parsed = json.loads(body["response"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"Malformed Ollama response: {exc}", retriable=False) from exc

        log_event(
            logger,
            logging.INFO,
            "llm_call_completed",
            provider="ollama",
            latency_ms=round(latency_ms, 2),
        )
        return parsed, {"latency_ms": latency_ms}


class MockLLMProvider:
    """Deterministic, offline, rule-based stand-in for a real LLM.

    This makes the *entire agent graph* runnable and unit-testable without
    any API key or network access — used as the default (`LLM_PROVIDER=mock`)
    so `docker compose up` / `pytest` work out of the box. Swapping in
    Gemini/Ollama is a one-line config change (see README)."""

    def extract(self, system_prompt: str, user_message: str) -> tuple[dict[str, Any], dict]:
        from backend.agents.mock_nlu import mock_extract  # local import avoids cycle

        start = time.perf_counter()
        parsed = mock_extract(system_prompt, user_message)
        latency_ms = (time.perf_counter() - start) * 1000
        return parsed, {"latency_ms": latency_ms, "provider": "mock"}


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLMProvider()
    if settings.LLM_PROVIDER == "ollama":
        return OllamaLLMProvider()
    return MockLLMProvider()
