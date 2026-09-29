from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas.chat import PreferenceOut, PreferenceUpdate
from backend.services.preference_service import get_preferences, update_preferences

router = APIRouter(tags=["preferences"])


@router.get("/preferences", response_model=PreferenceOut)
def read_preferences(user_id: uuid.UUID, db: Session = Depends(get_db)) -> PreferenceOut:
    return get_preferences(db, user_id)


@router.put("/preferences", response_model=PreferenceOut)
def write_preferences(
    user_id: uuid.UUID, payload: PreferenceUpdate, db: Session = Depends(get_db)
) -> PreferenceOut:
    return update_preferences(db, user_id, payload)
