from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.user_repository import ConversationRepository

router = APIRouter(tags=["conversations"])


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    repo = ConversationRepository(db)
    history = repo.recent_history(conversation_id, limit=100)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found or empty")
    return {
        "conversation_id": str(conversation_id),
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in history
        ],
    }
