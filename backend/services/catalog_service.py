from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository
from backend.repositories.user_repository import SavedItemRepository
from backend.schemas.catalog import MenuItemOut
from backend.utils.mappers import menu_item_to_out


def get_food_item(db: Session, item_id: uuid.UUID) -> MenuItemOut:
    repo = CatalogRepository(db)
    item = repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return menu_item_to_out(item)


def save_item_for_user(db: Session, user_id: uuid.UUID, menu_item_id: uuid.UUID) -> uuid.UUID:
    if CatalogRepository(db).get_by_id(menu_item_id) is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    saved = SavedItemRepository(db).add(user_id, menu_item_id)
    db.commit()
    return saved.id


def remove_saved_item(db: Session, saved_item_id: uuid.UUID) -> None:
    removed = SavedItemRepository(db).remove(saved_item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.commit()


def list_saved_items(db: Session, user_id: uuid.UUID) -> list[dict]:
    saved = SavedItemRepository(db).list_for_user(user_id)
    repo = CatalogRepository(db)
    out = []
    for s in saved:
        item = repo.get_by_id(s.menu_item_id)
        if item:
            out.append(
                {"saved_item_id": str(s.id), "item": menu_item_to_out(item).model_dump(mode="json")}
            )
    return out
