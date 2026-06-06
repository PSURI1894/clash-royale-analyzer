"""Translate a high-level push (attacker cards vs defender cards) into an Arena."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Card
from .arena import Arena
from .units import make_tower, make_unit, tower_layout


def _load(session: Session, keys: list[str]) -> dict[str, Card]:
    return {c.key: c for c in session.scalars(select(Card).where(Card.key.in_(keys)))}


def build_push_arena(
    session: Session, attacker_keys: list[str], defender_keys: list[str], lane: str = "left"
) -> tuple[Arena, list[str]]:
    cards = _load(session, [*attacker_keys, *defender_keys])
    units = []
    uid = 0
    warnings: list[str] = []

    for side in ("defender", "attacker"):
        for x, y, kind in tower_layout(side):
            units.append(make_tower(uid, side, x, y, kind))
            uid += 1

    lane_x = 3.5 if lane == "left" else 14.5

    for i, key in enumerate(attacker_keys):
        card = cards.get(key)
        if not card or not card.stats:
            warnings.append(f"no combat stats for '{key}' (spell or missing) — skipped")
            continue
        units.append(make_unit(uid, card, card.stats, "attacker", lane_x + (i % 2) - 0.5, 17.5 + i * 0.7))
        uid += 1

    for i, key in enumerate(defender_keys):
        card = cards.get(key)
        if not card or not card.stats:
            warnings.append(f"no combat stats for '{key}' (spell or missing) — skipped")
            continue
        units.append(make_unit(uid, card, card.stats, "defender", lane_x + (i % 2) * 1.5 - 0.75, 9.5 - i * 0.5))
        uid += 1

    return Arena(units), warnings
