"""Tests for Phase 3 mining: parser (real API shape), synthetic ETL, ensemble blend."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.db import Base
from cr_helper.graph.repo import SqlGraphRepo
from cr_helper.mining.aggregate import aggregate
from cr_helper.mining.parse import CardIndex, parse_battle
from cr_helper.mining.pipeline import build_synthetic_source, extract_into
from cr_helper.models import Card, CardMetaStat, MatchupEdge

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "battlelog_sample.json"

NAME_TO_KEY = {
    "hog rider": "hog-rider", "musketeer": "musketeer", "ice golem": "ice-golem",
    "ice spirit": "ice-spirit", "skeletons": "skeletons", "cannon": "cannon",
    "fireball": "fireball", "the log": "the-log", "golem": "golem",
    "night witch": "night-witch", "baby dragon": "baby-dragon", "mega minion": "mega-minion",
    "lightning": "lightning", "tornado": "tornado", "lumberjack": "lumberjack",
    "barbarian hut": "barbarian-hut",
}


# ---- parser against the real official-API battle-log shape ----

def test_parse_real_shape_and_filters():
    idx = CardIndex(by_id={}, by_name=NAME_TO_KEY)
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    parsed = [parse_battle(b, idx, "api") for b in raw]
    ok = [p for p in parsed if p is not None]

    assert len(ok) == 2  # 2v2 battle and the draw are filtered out
    win, loss = ok
    assert win.won is True
    assert win.team_cards[0] == "hog-rider"
    assert len(win.team_cards) == 8
    assert "golem" in win.opponent_cards
    assert loss.won is False
    assert win.battle_uid != loss.battle_uid


# ---- synthetic ETL + ensemble ----

@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    cards = [
        ("inferno-tower", 1, "Inferno Tower"), ("golem", 2, "Golem"), ("pekka", 3, "P.E.K.K.A"),
        ("musketeer", 4, "Musketeer"), ("balloon", 5, "Balloon"), ("mega-minion", 6, "Mega Minion"),
        ("hog-rider", 7, "Hog Rider"), ("cannon", 8, "Cannon"), ("skeleton-army", 9, "Skeleton Army"),
        ("lava-hound", 10, "Lava Hound"), ("mini-pekka", 11, "Mini P.E.K.K.A"), ("wizard", 12, "Wizard"),
    ]
    edges = [
        ("inferno-tower", "golem", 0.9), ("pekka", "golem", 0.85), ("inferno-tower", "lava-hound", 0.9),
        ("musketeer", "balloon", 0.75), ("mega-minion", "balloon", 0.7), ("cannon", "hog-rider", 0.8),
        ("mini-pekka", "hog-rider", 0.75), ("skeleton-army", "pekka", 0.8), ("wizard", "balloon", 0.6),
    ]
    with maker() as s:
        for key, cid, name in cards:
            s.add(Card(key=key, card_id=cid, name=name, elixir=4, type="Troop"))
        for a, b, v in edges:
            s.add(MatchupEdge(source_key=a, target_key=b, relation="counters",
                              value=v, source="curated", confidence=0.6))
        s.commit()
    with maker() as s:
        yield s


def _mine(session, seed: int, n: int = 3000):
    idx = CardIndex.from_session(session)
    inserted = extract_into(session, build_synthetic_source(session, seed=seed), "synthetic", idx, n)
    summary = aggregate(session, "synthetic", min_sample=20)
    return inserted, summary


def test_synthetic_mining_recovers_counter_direction(session):
    inserted, summary = _mine(session, seed=1)
    assert inserted > 1000
    assert summary["mined_edges"] > 0

    mined = {
        (e.source_key, e.target_key): e
        for e in session.scalars(
            select(MatchupEdge).where(MatchupEdge.source == "mined", MatchupEdge.relation == "counters")
        )
    }
    edge = mined[("inferno-tower", "golem")]
    assert edge.value > 0.5            # mining recovers the curated counter's direction
    assert edge.sample_size >= 20


def test_mined_blends_with_curated_prior(session):
    _mine(session, seed=2)
    answers = {e.source_key: e for e in SqlGraphRepo(session).answers_to("golem")}
    inferno = answers["inferno-tower"]

    sources = {c.source for c in inferno.components}
    assert {"curated", "mined"} <= sources
    mined_val = next(c.value for c in inferno.components if c.source == "mined")
    assert min(0.9, mined_val) <= inferno.value <= max(0.9, mined_val)


def test_card_meta_stats_written(session):
    _mine(session, seed=3)
    metas = session.scalars(
        select(CardMetaStat).where(CardMetaStat.dataset == "synthetic")
    ).all()
    assert len(metas) >= 8
    assert all(0.0 <= m.win_rate <= 1.0 for m in metas)
    assert all(0.0 <= m.usage <= 1.0 for m in metas)
