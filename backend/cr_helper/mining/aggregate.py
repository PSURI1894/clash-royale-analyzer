"""Aggregate stored battles into empirical win-rates -> mined edges + meta stats."""
from __future__ import annotations

import itertools
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Battle, CardMetaStat, MatchupEdge

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

    edges = 0
    edges += _write_edges(session, "counters", counter_g, counter_w, min_sample, dataset)
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


def _write_edges(session, relation, games, wins, min_sample, dataset) -> int:
    written = 0
    for (a, b), g in games.items():
        if g < min_sample:
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
