from __future__ import annotations

import uuid

from backend.agents.graph import build_agent_graph
from backend.agents.llm_provider import get_llm_provider
from backend.agents.state import AgentState


def _invoke(db_session, message: str, conversation_id=None, user_id=None) -> AgentState:
    llm = get_llm_provider()
    graph = build_agent_graph(db_session, llm)
    state: AgentState = {
        "conversation_id": conversation_id or uuid.uuid4(),
        "user_id": user_id or uuid.uuid4(),
        "request_id": str(uuid.uuid4()),
        "current_message": message,
        "activity_log": [],
        "errors": [],
    }
    return graph.invoke(state)


def test_agent_graph_search_food_happy_path(db_session, seeded_catalog):
    result = _invoke(db_session, "spicy vegetarian food under 300")
    assert result["detected_intent"] == "search_food"
    assert len(result["ranked_items"]) >= 1
    assert result["errors"] == []
    labels = [a["label"] for a in result["activity_log"]]
    assert "Loaded conversation context" in labels
    assert "Executed tools" in labels
    assert "Generated response" in labels


def test_agent_graph_never_exposes_chain_of_thought(db_session, seeded_catalog):
    result = _invoke(db_session, "spicy vegetarian food under 300")
    for event in result["activity_log"]:
        # Activity labels must be short, high-level descriptions — not raw
        # reasoning traces.
        assert len(event["label"]) < 80
        assert "\n" not in event["label"]


def test_agent_graph_empty_search_result_has_no_errors_just_empty_list(db_session, seeded_catalog):
    result = _invoke(db_session, "vegetarian food under 1 rupee")
    assert result["ranked_items"] == []
    assert result["detected_intent"] == "search_food"


def test_agent_graph_malformed_llm_output_falls_back_gracefully(
    db_session, seeded_catalog, monkeypatch
):
    """Simulates an LLM provider that returns garbage — the graph must not
    crash; it should degrade to 'unknown' intent with a safe response."""
    import backend.agents.nodes as nodes_module

    class _BrokenProvider:
        def extract(self, system_prompt, user_message):
            raise nodes_module.LLMProviderError("simulated malformed response", retriable=False)

    llm = _BrokenProvider()
    graph = build_agent_graph(db_session, llm)
    state: AgentState = {
        "conversation_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "request_id": str(uuid.uuid4()),
        "current_message": "anything",
        "activity_log": [],
        "errors": [],
    }
    result = graph.invoke(state)
    assert result["detected_intent"] == "unknown"
    assert result["response"]  # still produces a safe reply, doesn't crash
    assert len(result["errors"]) >= 1


def test_agent_graph_compare_without_context_is_handled(db_session, seeded_catalog):
    result = _invoke(db_session, "compare the first and third")
    assert result["detected_intent"] == "compare_items"
    assert len(result["errors"]) >= 1  # nothing to compare yet — handled, not crashed


def test_agent_graph_repeated_identical_request_is_reproducible(db_session, seeded_catalog):
    """Same request, same data -> same ranking. Determinism is the whole
    point of keeping ranking out of the LLM's hands."""
    r1 = _invoke(db_session, "spicy vegetarian food under 300")
    r2 = _invoke(db_session, "spicy vegetarian food under 300")
    names1 = [i["item"]["name"] for i in r1["ranked_items"]]
    names2 = [i["item"]["name"] for i in r2["ranked_items"]]
    assert names1 == names2
