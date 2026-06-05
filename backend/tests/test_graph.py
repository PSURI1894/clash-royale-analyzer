"""Tests for the knowledge graph: ensemble resolver, repo, matchup service."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.db import Base
from cr_helper.graph.repo import SqlGraphRepo
from cr_helper.graph.resolver import EdgeRow, resolve
from cr_helper.graph.service import GraphService
from cr_helper.models import MatchupEdge


# ---- ensemble resolver (pure) ----

def _curated(value=0.8):
    return EdgeRow("a", "b", "counters", value, "curated", 0.6, 0)


def test_resolver_curated_only_passthrough():
    r = resolve([_curated(0.8)])
    assert r.value == 0.8
    assert r.sources == ["curated"]
    assert 0 < r.confidence < 1


def test_resolver_mined_pulls_value_and_raises_confidence():
    r = resolve([_curated(0.8), EdgeRow("a", "b", "counters", 0.5, "mined", 0.9, 300)])
    assert 0.5 <= r.value <= 0.6      # heavily weighted toward the mined value
    assert r.confidence > 0.9
    assert r.sources[0] == "mined"


def test_resolver_more_battles_pull_further_from_prior():
    small = resolve([_curated(0.8), EdgeRow("a", "b", "counters", 0.4, "mined", 0.9, 20)]).value
    big = resolve([_curated(0.8), EdgeRow("a", "b", "counters", 0.4, "mined", 0.9, 400)]).value
    assert big < small  # more evidence moves further from the curated prior of 0.8


def test_resolver_zero_sample_mined_is_ignored():
    r = resolve([_curated(0.8), EdgeRow("a", "b", "counters", 0.1, "mined", 0.9, 0)])
    assert r.value == 0.8


# ---- repo + service (DB-backed) ----

@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    edges = [
        ("inferno-tower", "golem", "counters", 0.9),
        ("pekka", "golem", "counters", 0.85),
        ("musketeer", "balloon", "counters", 0.75),
        ("lava-hound", "balloon", "synergizes_with", 0.9),
    ]
    with maker() as s:
        for src, tgt, rel, val in edges:
            s.add(MatchupEdge(source_key=src, target_key=tgt, relation=rel,
                              value=val, source="curated", confidence=0.6))
        s.commit()
    with maker() as s:
        yield s


def test_answers_to_sorted_by_value(session):
    keys = [e.source_key for e in SqlGraphRepo(session).answers_to("golem")]
    assert keys == ["inferno-tower", "pekka"]


def test_synergies_normalized_to_queried_card(session):
    syn = SqlGraphRepo(session).synergies_for("balloon")
    assert syn[0].source_key == "balloon"
    assert syn[0].target_key == "lava-hound"


def test_matchup_covers_balloon_with_musketeer(session):
    deck = ["musketeer", "knight", "cannon", "skeletons", "ice-spirit", "the-log", "fireball", "hog-rider"]
    rep = GraphService(SqlGraphRepo(session)).matchup(deck, opponent="Lavaloon")
    assert rep.opponent == "Lavaloon"
    balloon = next(t for t in rep.threats if t.threat == "balloon")
    assert balloon.best_answer == "musketeer"


def test_matchup_flags_golem_as_danger(session):
    deck = ["musketeer", "knight", "cannon", "skeletons", "ice-spirit", "the-log", "fireball", "hog-rider"]
    rep = GraphService(SqlGraphRepo(session)).matchup(deck, opponent="Golem Beatdown")
    assert "golem" in rep.danger  # no inferno-tower / pekka in this deck


def test_weak_against_respects_answers(session):
    deck = ["pekka", "knight", "cannon", "skeletons", "ice-spirit", "the-log", "fireball", "musketeer"]
    weak = GraphService(SqlGraphRepo(session)).weak_against(deck)
    assert "golem" not in weak     # pekka answers golem
    assert "balloon" not in weak   # musketeer answers balloon
    assert "hog-rider" in weak     # nothing here answers hog-rider
