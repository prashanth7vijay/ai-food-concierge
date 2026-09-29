from __future__ import annotations

from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository
from backend.schemas.catalog import CompareItemsParams
from backend.tools.base import ToolError, ToolResult, run_tool, validate_params
from backend.utils.mappers import menu_item_to_out


def compare_items(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params: CompareItemsParams = validate_params(CompareItemsParams, raw_args)
        repo = CatalogRepository(db)
        items = repo.get_by_ids(params.item_ids)
        found_ids = {i.id for i in items}
        missing = [str(i) for i in params.item_ids if i not in found_ids]
        if missing:
            raise ToolError(f"Item id(s) not found or unavailable: {missing}")

        rows = [menu_item_to_out(i) for i in items]
        cheapest = min(rows, key=lambda r: r.price)
        highest_rated = max(rows, key=lambda r: r.rating)
        lightest_tags = {"salad", "soup", "steamed", "grilled", "clear soup"}
        lighter = min(
            rows,
            key=lambda r: (0 if any(t in lightest_tags for t in r.tags) else 1, r.price),
        )

        return {
            "items": [r.model_dump(mode="json") for r in rows],
            "summary": {
                "cheapest_id": str(cheapest.id),
                "highest_rated_id": str(highest_rated.id),
                "likely_lighter_id": str(lighter.id),
            },
        }

    return run_tool("compare_items", raw_args, _run)
