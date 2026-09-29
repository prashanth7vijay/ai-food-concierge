from __future__ import annotations

import uuid
from typing import Any, Literal, TypedDict

Intent = Literal[
    "search_food",
    "compare_items",
    "get_preferences",
    "update_preference",
    "chit_chat",
    "unknown",
]


class ExtractedConstraints(TypedDict, total=False):
    query: str | None
    max_price: float | None
    min_rating: float | None
    cuisine: str | None
    dietary_preference: str | None
    spice_level: str | None
    compare_indices: list[int] | None  # e.g. [0, 2] for "first and third"
    persistent_preference: dict[str, Any] | None  # present only if high-confidence


class ActivityEvent(TypedDict):
    label: str
    status: Literal["done", "skipped", "failed"]


class ToolExecution(TypedDict):
    tool_name: str
    arguments: dict
    success: bool
    data: Any
    error: str | None
    latency_ms: float


class AgentState(TypedDict, total=False):
    # --- identity / input ---
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    request_id: str
    current_message: str
    conversation_history: list[dict]  # [{role, content}]
    last_shown_item_ids: list[str]

    # --- planning ---
    detected_intent: Intent
    extracted_constraints: ExtractedConstraints
    selected_tools: list[str]

    # --- execution ---
    tool_results: list[ToolExecution]
    candidate_items: list[dict]
    ranked_items: list[dict]

    # --- output ---
    response: str
    preferences_snapshot: dict | None

    # --- bookkeeping ---
    activity_log: list[ActivityEvent]
    errors: list[str]
    llm_latency_ms: float
    llm_token_usage: dict | None
