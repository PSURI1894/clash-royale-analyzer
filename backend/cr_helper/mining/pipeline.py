"""Mining pipeline: extract -> dedupe -> store -> aggregate."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..models import Battle, Card, MatchupEdge
from .aggregate import aggregate
from .parse import CardIndex, parse_battle
from .sources import BattleSource, OfficialApiSource, SyntheticSource


def _synthetic_inputs(session: Session):
    """Build the synthetic card pool + curated counter lookup from the DB."""
    keys: set[str] = set()
    cval: dict[tuple, float] = {}
    edges = session.scalars(
        select(MatchupEdge).where(
            MatchupEdge.source == "curated", MatchupEdge.relation == "counters"
        )
    ).all()
    for e in edges:
        keys.add(e.source_key)
        keys.add(e.target_key)
        cval[(e.source_key, e.target_key)] = e.value

    cards = session.scalars(select(Card).where(Card.key.in_(keys))).all()
    pool = [{"id": c.card_id, "name": c.name, "key": c.key} for c in cards if c.card_id]

    def counter_value(a: str, b: str) -> float | None:
        return cval.get((a, b))

    return pool, counter_value


def build_synthetic_source(session: Session, seed: int = 7) -> SyntheticSource:
    pool, counter_value = _synthetic_inputs(session)
    return SyntheticSource(pool, counter_value, seed=seed)


def extract_into(
    session: Session, source: BattleSource, dataset: str, idx: CardIndex, limit: int
) -> int:
    seen = set(session.scalars(select(Battle.battle_uid).where(Battle.dataset == dataset)).all())
    inserted = 0
    for raw in source.iter_raw_battles(limit):
        rec = parse_battle(raw, idx, dataset)
        if rec is None or rec.battle_uid in seen:
            continue
        seen.add(rec.battle_uid)
        session.add(Battle(
            battle_uid=rec.battle_uid, dataset=dataset, player_tag=rec.player_tag,
            opponent_tag=rec.opponent_tag, won=rec.won, mode=rec.mode,
            team_cards=rec.team_cards, opponent_cards=rec.opponent_cards,
            team_avg_level=rec.team_avg_level, opponent_avg_level=rec.opponent_avg_level,
            trophies=rec.trophies, battle_time=rec.battle_time,
        ))
        inserted += 1
        if inserted % 1000 == 0:
            session.commit()
    session.commit()
    return inserted


def run_mining(
    dataset: str = "synthetic",
    limit: int = 4000,
    source: BattleSource | None = None,
    seed: int = 7,
    seed_tags: list[str] | None = None,
) -> dict:
    init_db()
    with SessionLocal() as session:
        idx = CardIndex.from_session(session)
        owns_source = source is None
        if source is None:
            source = (
                build_synthetic_source(session, seed)
                if dataset == "synthetic"
                else OfficialApiSource(seed_tags or [])
            )
        try:
            inserted = extract_into(session, source, dataset, idx, limit)
            summary = aggregate(session, dataset)
        finally:
            if owns_source:
                source.close()
        summary["battles_inserted"] = inserted
        return summary
