from __future__ import annotations

import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.session import Base
from backend.models.catalog import MenuItem, Restaurant


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_catalog(db_session: Session):
    """A small, hand-crafted catalog (independent of the demo JSON dataset)
    so unit/integration tests don't depend on that file's exact contents."""
    r1 = Restaurant(
        name="Test North Indian",
        cuisine="North Indian",
        area="Test Area",
        rating=4.5,
        is_pure_veg=True,
        price_band="mid",
    )
    r2 = Restaurant(
        name="Test Continental",
        cuisine="Continental",
        area="Test Area",
        rating=4.2,
        is_pure_veg=False,
        price_band="mid",
    )
    db_session.add_all([r1, r2])
    db_session.flush()

    items = [
        MenuItem(
            restaurant_id=r1.id,
            name="Paneer Curry",
            description="Rich paneer curry",
            price=280,
            cuisine="North Indian",
            is_vegetarian=True,
            spice_level="spicy",
            tags="paneer,curry",
            rating=4.6,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r1.id,
            name="Dal Fry",
            description="Comforting lentils",
            price=150,
            cuisine="North Indian",
            is_vegetarian=True,
            spice_level="mild",
            tags="dal,comforting",
            rating=4.3,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r1.id,
            name="Butter Chicken",
            description="Creamy chicken curry",
            price=350,
            cuisine="North Indian",
            is_vegetarian=False,
            spice_level="medium",
            tags="chicken,curry",
            rating=4.7,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r2.id,
            name="Garden Salad",
            description="Light salad with greens",
            price=200,
            cuisine="Continental",
            is_vegetarian=True,
            spice_level="mild",
            tags="salad,light,healthy",
            rating=4.1,
            is_available=True,
        ),
        MenuItem(
            restaurant_id=r2.id,
            name="Unavailable Soup",
            description="Should never show up",
            price=100,
            cuisine="Continental",
            is_vegetarian=True,
            spice_level="mild",
            tags="soup,light",
            rating=4.9,
            is_available=False,
        ),
    ]
    db_session.add_all(items)
    db_session.commit()
    return {"restaurants": [r1, r2], "items": items}


@pytest.fixture()
def api_client(db_session):
    """FastAPI TestClient wired to the same in-memory db_session via
    dependency override, so integration tests hit real routes/services/
    agent graph without touching a real network or a real Postgres."""
    from fastapi.testclient import TestClient

    from backend.database.session import get_db
    from backend.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def new_uuid_str() -> str:
    return str(uuid.uuid4())
