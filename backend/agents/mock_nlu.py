"""
Deterministic rule-based natural-language understanding.

Used by `MockLLMProvider` so the full agent graph works with zero external
API dependency. It is intentionally simple regex/keyword matching — good
enough to drive the documented demo conversation (spec section 29) and to
make agent behavior reproducible in CI, but it is NOT a substitute for a
real LLM's language understanding; see README for how this is swapped for
Gemini/Ollama in a real deployment.
"""

from __future__ import annotations

import re

_ORDINALS = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
}

_KNOWN_CUISINES = [
    "north indian",
    "south indian",
    "chinese",
    "italian",
    "continental",
    "thai",
    "mexican",
    "mediterranean",
]

_PERSISTENT_PHRASES = [
    "i usually prefer",
    "i always prefer",
    "i always like",
    "i usually like",
    "i generally prefer",
    "my preference is",
    "remember that i",
]


def _is_persistent_preference(text: str) -> bool:
    if any(p in text for p in _PERSISTENT_PHRASES):
        return True
    # Looser fallback: a persistence adverb anywhere near a preference verb
    # ("I prefer North Indian food usually", "I generally like it spicy").
    # A real LLM handles word-order variation natively; this mock only
    # approximates it — documented limitation, see README trade-offs.
    has_adverb = re.search(r"\b(usually|always|generally|normally)\b", text)
    has_verb = re.search(r"\b(prefer|like|love|enjoy)\b", text)
    return bool(has_adverb and has_verb)


def _extract_price(text: str) -> float | None:
    m = re.search(r"(?:under|below|less than|within)\s*(?:rs\.?|inr|₹)?\s*(\d+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(?:₹|rs\.?)\s*(\d+)", text)
    return float(m.group(1)) if m else None


def _extract_dietary(text: str) -> str | None:
    if "non veg" in text or "non-veg" in text or "nonveg" in text:
        return "non_vegetarian"
    if "veg" in text or "vegetarian" in text:
        return "vegetarian"
    return None


def _extract_spice(text: str) -> str | None:
    if "spicy" in text or "hot" in text:
        return "spicy"
    if "mild" in text:
        return "mild"
    if "medium spice" in text:
        return "medium"
    return None


def _extract_cuisine(text: str) -> str | None:
    for cuisine in _KNOWN_CUISINES:
        if cuisine in text:
            return cuisine.title()
    return None


def _extract_rating(text: str) -> float | None:
    if "highly rated" in text or "best rated" in text or "top rated" in text:
        return 4.0
    return None


def _extract_compare_indices(text: str) -> list[int] | None:
    if "compare" not in text:
        return None
    found = [idx for word, idx in _ORDINALS.items() if re.search(rf"\b{word}\b", text)]
    if len(found) >= 2:
        return sorted(set(found))
    # Generic comparison phrasing with no explicit ordinals ("compare these
    # two", "compare them both") — default to the first two prior results.
    if re.search(r"\b(these|those|them|both)\b", text):
        return [0, 1]
    return None


def _leftover_query_terms(text: str) -> str:
    """Very rough free-text signal for the semantic-retrieval layer:
    strip recognized structured tokens, keep the rest as descriptive text."""
    noise = [
        "i want",
        "i'd like",
        "show me",
        "looking for",
        "something",
        "for dinner",
        "for breakfast",
        "for lunch",
        "please",
        "preferably",
        "under",
        "below",
        "less than",
        "within",
        "vegetarian",
        "vegan",
        "non veg",
        "non-veg",
        "spicy",
        "mild",
        "medium",
        "highly rated",
        "best rated",
        "top rated",
    ]
    cleaned = text
    for n in noise:
        cleaned = cleaned.replace(n, " ")
    cleaned = re.sub(r"[₹\d]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def mock_extract(system_prompt: str, user_message: str) -> dict:
    # `user_message` here is actually "Conversation so far: ...\n\nUser message: <latest>"
    # (see agents/nodes.py understand_request_node). Intent/constraint
    # extraction must only look at the CURRENT turn, never bleed keywords
    # in from prior turns in the conversation history.
    marker = "user message:"
    lowered_full = user_message.lower()
    idx = lowered_full.rfind(marker)
    current_only = user_message[idx + len(marker) :] if idx != -1 else user_message
    text = current_only.lower().strip()

    compare_indices = _extract_compare_indices(text)
    is_persistent = _is_persistent_preference(text)

    if compare_indices:
        intent = "compare_items"
    elif is_persistent:
        intent = "update_preference"
    elif any(w in text for w in ["my preference", "what do you know about me", "my profile"]):
        intent = "get_preferences"
    elif (
        any(w in text for w in ["hi", "hello", "hey", "thanks", "thank you"])
        and len(text.split()) <= 3
    ):
        intent = "chit_chat"
    else:
        intent = "search_food"

    constraints: dict = {
        "query": _leftover_query_terms(text) or None,
        "max_price": _extract_price(text),
        "min_rating": _extract_rating(text),
        "cuisine": _extract_cuisine(text),
        "dietary_preference": _extract_dietary(text),
        "spice_level": _extract_spice(text),
        "compare_indices": compare_indices,
        "persistent_preference": None,
    }

    if is_persistent:
        pref: dict = {}
        if constraints["dietary_preference"] == "vegetarian":
            pref["is_vegetarian"] = True
        elif constraints["dietary_preference"] == "non_vegetarian":
            pref["is_vegetarian"] = False
        if constraints["cuisine"]:
            pref["preferred_cuisine"] = constraints["cuisine"]
        if constraints["spice_level"]:
            pref["spice_level"] = constraints["spice_level"]
        if constraints["max_price"]:
            pref["max_budget"] = constraints["max_price"]
        constraints["persistent_preference"] = pref or None

    return {"intent": intent, "constraints": constraints}
