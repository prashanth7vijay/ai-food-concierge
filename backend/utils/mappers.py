from __future__ import annotations

from backend.models.catalog import MenuItem
from backend.schemas.catalog import MenuItemOut


def menu_item_to_out(item: MenuItem) -> MenuItemOut:
    return MenuItemOut(
        id=item.id,
        name=item.name,
        description=item.description,
        price=item.price,
        cuisine=item.cuisine,
        is_vegetarian=item.is_vegetarian,
        spice_level=item.spice_level,
        tags=item.tag_list,
        rating=item.rating,
        restaurant_name=item.restaurant.name if item.restaurant else "",
        restaurant_id=item.restaurant_id,
    )
