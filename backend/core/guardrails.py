"""
Application-level guardrails for raw user input, applied before the message
ever reaches the agent/LLM layer (spec section 13).

This is a coarse, defense-in-depth screen — not a claim of fully solving
prompt injection. Combined with the tool registry whitelist (registry.py)
and strict Pydantic schemas on every tool, the real security boundary is
that the LLM's output is only ever treated as a *proposal*: it is validated
and executed through deterministic, parameterized code, never as a
literal command or SQL/shell input.
"""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"system prompt",
    r"reveal your (instructions|prompt)",
    r"you are now",
    r"disregard (the )?(rules|guidelines)",
]

_MAX_MESSAGE_LENGTH = 2000


class GuardrailViolation(Exception):
    pass


def validate_user_message(message: str) -> str:
    if not message or not message.strip():
        raise GuardrailViolation("Message cannot be empty.")
    if len(message) > _MAX_MESSAGE_LENGTH:
        raise GuardrailViolation(f"Message exceeds {_MAX_MESSAGE_LENGTH} characters.")
    return message.strip()


def flag_prompt_injection(message: str) -> bool:
    """Returns True if the message looks like an attempt to override the
    system prompt. We don't silently rewrite the user's message — the
    agent layer logs this and treats the message as ordinary (untrusted)
    user text rather than an instruction, same as it always does."""
    lowered = message.lower()
    return any(re.search(p, lowered) for p in _INJECTION_PATTERNS)
