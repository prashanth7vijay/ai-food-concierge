from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SpiceLevel = Literal["mild", "medium", "spicy"]


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    cuisine: str
    area: str
    rating: float
    is_pure_veg: bool
    price_band: str


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    price: float
    cuisine: str
    is_vegetarian: bool
    spice_level: str
    tags: list[str]
    rating: float
    restaurant_name: str
    restaurant_id: uuid.UUID


class RecommendationItem(BaseModel):
    """A ranked recommendation shown to the user, with the reasoning
    exposed at a safe, high-level, non-chain-of-thought granularity."""

    item: MenuItemOut
    score: float
    reason: str
    match_breakdown: dict[str, float] = Field(default_factory=dict)


class SearchFoodParams(BaseModel):
    """Strict input schema for the search_food tool. This is the contract
    the LLM's tool call is validated against before anything touches the
    database — see tools/search_food.py."""

    query: str | None = None
    max_price: float | None = Field(default=None, ge=0)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    cuisine: str | None = None
    dietary_preference: Literal["vegetarian", "non_vegetarian", "any"] = "any"
    spice_level: SpiceLevel | None = None
    limit: int = Field(default=10, ge=1, le=50)


class CompareItemsParams(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=2, max_length=5)
