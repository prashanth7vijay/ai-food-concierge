"""
Long-term memory gate.

Spec section 12 is explicit: "Do NOT save every conversational statement as
permanent memory. Only save preferences when the system has sufficient
confidence or when the user clearly expresses a persistent preference."

The NLU layer (mock or real LLM) only ever populates
`constraints['persistent_preference']` when the message contained an
explicit persistence signal (e.g. "I usually prefer...", not just "I want
spicy food right now"). This module is a second, independent guardrail on
top of that — it re-validates the payload is non-empty and well-formed
before the agent is allowed to call `save_preference` at all.
"""

from __future__ import annotations


def should_persist_preference(persistent_preference: dict | None) -> bool:
    if not persistent_preference:
        return False
    allowed_keys = {"is_vegetarian", "preferred_cuisine", "spice_level", "max_budget"}
    meaningful = {
        k: v for k, v in persistent_preference.items() if k in allowed_keys and v is not None
    }
    return len(meaningful) > 0
