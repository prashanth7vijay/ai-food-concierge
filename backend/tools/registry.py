from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from backend.tools.base import ToolResult
from backend.tools.compare import compare_items
from backend.tools.conversation_context import get_conversation_context
from backend.tools.food_details import get_food_details, get_menu
from backend.tools.preferences import get_user_preferences, save_preference
from backend.tools.saved_items import remove_saved_item, save_item
from backend.tools.search_food import search_food

ToolFn = Callable[[Session, dict], ToolResult]

# This is the ONLY place tool names are mapped to executable code. The
# agent graph looks up tool names here — an LLM proposing a tool name that
# isn't in this dict is rejected before anything runs (guardrail: "invalid
# tool names", spec section 13).
TOOL_REGISTRY: dict[str, ToolFn] = {
    "search_food": search_food,
    "get_food_details": get_food_details,
    "get_menu": get_menu,
    "compare_items": compare_items,
    "get_user_preferences": get_user_preferences,
    "save_preference": save_preference,
    "get_conversation_context": get_conversation_context,
    "save_item": save_item,
    "remove_saved_item": remove_saved_item,
}


def execute_tool(tool_name: str, db: Session, raw_args: dict) -> ToolResult:
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error=f"Unknown tool '{tool_name}' — rejected by guardrail.",
            arguments=raw_args,
        )
    return fn(db, raw_args)
