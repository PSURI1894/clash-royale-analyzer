"""High-level engine service: duels and push simulations over the card DB."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Card
from .arena import SimResult
from .duel import DuelResult, duel
from .scenario import build_push_arena
from .units import make_unit


class EngineError(ValueError):
    pass


def simulate_duel(session: Session, a_key: str, b_key: str) -> tuple[DuelResult, str, str]:
    cards = {c.key: c for c in session.scalars(select(Card).where(Card.key.in_([a_key, b_key])))}
    a, b = cards.get(a_key), cards.get(b_key)
    if not a or not a.stats:
        raise EngineError(f"'{a_key}' has no combat stats (spell or unknown)")
    if not b or not b.stats:
        raise EngineError(f"'{b_key}' has no combat stats (spell or unknown)")
    ua = make_unit(1, a, a.stats, "attacker", 9.0, 18.0)
    ub = make_unit(2, b, b.stats, "defender", 9.0, 14.0)
    return duel(ua, ub), a.name, b.name


def simulate_push(
    session: Session,
    attacker_keys: list[str],
    defender_keys: list[str],
    lane: str = "left",
    duration: float = 40.0,
) -> tuple[SimResult, list[str]]:
    arena, warnings = build_push_arena(session, attacker_keys, defender_keys, lane)
    return arena.run(duration=duration), warnings
