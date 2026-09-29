from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.catalog_service import list_saved_items, remove_saved_item, save_item_for_user

router = APIRouter(tags=["saved-items"])


class SaveItemRequest(BaseModel):
    user_id: uuid.UUID
    menu_item_id: uuid.UUID


@router.post("/saved-items")
def create_saved_item(payload: SaveItemRequest, db: Session = Depends(get_db)):
    saved_id = save_item_for_user(db, payload.user_id, payload.menu_item_id)
    return {"saved_item_id": str(saved_id)}


@router.get("/saved-items")
def get_saved_items(user_id: uuid.UUID, db: Session = Depends(get_db)):
    return {"items": list_saved_items(db, user_id)}


@router.delete("/saved-items/{saved_item_id}", status_code=204)
def delete_saved_item(saved_item_id: uuid.UUID, db: Session = Depends(get_db)):
    remove_saved_item(db, saved_item_id)
    return None
