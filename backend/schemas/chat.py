from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.catalog import RecommendationItem


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_vegetarian: bool | None = None
    preferred_cuisine: str | None = None
    spice_level: str | None = None
    max_budget: float | None = None


class PreferenceUpdate(BaseModel):
    is_vegetarian: bool | None = None
    preferred_cuisine: str | None = None
    spice_level: str | None = None
    max_budget: float | None = Field(default=None, ge=0)


class AgentActivityEvent(BaseModel):
    """A single high-level, safe-to-show execution step — NOT chain of
    thought. E.g. 'Applied budget filter', not the model's raw reasoning."""

    label: str
    status: Literal["done", "skipped", "failed"] = "done"


class ChatRequest(BaseModel):
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    agent_run_id: uuid.UUID
    reply: str
    intent: str | None = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    activity: list[AgentActivityEvent] = Field(default_factory=list)
    preferences: PreferenceOut | None = None
    errors: list[str] = Field(default_factory=list)
