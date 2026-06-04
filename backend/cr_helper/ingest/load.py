"""Upsert normalized card records into the database."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Card, CardStats
from .normalize import CardRecord

_CARD_FIELDS = (
    "card_id", "name", "elixir", "rarity", "type", "arena",
    "description", "is_evolved", "has_evolution",
)


def load_records(session: Session, records: list[CardRecord]) -> int:
    for rec in records:
        card = session.get(Card, rec.key) or Card(key=rec.key)
        for field in _CARD_FIELDS:
            setattr(card, field, getattr(rec, field))
        session.add(card)

        if rec.stats is not None:
            stats = session.get(CardStats, rec.key) or CardStats(card_key=rec.key)
            for field, value in rec.stats.model_dump().items():
                setattr(stats, field, value)
            session.add(stats)

    session.commit()
    return len(records)
