from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas.catalog import MenuItemOut
from backend.services.catalog_service import get_food_item

router = APIRouter(tags=["food"])


@router.get("/food/{item_id}", response_model=MenuItemOut)
def read_food_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> MenuItemOut:
    return get_food_item(db, item_id)
