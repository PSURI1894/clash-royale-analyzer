"""API tests against an in-memory DB (dependency-overridden session)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.db import Base, get_session
from cr_helper.main import app
from cr_helper.models import Card, CardStats


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    with testing_session() as s:
        knight = Card(
            key="knight", name="Knight", elixir=3, rarity="Common", type="Troop", arena=0
        )
        knight.stats = CardStats(
            card_key="knight", hitpoints=690, damage=79, dps=65.83, hit_speed_ms=1200,
            range_tiles=1.2, speed_label="Medium", targets_ground=True, count=1,
        )
        giant = Card(key="giant", name="Giant", elixir=5, rarity="Rare", type="Troop", arena=0)
        s.add_all([knight, giant])
        s.commit()

    def override_session():
        with testing_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    # No `with` block: avoids triggering the lifespan init_db() on the real engine.
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_cards(client: TestClient):
    r = client.get("/cards")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert names == ["Knight", "Giant"]  # ordered by elixir then name


def test_list_cards_filtered(client: TestClient):
    r = client.get("/cards", params={"max_elixir": 3})
    assert [c["key"] for c in r.json()] == ["knight"]


def test_get_card_detail(client: TestClient):
    r = client.get("/cards/knight")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Knight"
    assert body["stats"]["dps"] == 65.83
    assert body["stats"]["targets_ground"] is True


def test_get_card_404(client: TestClient):
    assert client.get("/cards/nonexistent").status_code == 404
