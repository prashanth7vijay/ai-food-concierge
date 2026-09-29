from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base
from backend.database.types import GUID, new_uuid
from backend.database.vector_type import EmbeddingVector


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cuisine: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_pure_veg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_band: Mapped[str] = mapped_column(String(20), nullable=False, default="mid")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )

    menu_items: Mapped[list[MenuItem]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_restaurants_cuisine_rating", "cuisine", "rating"),)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    cuisine: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    spice_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    tags: Mapped[str] = mapped_column(String(300), nullable=False, default="")  # comma-separated
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")

    __table_args__ = (
        Index("ix_menu_items_price_veg", "price", "is_vegetarian"),
        Index("ix_menu_items_cuisine_spice", "cuisine", "spice_level"),
    )

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]
