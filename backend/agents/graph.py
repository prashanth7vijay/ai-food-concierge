"""
The explicit stateful agent workflow (spec section 5):

START
 -> load_conversation_context
 -> understand_request              (LLM: intent + structured constraints)
 -> merge_context                    (short-term memory: inherit prior search filters)
 -> determine_tools                  (conditional routing by intent)
 -> execute_tools                    (deterministic tool layer)
 -> validate_and_rank                (validate tool output shape)
 -> generate_response
 -> finalize
END

This is intentionally NOT "User -> LLM -> Response". Only `understand_request`
calls the LLM; everything downstream is deterministic, inspectable, and
independently unit-testable.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from backend.agents.llm_provider import LLMProvider
from backend.agents.nodes import (
    determine_tools_node,
    execute_tools_node,
    finalize_node,
    generate_response_node,
    load_conversation_context_node,
    merge_context_node,
    understand_request_node,
    validate_and_rank_node,
)
from backend.agents.state import AgentState


def build_agent_graph(db: Session, llm: LLMProvider):
    graph = StateGraph(AgentState)

    graph.add_node("load_context", load_conversation_context_node(db))
    graph.add_node("understand_request", understand_request_node(llm))
    graph.add_node("merge_context", merge_context_node(db))
    graph.add_node("determine_tools", determine_tools_node)
    graph.add_node("execute_tools", execute_tools_node(db))
    graph.add_node("validate_and_rank", validate_and_rank_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "understand_request")
    graph.add_edge("understand_request", "merge_context")
    graph.add_edge("merge_context", "determine_tools")
    graph.add_edge("determine_tools", "execute_tools")
    graph.add_edge("execute_tools", "validate_and_rank")
    graph.add_edge("validate_and_rank", "generate_response")
    graph.add_edge("generate_response", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
