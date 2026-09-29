from __future__ import annotations

import uuid

from backend.tools.compare import compare_items
from backend.tools.preferences import get_user_preferences, save_preference
from backend.tools.search_food import search_food


def test_search_food_excludes_unavailable_items(db_session, seeded_catalog):
    result = search_food(db_session, {"dietary_preference": "any", "limit": 20})
    assert result.success
    names = {i["item"]["name"] for i in result.data["items"]}
    assert "Unavailable Soup" not in names


def test_search_food_hard_filters_never_relaxed_by_semantics(db_session, seeded_catalog):
    """Even if the free-text query is semantically close to a non-veg item,
    a vegetarian filter must never surface it (spec section 10)."""
    result = search_food(
        db_session,
        {"dietary_preference": "vegetarian", "query": "creamy chicken curry", "limit": 20},
    )
    assert result.success
    for i in result.data["items"]:
        assert i["item"]["is_vegetarian"] is True


def test_search_food_rejects_invalid_arguments(db_session, seeded_catalog):
    result = search_food(db_session, {"max_price": -50})  # guardrail: ge=0
    assert result.success is False
    assert result.error is not None


def test_search_food_rejects_unsupported_dietary_value(db_session, seeded_catalog):
    result = search_food(db_session, {"dietary_preference": "keto"})
    assert result.success is False


def test_compare_items_requires_at_least_two(db_session, seeded_catalog):
    one_id = str(seeded_catalog["items"][0].id)
    result = compare_items(db_session, {"item_ids": [one_id]})
    assert result.success is False


def test_compare_items_rejects_nonexistent_id(db_session, seeded_catalog):
    real_id = str(seeded_catalog["items"][0].id)
    fake_id = str(uuid.uuid4())
    result = compare_items(db_session, {"item_ids": [real_id, fake_id]})
    assert result.success is False
    assert "not found" in result.error.lower()


def test_compare_items_returns_summary(db_session, seeded_catalog):
    ids = [str(i.id) for i in seeded_catalog["items"][:2]]
    result = compare_items(db_session, {"item_ids": ids})
    assert result.success
    assert "cheapest_id" in result.data["summary"]
    assert "highest_rated_id" in result.data["summary"]


def test_save_preference_rejects_negative_budget(db_session, seeded_catalog):
    result = save_preference(db_session, {"user_id": str(uuid.uuid4()), "max_budget": -10})
    assert result.success is False


def test_save_preference_rejects_invalid_spice_level(db_session, seeded_catalog):
    result = save_preference(
        db_session, {"user_id": str(uuid.uuid4()), "spice_level": "extremely-hot"}
    )
    assert result.success is False


def test_save_and_get_preference_roundtrip(db_session, seeded_catalog):
    user_id = str(uuid.uuid4())
    save_result = save_preference(
        db_session,
        {"user_id": user_id, "spice_level": "spicy", "preferred_cuisine": "North Indian"},
    )
    assert save_result.success
    db_session.commit()

    get_result = get_user_preferences(db_session, {"user_id": user_id})
    assert get_result.success
    assert get_result.data["spice_level"] == "spicy"
    assert get_result.data["preferred_cuisine"] == "North Indian"


def test_unknown_tool_name_is_rejected():
    from backend.tools.registry import execute_tool

    class _FakeDb:
        pass

    result = execute_tool("drop_all_tables", _FakeDb(), {})
    assert result.success is False
    assert "unknown tool" in result.error.lower()
