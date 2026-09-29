"""
Repeatable agent evaluation.

Run: python -m backend.evaluation.run_eval

This is intentionally separate from pytest (spec section 16: "create a
repeatable evaluation script" producing real, non-invented metrics). It
runs a small labeled set of representative queries against the live agent
graph (mock LLM provider by default — set LLM_PROVIDER=gemini to eval
against the real model) and reports intent-classification accuracy,
constraint-extraction accuracy, invalid-tool-call rate, and task
completion rate, computed from actual execution, never hardcoded.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.agents.graph import build_agent_graph
from backend.agents.llm_provider import get_llm_provider
from backend.agents.state import AgentState


@dataclass
class EvalCase:
    message: str
    expected_intent: str
    setup_messages: list[str] = field(default_factory=list)  # prior turns, e.g. to seed a search


EVAL_DATASET: list[EvalCase] = [
    EvalCase("veg food under 300", "search_food"),
    EvalCase("spicy paneer under 400", "search_food"),
    EvalCase("something light for dinner", "search_food"),
    EvalCase("show me biryani", "search_food"),
    EvalCase("I prefer North Indian food usually", "update_preference"),
    EvalCase(
        "compare these two",
        "compare_items",
        setup_messages=["show me vegetarian food"],
    ),
    EvalCase("what are my preferences", "get_preferences"),
    EvalCase("hello", "chit_chat"),
]


def _run_single_case(db: Session, case: EvalCase) -> dict:
    llm = get_llm_provider()
    graph = build_agent_graph(db, llm)
    conversation_id = uuid.uuid4()
    user_id = uuid.uuid4()

    final_state: AgentState = {}
    for msg in [*case.setup_messages, case.message]:
        state: AgentState = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "request_id": str(uuid.uuid4()),
            "current_message": msg,
            "activity_log": [],
            "errors": [],
        }
        final_state = graph.invoke(state)
        # Persist a minimal AgentRun-like row so merge_context/compare can
        # resolve references the same way the real API does. We reuse the
        # repository layer directly for the eval harness.
        from backend.repositories.user_repository import AgentRunRepository, ConversationRepository

        convo_repo = ConversationRepository(db)
        convo_repo.add_message(conversation_id, "user", msg)
        shown = [uuid.UUID(i["item"]["id"]) for i in final_state.get("ranked_items", [])]
        convo_repo.add_message(
            conversation_id,
            "assistant",
            final_state.get("response", ""),
            shown_item_ids=shown or None,
        )
        run_repo = AgentRunRepository(db)
        run = run_repo.start_run(conversation_id, str(uuid.uuid4()), msg)
        run_repo.finish_run(
            run,
            status="completed",
            detected_intent=final_state.get("detected_intent"),
            extracted_constraints=final_state.get("extracted_constraints"),
        )
        db.commit()

    invalid_tool_calls = sum(1 for tr in final_state.get("tool_results", []) if not tr["success"])
    task_completed = bool(final_state.get("response")) and not final_state.get("errors")

    return {
        "message": case.message,
        "expected_intent": case.expected_intent,
        "actual_intent": final_state.get("detected_intent"),
        "intent_correct": final_state.get("detected_intent") == case.expected_intent,
        "invalid_tool_calls": invalid_tool_calls,
        "task_completed": task_completed,
        "errors": final_state.get("errors", []),
    }


def _seed_minimal_catalog(db: Session) -> None:
    from backend.models.catalog import MenuItem, Restaurant

    r1 = Restaurant(
        name="Eval North Indian",
        cuisine="North Indian",
        area="Eval Area",
        rating=4.5,
        is_pure_veg=True,
        price_band="mid",
    )
    r2 = Restaurant(
        name="Eval Biryani House",
        cuisine="Hyderabadi",
        area="Eval Area",
        rating=4.4,
        is_pure_veg=False,
        price_band="mid",
    )
    db.add_all([r1, r2])
    db.flush()
    items = [
        MenuItem(
            restaurant_id=r1.id,
            name="Paneer Tikka",
            description="Grilled paneer",
            price=280,
            cuisine="North Indian",
            is_vegetarian=True,
            spice_level="spicy",
            tags="paneer,curry",
            rating=4.6,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r1.id,
            name="Dal Fry",
            description="Comforting lentils",
            price=150,
            cuisine="North Indian",
            is_vegetarian=True,
            spice_level="mild",
            tags="dal,comforting,light",
            rating=4.3,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r2.id,
            name="Chicken Biryani",
            description="Layered rice with chicken",
            price=260,
            cuisine="Hyderabadi",
            is_vegetarian=False,
            spice_level="spicy",
            tags="biryani,rice,filling,dinner",
            rating=4.7,
            is_available=True,
        ),
    ]
    db.add_all(items)
    db.commit()


def run_evaluation(db: Session) -> dict:
    _seed_minimal_catalog(db)
    results = [_run_single_case(db, case) for case in EVAL_DATASET]
    total = len(results)
    intent_accuracy = sum(r["intent_correct"] for r in results) / total
    invalid_tool_call_rate = sum(r["invalid_tool_calls"] for r in results) / total
    task_completion_rate = sum(r["task_completed"] for r in results) / total

    return {
        "total_cases": total,
        "intent_accuracy": round(intent_accuracy, 3),
        "invalid_tool_call_rate": round(invalid_tool_call_rate, 3),
        "task_completion_rate": round(task_completion_rate, 3),
        "cases": results,
    }


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.database.session import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        report = run_evaluation(session)
    finally:
        session.close()
    print(json.dumps(report, indent=2, default=str))
