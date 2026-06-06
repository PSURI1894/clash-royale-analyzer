"""Tests for Phase 4 RAG: embedder, retrieval, grounding guardrail, stub advisor."""
from __future__ import annotations

import math

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cr_helper.db import Base
from cr_helper.rag.clients import StubClient
from cr_helper.rag.corpus import load_corpus
from cr_helper.rag.embed import HashingEmbedder
from cr_helper.rag.fusion import EvidencePack, RetrievedChunk
from cr_helper.rag.guardrail import check_grounding, collect_numbers, find_unverified
from cr_helper.rag.retrieve import Retriever
from cr_helper.rag.store import SqlVectorStore


# ---- embedder ----

def test_hashing_embedder_deterministic_and_normalized():
    e = HashingEmbedder(dim=256)
    v1 = e.embed("defend the Balloon with Musketeer")
    v2 = e.embed("defend the Balloon with Musketeer")
    assert v1 == v2  # stable hash -> reproducible across calls
    assert abs(math.sqrt(sum(x * x for x in v1)) - 1.0) < 1e-6
    assert v1 != e.embed("golem beatdown counter push")


# ---- retrieval over the real corpus ----

@pytest.fixture()
def indexed_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    chunks = load_corpus()
    emb = HashingEmbedder()
    with maker() as s:
        store = SqlVectorStore(s)
        for c, v in zip(chunks, emb.embed_many([f"{c['title']}. {c['text']}" for c in chunks])):
            store.upsert(c, v, emb.name)
        s.commit()
    with maker() as s:
        yield s


def test_retrieval_finds_relevant_archetype(indexed_session):
    retriever = Retriever(indexed_session, HashingEmbedder())
    hits = retriever.retrieve("defend against Lavaloon balloon lava hound air", k=5, archetype="Lavaloon")
    archetypes = [c.archetype for c, _ in hits]
    assert any(a in ("Lavaloon", "Air Beatdown") for a in archetypes)


# ---- grounding guardrail ----

def test_guardrail_flags_unverified_numbers():
    allowed = collect_numbers(["Average elixir 2.6", "coverage 75%", "score 69"])
    assert find_unverified("Play at 2.6 elixir and win 75% of the time.", allowed) == []
    bad = find_unverified("Your air defense drops by 74% and deals 176 dps.", allowed)
    assert "74" in bad and "176" in bad
    # small structural integers (steps, tile counts) are ignored
    assert find_unverified("Step 1: place four tiles back, hold 1 spell.", allowed) == []


# ---- stub advisor is grounded by construction ----

def _pack() -> EvidencePack:
    facts = [
        "Average elixir cost: 2.6.",
        "Matchup vs Lavaloon: 69 out of 100 (Even).",
        "Threat balloon: 75% coverage (answers: Musketeer).",
    ]
    chunks = [RetrievedChunk("lava-protect-air", "Protect your anti-air", "Keep your air units spread out.", 0.5)]
    pack = EvidencePack(
        deck_keys=["hog-rider", "musketeer"], deck_archetype="Hog Cycle", opponent="Lavaloon",
        verdict="Even", matchup_score=69, win_conditions=["hog-rider"], facts=facts,
        threats=[{"threat": "balloon", "coverage": 0.75, "best_answer": "musketeer", "answers": ["musketeer"]}],
        danger=[], anti_air=[{"key": "musketeer", "name": "Musketeer", "dps": 176.0}],
        weak_against=["golem"], meta=[], chunks=chunks, allowed_numbers=set(),
        names={"hog-rider": "Hog Rider", "musketeer": "Musketeer"},
    )
    pack.allowed_numbers = collect_numbers(facts + [c.text for c in chunks] + [str(pack.matchup_score)])
    return pack


def test_stub_advisor_is_grounded_and_cites():
    pack = _pack()
    report = StubClient().generate(pack)
    grounding = check_grounding(report, pack.allowed_numbers, "stub")
    assert grounding.ok, grounding.unverified_numbers
    assert report.citations == ["lava-protect-air"]
    assert report.key_facts and report.defensive_routine


def test_grounding_catches_tampered_report():
    pack = _pack()
    report = StubClient().generate(pack)
    report.game_plan.append("Your defence fails 88% of the time against this deck.")
    grounding = check_grounding(report, pack.allowed_numbers, "stub")
    assert not grounding.ok
    assert "88" in grounding.unverified_numbers
