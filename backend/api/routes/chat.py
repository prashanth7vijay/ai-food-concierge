from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.guardrails import GuardrailViolation
from backend.core.rate_limit import get_rate_limiter
from backend.database.session import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import handle_chat_message

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(
    payload: ChatRequest, request: Request, db: Session = Depends(get_db)
) -> ChatResponse:
    settings = get_settings()
    limiter = get_rate_limiter()
    if not limiter.allow(str(payload.user_id), settings.RATE_LIMIT_REQUESTS_PER_MINUTE):
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")

    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        return handle_chat_message(db, payload, request_id)
    except GuardrailViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
