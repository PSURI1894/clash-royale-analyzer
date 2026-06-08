"""Phase 6 tests: rate limiter, TTL cache, scrape reconcile/seed, saved decks."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.db import Base, get_session
from cr_helper.main import app
from cr_helper.models import Card, CardMetaStat, MatchupEdge
from cr_helper.runtime import RateLimiter, TTLCache
from cr_helper.scrape.reconcile import reconcile
from cr_helper.scrape.seed import seed_scraped


# ---- runtime primitives ----

def test_rate_limiter_allows_then_blocks_per_key():
    rl = RateLimiter(per_min=3)
    assert [rl.allow("k") for _ in range(3)] == [True, True, True]
    assert rl.allow("k") is False        # budget spent
    assert rl.allow("other") is True     # separate bucket per key


def test_rate_limiter_zero_disables():
    rl = RateLimiter(per_min=0)
    assert all(rl.allow("k") for _ in range(50))


def test_ttl_cache_hit_miss_and_lru_evict():
    c = TTLCache(ttl=100, maxsize=2)
    assert c.get("a") is None
    c.set("a", 1)
    c.set("b", 2)
    assert c.get("a") == 1                # hit (makes 'a' most-recent)
    c.set("c", 3)                         # evicts LRU -> 'b'
    assert c.get("b") is None
    assert c.get("c") == 3
    assert c.stats()["size"] == 2


def test_ttl_cache_expiry():
    c = TTLCache(ttl=0)
    c.set("a", 1)
    assert c.get("a") is None             # already expired


# ---- scrape reconcile + seed ----

def test_seed_scraped_and_reconcile(session):
    session.add_all([
        CardMetaStat(card_key="inferno-tower", dataset="synthetic", games=100, wins=58, win_rate=0.58, usage=0.13),
        CardMetaStat(card_key="hog-rider", dataset="synthetic", games=100, wins=51, win_rate=0.51, usage=0.14),
    ])
    session.commit()
    meta = {
        "cards": [
            {"key": "inferno-tower", "win_rate": 0.575, "usage": 0.13},
            {"key": "hog-rider", "win_rate": 0.512, "usage": 0.14},
            {"key": "unknown-card", "win_rate": 0.60, "usage": 0.10},
        ],
        "counters": [{"a": "inferno-tower", "b": "golem", "win_rate": 0.72}],
    }
    n_cards, n_counters = seed_scraped(session, meta)
    assert (n_cards, n_counters) == (3, 1)

    assert len(session.scalars(select(CardMetaStat).where(CardMetaStat.dataset == "scraped")).all()) == 3
    edge = session.scalar(select(MatchupEdge).where(MatchupEdge.source == "scraped"))
    assert edge.source_key == "inferno-tower" and edge.confidence == 0.5

    report = reconcile(session, meta["cards"])
    assert report["compared"] == 2          # unknown-card has no mined counterpart
    assert report["agreement"] == "strong"  # deltas are tiny


# ---- saved decks ----

@pytest.fixture()
def deck_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    keys = [f"c{i}" for i in range(1, 9)]
    with maker() as s:
        for k in keys:
            s.add(Card(key=k, name=k.upper(), elixir=3, type="Troop"))
        s.commit()

    def override():
        with maker() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), keys
    app.dependency_overrides.clear()


def test_decks_require_token(deck_client):
    client, keys = deck_client
    assert client.post("/decks", json={"name": "x", "cards": keys}).status_code == 401


def test_decks_crud_is_token_scoped(deck_client):
    client, keys = deck_client
    mine = {"X-User-Token": "user-abc123"}

    created = client.post("/decks", json={"name": "My Cycle", "cards": keys}, headers=mine)
    assert created.status_code == 200
    deck_id = created.json()["id"]

    listed = client.get("/decks", headers=mine).json()
    assert len(listed) == 1 and listed[0]["name"] == "My Cycle"

    assert client.get("/decks", headers={"X-User-Token": "someone-else"}).json() == []  # scoped

    assert client.delete(f"/decks/{deck_id}", headers=mine).status_code == 200
    assert client.get("/decks", headers=mine).json() == []


def test_decks_reject_invalid_deck(deck_client):
    client, keys = deck_client
    r = client.post("/decks", json={"name": "bad", "cards": keys[:7]}, headers={"X-User-Token": "user-abc123"})
    assert r.status_code == 422
