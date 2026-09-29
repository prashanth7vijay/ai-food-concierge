"""
Reproducible seed/import pipeline (spec section 9).

Usage:
    python -m backend.scripts.seed_data

Reads backend/data/demo_dataset.json (a fully synthetic, static dataset —
see the file's _dataset_notice), validates every record against a strict
schema, cleans/normalizes fields, de-duplicates by (restaurant name, dish
name), and loads the result into the configured database. The application
never depends on this external file being present at *runtime* — ingestion
is a one-time/CI step, not something the API reads from disk on each
request.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.core.logging import configure_logging, get_logger
from backend.database.session import Base, SessionLocal, engine
from backend.models.catalog import MenuItem, Restaurant
from backend.tools.embeddings import get_embedding_provider

logger = get_logger("seed")

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_dataset.json"


class RawMenuItem(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    price: float = Field(ge=0)
    is_vegetarian: bool
    spice_level: Literal["mild", "medium", "spicy"]
    tags: str = ""
    rating: float = Field(ge=0, le=5)

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class RawRestaurant(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cuisine: str = Field(min_length=1, max_length=100)
    area: str = ""
    rating: float = Field(ge=0, le=5)
    is_pure_veg: bool
    price_band: Literal["budget", "mid", "premium"]
    menu: list[RawMenuItem]


def load_raw_dataset(path: Path = DATASET_PATH) -> list[RawRestaurant]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    validated: list[RawRestaurant] = []
    seen_names: set[str] = set()
    for entry in raw.get("restaurants", []):
        try:
            restaurant = RawRestaurant.model_validate(entry)
        except ValidationError as exc:
            logger.warning(f"Skipping invalid restaurant record: {exc}")
            continue
        key = restaurant.name.strip().lower()
        if key in seen_names:
            logger.warning(f"Duplicate restaurant skipped: {restaurant.name}")
            continue
        seen_names.add(key)

        # De-dupe menu items within a restaurant by normalized dish name.
        seen_dishes: set[str] = set()
        deduped_menu = []
        for item in restaurant.menu:
            dish_key = item.name.strip().lower()
            if dish_key in seen_dishes:
                continue
            seen_dishes.add(dish_key)
            deduped_menu.append(item)
        restaurant.menu = deduped_menu
        validated.append(restaurant)

    return validated


def seed_database(reset: bool = False) -> dict:
    configure_logging("INFO")
    Base.metadata.create_all(bind=engine)

    restaurants = load_raw_dataset()
    provider = get_embedding_provider()
    db = SessionLocal()
    created_restaurants = 0
    created_items = 0

    try:
        if reset:
            db.query(MenuItem).delete()
            db.query(Restaurant).delete()
            db.commit()

        existing_names = {r.name for r in db.query(Restaurant).all()}

        for raw in restaurants:
            if raw.name in existing_names:
                logger.info(f"Restaurant already seeded, skipping: {raw.name}")
                continue

            restaurant = Restaurant(
                name=raw.name,
                cuisine=raw.cuisine,
                area=raw.area,
                rating=raw.rating,
                is_pure_veg=raw.is_pure_veg,
                price_band=raw.price_band,
            )
            db.add(restaurant)
            db.flush()
            created_restaurants += 1

            for item in raw.menu:
                embedding_text = f"{item.name} {item.description} {item.tags}"
                menu_item = MenuItem(
                    restaurant_id=restaurant.id,
                    name=item.name,
                    description=item.description,
                    price=item.price,
                    cuisine=raw.cuisine,
                    is_vegetarian=item.is_vegetarian,
                    spice_level=item.spice_level,
                    tags=item.tags,
                    rating=item.rating,
                    is_available=True,
                    embedding=provider.embed(embedding_text),
                )
                db.add(menu_item)
                created_items += 1

        db.commit()
    finally:
        db.close()

    summary = {"restaurants_created": created_restaurants, "menu_items_created": created_items}
    logger.info(f"Seed complete: {summary}")
    return summary


if __name__ == "__main__":
    import sys

    reset_flag = "--reset" in sys.argv
    result = seed_database(reset=reset_flag)
    print(json.dumps(result, indent=2))
