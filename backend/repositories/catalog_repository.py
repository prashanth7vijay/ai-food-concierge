from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from backend.models.catalog import MenuItem, Restaurant


class CatalogRepository:
    """Encapsulates all SQL access to restaurants/menu_items. No other
    module is allowed to issue raw queries against these tables — tools
    and services call through here, keeping the LLM/agent layer strictly
    read-only via validated, parameterized methods (never arbitrary SQL)."""

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self) -> Select:
        return (
            select(MenuItem)
            .options(joinedload(MenuItem.restaurant))
            .where(MenuItem.is_available.is_(True))
        )

    def search(
        self,
        *,
        max_price: float | None = None,
        min_rating: float | None = None,
        cuisine: str | None = None,
        dietary_preference: str = "any",
        spice_level: str | None = None,
        text_query: str | None = None,
        limit: int = 10,
    ) -> list[MenuItem]:
        stmt = self._base_query()

        if max_price is not None:
            stmt = stmt.where(MenuItem.price <= max_price)
        if min_rating is not None:
            stmt = stmt.where(MenuItem.rating >= min_rating)
        if cuisine:
            stmt = stmt.where(MenuItem.cuisine.ilike(f"%{cuisine}%"))
        if dietary_preference == "vegetarian":
            stmt = stmt.where(MenuItem.is_vegetarian.is_(True))
        elif dietary_preference == "non_vegetarian":
            stmt = stmt.where(MenuItem.is_vegetarian.is_(False))
        if spice_level:
            stmt = stmt.where(MenuItem.spice_level == spice_level)
        if text_query:
            like = f"%{text_query.lower()}%"
            stmt = stmt.where(
                (MenuItem.name.ilike(like))
                | (MenuItem.description.ilike(like))
                | (MenuItem.tags.ilike(like))
            )

        stmt = stmt.order_by(MenuItem.rating.desc()).limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_all_available(self) -> list[MenuItem]:
        """Used by the semantic-retrieval layer for in-memory cosine
        similarity when running on SQLite (no pgvector ANN index)."""
        stmt = self._base_query()
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_by_ids(self, item_ids: list[uuid.UUID]) -> list[MenuItem]:
        stmt = self._base_query().where(MenuItem.id.in_(item_ids))
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_by_id(self, item_id: uuid.UUID) -> MenuItem | None:
        stmt = self._base_query().where(MenuItem.id == item_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_restaurants(self) -> list[Restaurant]:
        return list(self.db.execute(select(Restaurant)).scalars().all())
