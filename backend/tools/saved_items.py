from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository
from backend.repositories.user_repository import SavedItemRepository
from backend.tools.base import ToolError, ToolResult, run_tool, validate_params


class SaveItemParams(BaseModel):
    user_id: uuid.UUID
    menu_item_id: uuid.UUID


def save_item(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(SaveItemParams, raw_args)
        if CatalogRepository(db).get_by_id(params.menu_item_id) is None:
            raise ToolError(f"Menu item {params.menu_item_id} does not exist")
        saved = SavedItemRepository(db).add(params.user_id, params.menu_item_id)
        return {"saved_item_id": str(saved.id)}

    return run_tool("save_item", raw_args, _run)


class RemoveSavedItemParams(BaseModel):
    saved_item_id: uuid.UUID


def remove_saved_item(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(RemoveSavedItemParams, raw_args)
        removed = SavedItemRepository(db).remove(params.saved_item_id)
        if not removed:
            raise ToolError(f"Saved item {params.saved_item_id} not found")
        return {"removed": True}

    return run_tool("remove_saved_item", raw_args, _run)
