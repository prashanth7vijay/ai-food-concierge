from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.repositories.user_repository import ConversationRepository
from backend.tools.base import ToolResult, run_tool, validate_params


class GetConversationContextParams(BaseModel):
    conversation_id: uuid.UUID
    limit: int = Field(default=6, ge=1, le=20)


def get_conversation_context(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(GetConversationContextParams, raw_args)
        repo = ConversationRepository(db)
        history = repo.recent_history(params.conversation_id, limit=params.limit)
        last_shown = repo.last_shown_item_ids(params.conversation_id)
        return {
            "history": [{"role": m.role, "content": m.content} for m in history],
            "last_shown_item_ids": [str(i) for i in last_shown],
        }

    return run_tool("get_conversation_context", raw_args, _run)
