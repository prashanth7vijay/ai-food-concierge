from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.repositories.user_repository import UserRepository
from backend.schemas.chat import PreferenceOut, PreferenceUpdate


def get_preferences(db: Session, user_id: uuid.UUID) -> PreferenceOut:
    repo = UserRepository(db)
    pref = repo.get_preferences(user_id)
    if pref is None:
        return PreferenceOut()
    return PreferenceOut.model_validate(pref)


def update_preferences(db: Session, user_id: uuid.UUID, update: PreferenceUpdate) -> PreferenceOut:
    repo = UserRepository(db)
    repo.get_or_create_user(user_id)
    pref = repo.upsert_preferences(user_id, **update.model_dump(exclude_unset=True))
    db.commit()
    return PreferenceOut.model_validate(pref)
