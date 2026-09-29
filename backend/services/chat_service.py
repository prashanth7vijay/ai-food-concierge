from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from backend.agents.graph import build_agent_graph
from backend.agents.llm_provider import get_llm_provider
from backend.agents.state import AgentState
from backend.core.guardrails import flag_prompt_injection, validate_user_message
from backend.core.logging import get_logger, log_event
from backend.repositories.user_repository import (
    AgentRunRepository,
    ConversationRepository,
    UserRepository,
)
from backend.schemas.chat import AgentActivityEvent, ChatRequest, ChatResponse, PreferenceOut

logger = get_logger("chat_service")


def handle_chat_message(db: Session, request: ChatRequest, request_id: str) -> ChatResponse:
    message = validate_user_message(request.message)
    if flag_prompt_injection(message):
        log_event(logger, logging.WARNING, "possible_prompt_injection", request_id=request_id)

    user_repo = UserRepository(db)
    convo_repo = ConversationRepository(db)
    run_repo = AgentRunRepository(db)

    user_repo.get_or_create_user(request.user_id)
    conversation = convo_repo.get_or_create(request.conversation_id, request.user_id)
    convo_repo.add_message(conversation.id, role="user", content=message)

    agent_run = run_repo.start_run(conversation.id, request_id=request_id, user_message=message)

    llm = get_llm_provider()
    graph = build_agent_graph(db, llm)

    initial_state: AgentState = {
        "conversation_id": conversation.id,
        "user_id": request.user_id,
        "request_id": request_id,
        "current_message": message,
        "activity_log": [],
        "errors": [],
    }

    start = time.perf_counter()
    try:
        final_state: AgentState = graph.invoke(initial_state)
        status = "completed"
        error_message = None
    except Exception as exc:  # noqa: BLE001 - graph must never crash the request
        log_event(
            logger, logging.ERROR, "agent_graph_failed", error=str(exc), request_id=request_id
        )
        final_state = {
            **initial_state,
            "response": "Something went wrong on my end — please try again.",
            "errors": [str(exc)],
            "ranked_items": [],
            "detected_intent": "unknown",
            "activity_log": initial_state["activity_log"],
        }
        status = "failed"
        error_message = str(exc)
    total_latency_ms = (time.perf_counter() - start) * 1000

    # Persist tool call audit rows
    for tr in final_state.get("tool_results", []):
        run_repo.record_tool_call(
            agent_run.id,
            tool_name=tr["tool_name"],
            arguments=tr["arguments"],
            result_summary={"success": tr["success"]},
            status="success" if tr["success"] else "failed",
            latency_ms=tr["latency_ms"],
            error_message=tr.get("error"),
        )

    run_repo.finish_run(
        agent_run,
        status=status,
        detected_intent=final_state.get("detected_intent"),
        extracted_constraints=final_state.get("extracted_constraints"),
        total_latency_ms=total_latency_ms,
        llm_latency_ms=final_state.get("llm_latency_ms"),
        token_usage=final_state.get("llm_token_usage"),
        error_message=error_message,
    )

    shown_ids = [uuid.UUID(i["item"]["id"]) for i in final_state.get("ranked_items", [])]
    convo_repo.add_message(
        conversation.id,
        role="assistant",
        content=final_state.get("response", ""),
        shown_item_ids=shown_ids or None,
    )

    pref = user_repo.get_preferences(request.user_id)
    preferences_out = PreferenceOut.model_validate(pref) if pref else PreferenceOut()

    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        agent_run_id=agent_run.id,
        reply=final_state.get("response", ""),
        intent=final_state.get("detected_intent"),
        recommendations=final_state.get("ranked_items", []),
        activity=[AgentActivityEvent(**e) for e in final_state.get("activity_log", [])],
        preferences=preferences_out,
        errors=final_state.get("errors", []),
    )
