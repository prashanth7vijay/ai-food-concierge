"""
Deterministic ranking.

Design decision (see README "Trade-offs"): the LLM proposes constraints and
generates the natural-language reply, but it NEVER decides which items rank
higher than others. Ranking is a pure function of measurable signals so that
(a) results are reproducible given the same data and weights, (b) results
can be unit tested, and (c) a prompt change or model swap can never silently
change what users are recommended.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import get_settings
from backend.models.catalog import MenuItem
from backend.schemas.catalog import SearchFoodParams


@dataclass
class ScoredItem:
    item: MenuItem
    score: float
    breakdown: dict[str, float]


def _price_fit(item_price: float, max_price: float | None) -> float:
    if max_price is None or max_price <= 0:
        return 0.5  # neutral — no constraint given
    if item_price > max_price:
        return 0.0  # should already be filtered out, but scored safely regardless
    # Closer to the budget without exceeding it scores slightly higher than
    # something far under budget, on the theory the user picked a budget
    # that matters to them (weakly-held heuristic, documented as such).
    return 0.5 + 0.5 * (item_price / max_price)


def _cuisine_match(item_cuisine: str, requested_cuisine: str | None) -> float:
    if not requested_cuisine:
        return 0.5
    return 1.0 if requested_cuisine.lower() in item_cuisine.lower() else 0.0


def _constraint_match(item: MenuItem, params: SearchFoodParams) -> float:
    checks: list[bool] = []
    if params.dietary_preference == "vegetarian":
        checks.append(item.is_vegetarian is True)
    elif params.dietary_preference == "non_vegetarian":
        checks.append(item.is_vegetarian is False)
    if params.spice_level:
        checks.append(item.spice_level == params.spice_level)
    if params.max_price is not None:
        checks.append(item.price <= params.max_price)
    if not checks:
        return 1.0
    return sum(1 for c in checks if c) / len(checks)


def rank_items(
    items: list[MenuItem],
    params: SearchFoodParams,
    semantic_scores: dict[str, float] | None = None,
) -> list[ScoredItem]:
    """Score and sort items by a weighted combination of signals.

    Weights are configurable via Settings (RANKING_WEIGHT_*) rather than
    hardcoded, per spec section 11.
    """
    settings = get_settings()
    semantic_scores = semantic_scores or {}
    scored: list[ScoredItem] = []

    for item in items:
        breakdown = {
            "constraint_match": _constraint_match(item, params),
            "semantic_relevance": semantic_scores.get(str(item.id), 0.0),
            "rating": (item.rating or 0.0) / 5.0,
            "price_fit": _price_fit(item.price, params.max_price),
            "cuisine_match": _cuisine_match(item.cuisine, params.cuisine),
        }
        score = (
            breakdown["constraint_match"] * settings.RANKING_WEIGHT_CONSTRAINT_MATCH
            + breakdown["semantic_relevance"] * settings.RANKING_WEIGHT_SEMANTIC
            + breakdown["rating"] * settings.RANKING_WEIGHT_RATING
            + breakdown["price_fit"] * settings.RANKING_WEIGHT_PRICE_FIT
            + breakdown["cuisine_match"] * settings.RANKING_WEIGHT_CUISINE_MATCH
        )
        scored.append(ScoredItem(item=item, score=round(score, 4), breakdown=breakdown))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def explain_reason(scored: ScoredItem, params: SearchFoodParams) -> str:
    """Short, human-readable reason string for a recommendation card.
    Deterministic (not LLM-generated) so it always matches the actual
    ranking signals — no hallucinated justifications."""
    reasons: list[str] = []
    b = scored.breakdown
    if params.dietary_preference == "vegetarian" and scored.item.is_vegetarian:
        reasons.append("matches your vegetarian preference")
    if params.spice_level and scored.item.spice_level == params.spice_level:
        reasons.append(f"{params.spice_level} spice level as requested")
    if params.max_price and scored.item.price <= params.max_price:
        reasons.append(f"within your ₹{int(params.max_price)} budget")
    if b["rating"] >= 0.8:
        reasons.append("highly rated")
    if b["semantic_relevance"] >= 0.6:
        reasons.append("closely matches what you described")
    if not reasons:
        reasons.append("a solid overall match for your request")
    return "; ".join(reasons).capitalize()
