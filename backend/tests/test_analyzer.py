"""Tests for the deterministic analyzer (engine + service)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.analyzer.engine import AnalyzerCard, build_report
from cr_helper.analyzer.service import DeckValidationError, analyze_deck
from cr_helper.db import Base
from cr_helper.models import Card, CardStats


def mk(key, name, elixir, ctype, dps=None, air=False, ground=True, fly=False, count=1, bo=False):
    return AnalyzerCard(
        key=key, name=name, type=ctype, elixir=elixir, rarity=None, dps=dps, count=count,
        hitpoints=None, damage=None, targets_air=air, targets_ground=ground, is_flying=fly,
        targets_buildings_only=bo,
    )


def test_building_only_attacker_is_not_anti_air():
    # Golem has attacks_air=True in the data but only targets buildings -> not real anti-air.
    golem = mk("golem", "Golem", 8, "Troop", dps=78.0, air=True, bo=True)
    assert golem.is_anti_air is False
    assert golem.air_dps == 0.0
    musketeer = mk("musketeer", "Musketeer", 4, "Troop", dps=103.0, air=True)
    assert musketeer.is_anti_air is True


def test_26_hog_cycle_report():
    deck = [
        mk("hog-rider", "Hog Rider", 4, "Troop", dps=93.75),
        mk("musketeer", "Musketeer", 4, "Troop", dps=103.0, air=True),
        mk("ice-golem", "Ice Golem", 2, "Troop", dps=None),
        mk("ice-spirit", "Ice Spirit", 1, "Troop", dps=None),
        mk("skeletons", "Skeletons", 1, "Troop", dps=None, count=3),
        mk("cannon", "Cannon", 3, "Building", dps=92.2),
        mk("fireball", "Fireball", 4, "Spell", ground=False),
        mk("the-log", "The Log", 2, "Spell"),
    ]
    r = build_report(deck)
    assert r.metrics.avg_elixir == 2.62
    assert r.metrics.cycle_cost == 6
    assert r.win_conditions == ["hog-rider"]
    assert r.archetype.primary == "Cycle"
    assert r.metrics.anti_air_cards == ["musketeer"]
    assert any(v.code == "limited_air_defense" for v in r.vulnerabilities)
    assert r.stability_score == 88


def test_conflicting_win_conditions_and_siege():
    deck = [
        mk("x-bow", "X-Bow", 6, "Building", dps=86.7),
        mk("golem", "Golem", 8, "Troop", dps=120.0),
        mk("knight", "Knight", 3, "Troop", dps=65.8),
        mk("archers", "Archers", 3, "Troop", dps=50.0, air=True, count=2),
        mk("fireball", "Fireball", 4, "Spell", ground=False),
        mk("the-log", "The Log", 2, "Spell"),
        mk("tesla", "Tesla", 4, "Building", dps=81.8, air=True),
        mk("ice-spirit", "Ice Spirit", 1, "Troop", dps=None),
    ]
    r = build_report(deck)
    assert any(v.code == "conflicting_win_conditions" for v in r.vulnerabilities)
    assert r.archetype.primary == "Siege"


def test_no_air_defense_flagged_high():
    deck = [mk(f"ground{i}", f"G{i}", 3, "Troop", dps=50.0) for i in range(7)]
    deck.append(mk("hog-rider", "Hog Rider", 4, "Troop", dps=90.0))
    r = build_report(deck)
    assert any(v.code == "no_air_defense" and v.severity == "high" for v in r.vulnerabilities)


# ---- service (DB-backed validation) ----

_DECK = ["knight", "giant", "musketeer", "cannon", "fireball", "the-log", "ice-spirit", "skeletons"]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as s:
        for k in _DECK:
            card = Card(key=k, name=k.replace("-", " ").title(), elixir=3, type="Troop")
            card.stats = CardStats(card_key=k, dps=50.0, count=1, targets_ground=True)
            s.add(card)
        s.commit()
    with maker() as s:
        yield s


def test_service_valid_deck(db_session):
    report = analyze_deck(db_session, _DECK)
    assert report.metrics.card_count == 8


def test_service_rejects_wrong_size(db_session):
    with pytest.raises(DeckValidationError):
        analyze_deck(db_session, _DECK[:7])


def test_service_rejects_unknown_card(db_session):
    with pytest.raises(DeckValidationError) as exc:
        analyze_deck(db_session, ["totally-fake"] + _DECK[1:])
    assert any("unknown card" in p for p in exc.value.problems)
