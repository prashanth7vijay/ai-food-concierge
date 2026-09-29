from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from backend.agents.llm_provider import LLMProvider, LLMProviderError
from backend.agents.memory import should_persist_preference
from backend.agents.state import AgentState
from backend.core.logging import get_logger, log_event
from backend.repositories.user_repository import ConversationRepository
from backend.tools.registry import execute_tool

logger = get_logger("agent")

_SYSTEM_PROMPT = """You are the NLU layer for a food-recommendation agent.
Given a user message and short conversation history, respond with ONLY a
JSON object of the form:
{
  "intent": "search_food | compare_items | get_preferences | update_preference | chit_chat | unknown",
  "constraints": {
    "query": string or null,
    "max_price": number or null,
    "min_rating": number or null,
    "cuisine": string or null,
    "dietary_preference": "vegetarian" | "non_vegetarian" | null,
    "spice_level": "mild" | "medium" | "spicy" | null,
    "compare_indices": [array of 0-based ints] or null,
    "persistent_preference": object or null
  }
}
Only set persistent_preference when the user is expressing a stable, recurring
preference (e.g. "I usually prefer..."), not a one-off request. Never invent
values not implied by the message."""


def _activity(state: AgentState, label: str, status: str = "done") -> None:
    state.setdefault("activity_log", []).append({"label": label, "status": status})


def load_conversation_context_node(db: Session):
    def _node(state: AgentState) -> AgentState:
        repo = ConversationRepository(db)
        history = repo.recent_history(state["conversation_id"], limit=6)
        last_shown = repo.last_shown_item_ids(state["conversation_id"])
        state["conversation_history"] = [{"role": m.role, "content": m.content} for m in history]
        state["last_shown_item_ids"] = [str(i) for i in last_shown]
        _activity(state, "Loaded conversation context")
        return state

    return _node


def understand_request_node(llm: LLMProvider):
    def _node(state: AgentState) -> AgentState:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("conversation_history", [])[-4:]
        )
        prompt_input = (
            f"Conversation so far:\n{history_text}\n\nUser message: {state['current_message']}"
        )

        start = time.perf_counter()
        try:
            parsed, usage = llm.extract(_SYSTEM_PROMPT, prompt_input)
        except LLMProviderError as exc:
            # Transient vs permanent: retriable errors still fail this turn
            # gracefully rather than hanging; permanent errors (bad config,
            # malformed response) fall back to "unknown" intent so the user
            # gets a safe, honest response instead of a crash.
            log_event(
                logger, logging.ERROR, "llm_extract_failed", error=str(exc), retriable=exc.retriable
            )
            state.setdefault("errors", []).append(f"Language understanding failed: {exc}")
            state["detected_intent"] = "unknown"
            state["extracted_constraints"] = {}
            _activity(state, "Understood user request", status="failed")
            return state
        state["llm_latency_ms"] = (time.perf_counter() - start) * 1000
        state["llm_token_usage"] = usage

        intent = parsed.get("intent", "unknown")
        if intent not in {
            "search_food",
            "compare_items",
            "get_preferences",
            "update_preference",
            "chit_chat",
            "unknown",
        }:
            intent = "unknown"  # guardrail: never trust an unvalidated intent label
        state["detected_intent"] = intent
        state["extracted_constraints"] = parsed.get("constraints", {}) or {}
        _activity(state, "Parsed user request and intent")
        return state

    return _node


def merge_context_node(db: Session):
    """Short-term memory: for a search_food turn, any constraint field the
    current message didn't specify is inherited from the most recent
    search in this conversation (e.g. 'make it spicy' / 'which one is
    lighter' keeps the earlier budget/dietary/cuisine filters and only
    changes what the user actually mentioned this turn)."""

    def _node(state: AgentState) -> AgentState:
        if state.get("detected_intent") != "search_food":
            return state
        from backend.repositories.user_repository import AgentRunRepository

        previous = AgentRunRepository(db).get_last_search_constraints(state["conversation_id"])
        if not previous:
            return state

        current = state.get("extracted_constraints", {}) or {}
        carried_over: list[str] = []
        for field in ("max_price", "min_rating", "cuisine", "dietary_preference", "spice_level"):
            if current.get(field) is None and previous.get(field) is not None:
                current[field] = previous[field]
                carried_over.append(field)
        state["extracted_constraints"] = current
        if carried_over:
            _activity(state, f"Reused prior context ({', '.join(carried_over)})")
        return state

    return _node


def determine_tools_node(state: AgentState) -> AgentState:
    intent = state.get("detected_intent", "unknown")
    mapping = {
        "search_food": ["search_food"],
        "compare_items": ["compare_items"],
        "get_preferences": ["get_user_preferences"],
        "update_preference": ["save_preference"],
        "chit_chat": [],
        "unknown": [],
    }
    state["selected_tools"] = mapping.get(intent, [])
    _activity(state, "Determined required tools")
    return state


def execute_tools_node(db: Session):
    def _node(state: AgentState) -> AgentState:
        tools = state.get("selected_tools", [])
        constraints = state.get("extracted_constraints", {})
        results = []

        for tool_name in tools:
            args = _build_tool_args(tool_name, state, constraints)
            if args is None:
                continue  # guardrail rejected building args (e.g. bad compare indices)
            result = execute_tool(tool_name, db, args)
            results.append(
                {
                    "tool_name": tool_name,
                    "arguments": args,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "latency_ms": round(result.latency_ms, 2),
                }
            )
            if not result.success:
                state.setdefault("errors", []).append(f"{tool_name}: {result.error}")

        state["tool_results"] = results
        _activity(state, "Executed tools")
        return state

    return _node


def _build_tool_args(tool_name: str, state: AgentState, constraints: dict) -> dict | None:
    if tool_name == "search_food":
        return {
            "query": constraints.get("query"),
            "max_price": constraints.get("max_price"),
            "min_rating": constraints.get("min_rating"),
            "cuisine": constraints.get("cuisine"),
            "dietary_preference": constraints.get("dietary_preference") or "any",
            "spice_level": constraints.get("spice_level"),
            "limit": 10,
        }
    if tool_name == "compare_items":
        indices = constraints.get("compare_indices")
        last_shown = state.get("last_shown_item_ids", [])
        if not indices or not last_shown:
            state.setdefault("errors", []).append(
                "Nothing to compare — no prior results in this conversation."
            )
            return None
        try:
            item_ids = [last_shown[i] for i in indices if i < len(last_shown)]
        except (IndexError, TypeError):
            item_ids = []
        if len(item_ids) < 2:
            state.setdefault("errors", []).append("Couldn't resolve which items to compare.")
            return None
        return {"item_ids": item_ids}
    if tool_name == "get_user_preferences":
        return {"user_id": str(state["user_id"])}
    if tool_name == "save_preference":
        pref = constraints.get("persistent_preference")
        if not should_persist_preference(pref):
            return None
        return {"user_id": str(state["user_id"]), **pref}
    return None


def validate_and_rank_node(state: AgentState) -> AgentState:
    """Ranking itself already happened deterministically inside the
    search_food tool; this node just extracts/validates the shape of what
    each tool returned before it's used to build the response."""
    ranked_items: list[dict] = []
    for tr in state.get("tool_results", []):
        if tr["tool_name"] == "search_food" and tr["success"]:
            ranked_items = tr["data"].get("items", [])
    state["ranked_items"] = ranked_items
    _activity(state, "Validated and ranked results")
    return state


def generate_response_node(state: AgentState) -> AgentState:
    """Deterministic, template-based reply generation — kept separate from
    the LLM's structured extraction so that even in mock/offline mode the
    demo produces a coherent, safe reply (see README: real deployments can
    swap this for an LLM-authored reply using ranked_items as grounding,
    while keeping ranking itself deterministic)."""
    intent = state.get("detected_intent", "unknown")
    errors = state.get("errors", [])

    if intent == "search_food":
        items = state.get("ranked_items", [])
        if not items:
            state["response"] = (
                "I couldn't find anything matching that. Try loosening the budget "
                "or dietary filter?"
            )
        else:
            top = items[0]["item"]["name"]
            state["response"] = (
                f"Here are {len(items)} options I found, starting with {top} — "
                "take a look at the cards for details."
            )
    elif intent == "compare_items":
        tool_data = next(
            (
                tr["data"]
                for tr in state.get("tool_results", [])
                if tr["tool_name"] == "compare_items"
            ),
            None,
        )
        if tool_data:
            state["response"] = (
                "Here's how those two compare on price, rating, and how light they are."
            )
        else:
            state["response"] = "I couldn't compare those — " + "; ".join(
                errors or ["please try again."]
            )
    elif intent == "update_preference":
        pref = state.get("extracted_constraints", {}).get("persistent_preference")
        if pref:
            state["response"] = "Got it — I'll remember that preference for next time."
        else:
            state["response"] = (
                "Noted, though I'll only remember it if it sounded like a lasting preference."
            )
    elif intent == "get_preferences":
        state["response"] = "Here's what I have saved about your preferences so far."
    elif intent == "chit_chat":
        state["response"] = "Happy to help — tell me what you're in the mood for!"
    else:
        state["response"] = (
            "I'm not sure I understood that — try describing what you'd like to eat, "
            "e.g. 'spicy vegetarian food under ₹400'."
        )

    _activity(state, "Generated response")
    return state


def finalize_node(state: AgentState) -> AgentState:
    """Marks the graph run complete. Actual persistence of the AgentRun /
    ToolCall audit rows happens in the service layer that invokes this
    graph (backend/services/chat_service.py), since it needs to wrap the
    whole run in one DB transaction alongside message persistence."""
    _activity(state, "Finalized agent run")
    return state
