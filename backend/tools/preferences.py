from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.repositories.user_repository import UserRepository
from backend.tools.base import ToolResult, run_tool, validate_params


class GetUserPreferencesParams(BaseModel):
    user_id: uuid.UUID


def get_user_preferences(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(GetUserPreferencesParams, raw_args)
        repo = UserRepository(db)
        pref = repo.get_preferences(params.user_id)
        if pref is None:
            return {
                "is_vegetarian": None,
                "preferred_cuisine": None,
                "spice_level": None,
                "max_budget": None,
            }
        return {
            "is_vegetarian": pref.is_vegetarian,
            "preferred_cuisine": pref.preferred_cuisine,
            "spice_level": pref.spice_level,
            "max_budget": pref.max_budget,
        }

    return run_tool("get_user_preferences", raw_args, _run)


class SavePreferenceParams(BaseModel):
    """Strict schema: only these four stable preference fields can ever be
    written, and each is validated/bounded. Nothing else the user says
    becomes 'preference' data — see agents/memory.py for the confidence
    gate that decides *whether* to call this tool at all (spec section 12:
    do not persist every conversational statement)."""

    user_id: uuid.UUID
    is_vegetarian: bool | None = None
    preferred_cuisine: str | None = Field(default=None, max_length=100)
    spice_level: Literal["mild", "medium", "spicy"] | None = None
    max_budget: float | None = Field(default=None, ge=0, le=100_000)


def save_preference(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(SavePreferenceParams, raw_args)
        repo = UserRepository(db)
        repo.get_or_create_user(params.user_id)
        pref = repo.upsert_preferences(
            params.user_id,
            is_vegetarian=params.is_vegetarian,
            preferred_cuisine=params.preferred_cuisine,
            spice_level=params.spice_level,
            max_budget=params.max_budget,
        )
        return {
            "is_vegetarian": pref.is_vegetarian,
            "preferred_cuisine": pref.preferred_cuisine,
            "spice_level": pref.spice_level,
            "max_budget": pref.max_budget,
        }

    return run_tool("save_preference", raw_args, _run)
