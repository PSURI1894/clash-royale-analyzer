"""SQLAlchemy ORM models for the card catalog and combat stats.

`Card` mirrors the playable-card catalog (cr-api-data `cards.json`); `CardStats`
holds the unified combat numbers resolved by joining the characters / building /
spell / projectile stat files. The full source record is kept in `raw` so later
phases can pull additional fields without re-ingesting.
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Card(Base):
    __tablename__ = "cards"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    elixir: Mapped[int | None] = mapped_column(Integer, index=True)
    rarity: Mapped[str | None] = mapped_column(String, index=True)
    type: Mapped[str | None] = mapped_column(String, index=True)  # Troop | Building | Spell
    arena: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    is_evolved: Mapped[bool] = mapped_column(Boolean, default=False)
    has_evolution: Mapped[bool] = mapped_column(Boolean, default=False)

    stats: Mapped["CardStats | None"] = relationship(
        back_populates="card", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )


class CardStats(Base):
    __tablename__ = "card_stats"

    card_key: Mapped[str] = mapped_column(
        ForeignKey("cards.key", ondelete="CASCADE"), primary_key=True
    )

    # Core combat numbers (base / level-1 values, as given by cr-api-data).
    hitpoints: Mapped[int | None] = mapped_column(Integer)
    damage: Mapped[int | None] = mapped_column(Integer)
    dps: Mapped[float | None] = mapped_column(Float)
    hit_speed_ms: Mapped[int | None] = mapped_column(Integer)
    load_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Range / vision / movement (raw = cr-api-data units of 1/1000 tile; tiles = derived).
    range_raw: Mapped[int | None] = mapped_column(Integer)
    range_tiles: Mapped[float | None] = mapped_column(Float)
    sight_range_raw: Mapped[int | None] = mapped_column(Integer)
    speed_raw: Mapped[int | None] = mapped_column(Integer)
    speed_label: Mapped[str | None] = mapped_column(String)

    # Targeting / unit nature.
    targets_ground: Mapped[bool] = mapped_column(Boolean, default=False)
    targets_air: Mapped[bool] = mapped_column(Boolean, default=False)
    targets_buildings_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flying: Mapped[bool] = mapped_column(Boolean, default=False)
    count: Mapped[int] = mapped_column(Integer, default=1)  # units deployed per card

    # Spell/area attributes.
    radius_raw: Mapped[int | None] = mapped_column(Integer)
    radius_tiles: Mapped[float | None] = mapped_column(Float)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Per-level scaling arrays + the full source record (lossless).
    hitpoints_per_level: Mapped[list | None] = mapped_column(JSON)
    damage_per_level: Mapped[list | None] = mapped_column(JSON)
    raw: Mapped[dict | None] = mapped_column(JSON)

    card: Mapped["Card"] = relationship(back_populates="stats")
