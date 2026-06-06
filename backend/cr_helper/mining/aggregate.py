"""Aggregate stored battles into empirical win-rates -> mined edges + meta stats."""
from __future__ import annotations

import itertools
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Battle, Card, CardMetaStat, CardStats, MatchupEdge

MINED_CONFIDENCE = 0.8
# Only persist a mined edge if the win-rate is at least this far from neutral (0.5).
# Keeps the graph to real signal instead of ~0.5 noise from incidental card pairings.
MINED_MARGIN = 0.04


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_fair(b: Battle, tol: float) -> bool:
    if b.team_avg_level is None or b.opponent_avg_level is None:
        return True
    return abs(b.team_avg_level - b.opponent_avg_level) <= tol


# Spells that only hit the ground — they can never answer a flying threat.
GROUND_ONLY_SPELLS = {"the-log", "earthquake", "barbarian-barrel", "royal-delivery"}


def _targeting_sets(session: Session) -> tuple[set[str], set[str]]:
    """(flying cards, cards that can answer air). Most spells hit air; ground-only
    troops/buildings and ground-only spells cannot — so we never mine them as air counters."""
    flying: set[str] = set()
    air_ok: set[str] = set()
    rows = session.execute(
        select(
            Card.key, Card.type, CardStats.is_flying,
            CardStats.targets_air, CardStats.targets_buildings_only,
        ).outerjoin(CardStats, CardStats.card_key == Card.key)
    ).all()
    for key, ctype, is_flying, targets_air, buildings_only in rows:
        if is_flying:
            flying.add(key)
        # A real air answer hits air and isn't a building-only targeter (e.g. Ice Golem).
        can_air = (bool(targets_air) and not bool(buildings_only)) or ctype == "Spell"
        if can_air and key not in GROUND_ONLY_SPELLS:
            air_ok.add(key)
    return flying, air_ok


def aggregate(
    session: Session,
    dataset: str,
    min_sample: int | None = None,
    level_tol: float | None = None,
) -> dict:
    min_sample = settings.mining_min_sample if min_sample is None else min_sample
    level_tol = settings.mining_level_tolerance if level_tol is None else level_tol

    battles = session.scalars(select(Battle).where(Battle.dataset == dataset)).all()
    fair = [b for b in battles if _is_fair(b, level_tol)]
    n = len(fair)

    counter_g: dict[tuple, int] = defaultdict(int)
    counter_w: dict[tuple, int] = defaultdict(int)
    synergy_g: dict[tuple, int] = defaultdict(int)
    synergy_w: dict[tuple, int] = defaultdict(int)
    card_g: dict[str, int] = defaultdict(int)
    card_w: dict[str, int] = defaultdict(int)

    for b in fair:
        won = 1 if b.won else 0
        team, opp = b.team_cards, b.opponent_cards
        for a in set(team):
            card_g[a] += 1
            card_w[a] += won
        for a in set(team):
            for bb in set(opp):
                counter_g[(a, bb)] += 1
                counter_w[(a, bb)] += won
        for a, bb in itertools.combinations(sorted(set(team)), 2):
            synergy_g[(a, bb)] += 1
            synergy_w[(a, bb)] += won

    # Clean rebuild of this dataset's mined edges (idempotent; no stale rows).
    flying, air_ok = _targeting_sets(session)
    session.execute(
        delete(MatchupEdge).where(MatchupEdge.source == "mined", MatchupEdge.note.like(f"{dataset}:%"))
    )

    edges = 0
    edges += _write_edges(session, "counters", counter_g, counter_w, min_sample, dataset, flying, air_ok)
    edges += _write_edges(session, "synergizes_with", synergy_g, synergy_w, min_sample, dataset)

    for key, g in card_g.items():
        _upsert_meta(session, key, dataset, g, card_w[key], card_w[key] / g, g / n if n else 0.0)

    session.commit()
    return {
        "dataset": dataset,
        "battles_total": len(battles),
        "battles_fair": n,
        "mined_edges": edges,
        "cards_scored": len(card_g),
    }


def _write_edges(session, relation, games, wins, min_sample, dataset, flying=None, air_ok=None) -> int:
    written = 0
    for (a, b), g in games.items():
        if g < min_sample:
            continue
        # A ground-only unit cannot be a real counter to a flying threat — drop it.
        if relation == "counters" and flying and b in flying and a not in air_ok:
            continue
        wr = wins[(a, b)] / g
        if abs(wr - 0.5) < MINED_MARGIN:
            continue  # neutral pairing — not signal
        _upsert_edge(session, a, b, relation, wr, g, dataset)
        written += 1
    return written


def _upsert_edge(session, a, b, relation, value, n, dataset) -> None:
    edge = session.scalar(
        select(MatchupEdge).where(
            MatchupEdge.source_key == a,
            MatchupEdge.target_key == b,
            MatchupEdge.relation == relation,
            MatchupEdge.source == "mined",
        )
    )
    note = f"{dataset}:{n}g"
    if edge:
        edge.value = round(value, 3)
        edge.sample_size = n
        edge.confidence = MINED_CONFIDENCE
        edge.note = note
        edge.updated_at = _now()
    else:
        session.add(MatchupEdge(
            source_key=a, target_key=b, relation=relation, target_kind="card",
            value=round(value, 3), source="mined", confidence=MINED_CONFIDENCE,
            sample_size=n, note=note,
        ))


def _upsert_meta(session, key, dataset, games, wins, win_rate, usage) -> None:
    meta = session.scalar(
        select(CardMetaStat).where(
            CardMetaStat.card_key == key, CardMetaStat.dataset == dataset
        )
    )
    if meta:
        meta.games, meta.wins = games, wins
        meta.win_rate, meta.usage = round(win_rate, 3), round(usage, 3)
        meta.updated_at = _now()
    else:
        session.add(CardMetaStat(
            card_key=key, dataset=dataset, games=games, wins=wins,
            win_rate=round(win_rate, 3), usage=round(usage, 3),
        ))
