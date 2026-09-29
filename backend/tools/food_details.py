from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository
from backend.tools.base import ToolError, ToolResult, run_tool, validate_params
from backend.utils.mappers import menu_item_to_out


class GetFoodDetailsParams(BaseModel):
    item_id: uuid.UUID


def get_food_details(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(GetFoodDetailsParams, raw_args)
        repo = CatalogRepository(db)
        item = repo.get_by_id(params.item_id)
        if item is None:
            raise ToolError(f"No menu item found with id {params.item_id}")
        return {"item": menu_item_to_out(item).model_dump(mode="json")}

    return run_tool("get_food_details", raw_args, _run)


class GetMenuParams(BaseModel):
    restaurant_id: uuid.UUID


def get_menu(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params = validate_params(GetMenuParams, raw_args)
        repo = CatalogRepository(db)
        items = [i for i in repo.get_all_available() if i.restaurant_id == params.restaurant_id]
        if not items:
            raise ToolError(f"No available menu items for restaurant {params.restaurant_id}")
        return {"items": [menu_item_to_out(i).model_dump(mode="json") for i in items]}

    return run_tool("get_menu", raw_args, _run)
