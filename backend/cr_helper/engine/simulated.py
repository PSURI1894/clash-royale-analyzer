"""Seed `source=simulated` counter edges from v0 duels.

    python -m cr_helper.engine.simulated

Runs a deterministic stat-trade duel for every (attacker, target) fighter pair
and writes an edge where the attacker decisively wins. These are low-weight in
the ensemble (positioning-blind), so they fill gaps without overriding curated
or mined evidence — completing the curated + mined + simulated blend.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..models import Card, MatchupEdge
from .duel import duel
from .units import make_unit

SIM_CONFIDENCE = 0.7
SIM_MIN_VALUE = 0.6  # only write decisive stat wins


def _troops(session: Session) -> list[Card]:
    return [c for c in session.scalars(select(Card).where(Card.type == "Troop")) if c.stats and c.stats.damage]


def _duel_value(ua, ub) -> float:
    r = duel(ua, ub)
    if r.winner == "a":
        return round(0.5 + 0.5 * r.a_hp_pct, 3)
    if r.winner == "b":
        return round(0.5 - 0.5 * r.b_hp_pct, 3)
    return 0.5


def seed_simulated(session: Session) -> int:
    troops = _troops(session)
    attackers = [c for c in troops if not c.stats.targets_buildings_only]

    session.execute(delete(MatchupEdge).where(MatchupEdge.source == "simulated"))
    written = 0
    for a in attackers:
        ua = make_unit(1, a, a.stats, "attacker", 0.0, 0.0)
        for b in troops:
            if a.key == b.key:
                continue
            ub = make_unit(2, b, b.stats, "defender", 0.0, 0.0)
            if not ua.can_target(ub):
                continue
            value = _duel_value(ua, ub)
            if value < SIM_MIN_VALUE:
                continue
            session.add(MatchupEdge(
                source_key=a.key, target_key=b.key, relation="counters", target_kind="card",
                value=value, source="simulated", confidence=SIM_CONFIDENCE, sample_size=1, note="duel",
            ))
            written += 1
    session.commit()
    return written


def main() -> None:
    init_db()
    with SessionLocal() as session:
        count = seed_simulated(session)
        print(f"Seeded {count} simulated counter edges from v0 duels.")


if __name__ == "__main__":
    main()
