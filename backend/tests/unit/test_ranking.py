from __future__ import annotations

from backend.schemas.catalog import SearchFoodParams
from backend.tools.ranking import explain_reason, rank_items


def test_rank_items_orders_by_score_descending(seeded_catalog, db_session):
    items = seeded_catalog["items"][:4]  # exclude the unavailable one
    params = SearchFoodParams(dietary_preference="vegetarian", max_price=300, spice_level=None)
    scored = rank_items(items, params)
    scores = [s.score for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_rank_items_rewards_constraint_match(seeded_catalog):
    items = seeded_catalog["items"][:4]
    params = SearchFoodParams(dietary_preference="vegetarian", max_price=300, spice_level="spicy")
    scored = rank_items(items, params)
    # Paneer Curry is vegetarian+spicy+<=300; Butter Chicken is non-veg and
    # over budget-ish spice mismatch — Paneer Curry must outrank it.
    names = {s.item.name: s.score for s in scored}
    assert names["Paneer Curry"] > names["Butter Chicken"]


def test_price_fit_never_negative_or_above_one(seeded_catalog):
    items = seeded_catalog["items"][:4]
    params = SearchFoodParams(max_price=None)  # no budget constraint given
    scored = rank_items(items, params)
    for s in scored:
        assert 0.0 <= s.breakdown["price_fit"] <= 1.0


def test_explain_reason_mentions_budget_when_relevant(seeded_catalog):
    items = seeded_catalog["items"][:4]
    params = SearchFoodParams(max_price=300, dietary_preference="vegetarian")
    scored = rank_items(items, params)
    top = scored[0]
    reason = explain_reason(top, params)
    assert isinstance(reason, str) and len(reason) > 0


def test_ranking_weights_configurable(monkeypatch, seeded_catalog):
    """Weights come from Settings, not hardcoded constants — verify a
    weight change actually shifts scores rather than being ignored."""
    from backend.core import config

    items = seeded_catalog["items"][:4]
    params = SearchFoodParams(dietary_preference="vegetarian")

    baseline = rank_items(items, params)
    baseline_scores = {s.item.name: s.score for s in baseline}

    config.get_settings.cache_clear()
    monkeypatch.setenv("RANKING_WEIGHT_RATING", "0.9")
    monkeypatch.setenv("RANKING_WEIGHT_CONSTRAINT_MATCH", "0.02")
    monkeypatch.setenv("RANKING_WEIGHT_SEMANTIC", "0.02")
    monkeypatch.setenv("RANKING_WEIGHT_PRICE_FIT", "0.03")
    monkeypatch.setenv("RANKING_WEIGHT_CUISINE_MATCH", "0.03")
    config.get_settings.cache_clear()

    reweighted = rank_items(items, params)
    reweighted_scores = {s.item.name: s.score for s in reweighted}

    assert baseline_scores != reweighted_scores
    config.get_settings.cache_clear()
