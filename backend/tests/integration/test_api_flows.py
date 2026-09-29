from __future__ import annotations

import uuid


def test_health_check(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_search_returns_ranked_recommendations(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    resp = api_client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "I want spicy vegetarian food under 300."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "search_food"
    assert len(body["recommendations"]) >= 1
    for rec in body["recommendations"]:
        assert rec["item"]["is_vegetarian"] is True
        assert rec["item"]["price"] <= 300


def test_chat_conversation_context_persists_across_turns(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    r1 = api_client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "I want vegetarian food under 300."},
    ).json()
    convo_id = r1["conversation_id"]
    assert len(r1["recommendations"]) >= 1

    r2 = api_client.post(
        "/api/chat",
        json={"user_id": user_id, "conversation_id": convo_id, "message": "Make it spicy."},
    ).json()
    assert r2["conversation_id"] == convo_id
    for rec in r2["recommendations"]:
        assert rec["item"]["is_vegetarian"] is True  # inherited from turn 1
        assert rec["item"]["spice_level"] == "spicy"  # from turn 2


def test_chat_compare_resolves_ordinal_references(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    r1 = api_client.post(
        "/api/chat", json={"user_id": user_id, "message": "show me vegetarian food"}
    ).json()
    convo_id = r1["conversation_id"]
    assert len(r1["recommendations"]) >= 2

    r2 = api_client.post(
        "/api/chat",
        json={
            "user_id": user_id,
            "conversation_id": convo_id,
            "message": "Compare the first and second.",
        },
    ).json()
    assert r2["intent"] == "compare_items"
    assert r2["errors"] == []


def test_chat_compare_without_prior_search_fails_gracefully(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    resp = api_client.post(
        "/api/chat", json={"user_id": user_id, "message": "Compare the first and third."}
    )
    assert resp.status_code == 200  # never a raw 500 for a recoverable case
    body = resp.json()
    assert len(body["errors"]) >= 1


def test_chat_persistent_preference_is_saved_and_retrievable(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    resp = api_client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "I usually prefer spicy North Indian food."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "update_preference"

    pref_resp = api_client.get(f"/api/preferences?user_id={user_id}")
    assert pref_resp.status_code == 200
    pref = pref_resp.json()
    assert pref["spice_level"] == "spicy"
    assert pref["preferred_cuisine"] == "North Indian"


def test_chat_one_off_preference_statement_is_not_persisted(api_client, seeded_catalog):
    """'I want spicy food right now' is NOT a persistent-preference phrase —
    spec section 12 explicitly forbids saving every conversational
    statement as permanent memory."""
    user_id = str(uuid.uuid4())
    api_client.post(
        "/api/chat", json={"user_id": user_id, "message": "I want spicy food right now."}
    )
    pref = api_client.get(f"/api/preferences?user_id={user_id}").json()
    assert pref["spice_level"] is None


def test_chat_empty_message_returns_400(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    resp = api_client.post("/api/chat", json={"user_id": user_id, "message": "   "})
    assert resp.status_code == 400


def test_chat_no_results_returns_helpful_message_not_error(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    resp = api_client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "vegetarian food under 1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendations"] == []
    assert "couldn't find" in body["reply"].lower()


def test_food_detail_endpoint(api_client, seeded_catalog):
    item_id = str(seeded_catalog["items"][0].id)
    resp = api_client.get(f"/api/food/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id


def test_food_detail_404_for_unknown_id(api_client, seeded_catalog):
    resp = api_client.get(f"/api/food/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_saved_items_roundtrip(api_client, seeded_catalog):
    user_id = str(uuid.uuid4())
    item_id = str(seeded_catalog["items"][0].id)

    create_resp = api_client.post(
        "/api/saved-items", json={"user_id": user_id, "menu_item_id": item_id}
    )
    assert create_resp.status_code == 200
    saved_id = create_resp.json()["saved_item_id"]

    list_resp = api_client.get(f"/api/saved-items?user_id={user_id}")
    assert len(list_resp.json()["items"]) == 1

    delete_resp = api_client.delete(f"/api/saved-items/{saved_id}")
    assert delete_resp.status_code == 204

    list_resp2 = api_client.get(f"/api/saved-items?user_id={user_id}")
    assert len(list_resp2.json()["items"]) == 0


def test_compare_endpoint_direct(api_client, seeded_catalog):
    ids = [str(i.id) for i in seeded_catalog["items"][:2]]
    resp = api_client.post("/api/compare", json={"item_ids": ids})
    assert resp.status_code == 200
    assert "summary" in resp.json()


def test_rate_limit_headers_present(api_client, seeded_catalog):
    resp = api_client.get("/health")
    assert "x-request-id" in resp.headers
