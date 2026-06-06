"""SQLAlchemy ORM models for the card catalog and combat stats.

`Card` mirrors the playable-card catalog (cr-api-data `cards.json`); `CardStats`
holds the unified combat numbers resolved by joining the characters / building /
spell / projectile stat files. The full source record is kept in `raw` so later
phases can pull additional fields without re-ingesting.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


class MatchupEdge(Base):
    """A provenance-bearing edge in the knowledge graph.

    Multiple rows may exist for the same (source_key, target_key, relation) from
    different data sources; the ensemble resolver blends them into one effective
    value. This is the spine of the confidence-weighted ensemble (curated now;
    mined/simulated/scraped in later phases).
    """

    __tablename__ = "matchup_edges"
    __table_args__ = (
        UniqueConstraint("source_key", "target_key", "relation", "source", name="uq_edge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String, index=True)
    target_key: Mapped[str] = mapped_column(String, index=True)
    target_kind: Mapped[str] = mapped_column(String, default="card")  # card | archetype
    # counters | synergizes_with | win_condition_for
    relation: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[float] = mapped_column(Float, default=0.0)  # strength / effectiveness 0..1
    source: Mapped[str] = mapped_column(String, default="curated")  # provenance
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Battle(Base):
    """One parsed 1v1 battle (deduped across crawled players by `battle_uid`).

    Decks are stored as resolved card keys so aggregation is catalog-native.
    `dataset` keeps synthetic demo data strictly separate from official-API data.
    """

    __tablename__ = "battles"
    __table_args__ = (UniqueConstraint("battle_uid", name="uq_battle_uid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    battle_uid: Mapped[str] = mapped_column(String, index=True)
    dataset: Mapped[str] = mapped_column(String, default="api", index=True)  # api | synthetic
    player_tag: Mapped[str | None] = mapped_column(String, index=True)
    opponent_tag: Mapped[str | None] = mapped_column(String)
    won: Mapped[bool] = mapped_column(Boolean)
    mode: Mapped[str | None] = mapped_column(String, index=True)
    team_cards: Mapped[list] = mapped_column(JSON)       # list[str] of card keys
    opponent_cards: Mapped[list] = mapped_column(JSON)
    team_avg_level: Mapped[float | None] = mapped_column(Float)
    opponent_avg_level: Mapped[float | None] = mapped_column(Float)
    trophies: Mapped[int | None] = mapped_column(Integer)
    battle_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class CardMetaStat(Base):
    """Aggregated per-card empirical win-rate / usage for a dataset."""

    __tablename__ = "card_meta_stats"
    __table_args__ = (UniqueConstraint("card_key", "dataset", name="uq_card_meta"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_key: Mapped[str] = mapped_column(String, index=True)
    dataset: Mapped[str] = mapped_column(String, default="api", index=True)
    games: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    usage: Mapped[float] = mapped_column(Float, default=0.0)  # fraction of battles featuring it
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class GuideChunk(Base):
    """A retrievable strategy/placement note for the RAG advisor.

    Original, paraphrased guidance (not copyrighted text). The embedding is stored
    as JSON (Python cosine on SQLite); swap in pgvector for the full stack.
    """

    __tablename__ = "guide_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String, index=True)      # defense | placement | macro | matchup
    archetype: Mapped[str] = mapped_column(String, index=True)  # opponent archetype, or "general"
    cards: Mapped[list] = mapped_column(JSON, default=list)     # relevant card keys
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON)        # L2-normalized list[float]
    embed_model: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
