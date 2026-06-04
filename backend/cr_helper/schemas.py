"""Pydantic response schemas (API serialization)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CardStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hitpoints: int | None = None
    damage: int | None = None
    dps: float | None = None
    hit_speed_ms: int | None = None
    load_time_ms: int | None = None
    range_tiles: float | None = None
    sight_range_raw: int | None = None
    speed_label: str | None = None
    targets_ground: bool = False
    targets_air: bool = False
    targets_buildings_only: bool = False
    is_flying: bool = False
    count: int = 1
    radius_tiles: float | None = None
    duration_ms: int | None = None


class CardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    elixir: int | None = None
    rarity: str | None = None
    type: str | None = None
    arena: int | None = None


class CardDetail(CardSummary):
    description: str | None = None
    is_evolved: bool = False
    has_evolution: bool = False
    stats: CardStatsOut | None = None


# ---- Analyzer (Phase 1) ----


class DeckRequest(BaseModel):
    cards: list[str]


class AnalyzerCardOut(BaseModel):
    key: str
    name: str
    elixir: int | None = None
    type: str | None = None
    rarity: str | None = None
    dps: float | None = None
    count: int = 1
    targets_air: bool = False
    targets_ground: bool = False
    targets_buildings_only: bool = False
    is_flying: bool = False
    role: str | None = None


class DeckMetricsOut(BaseModel):
    card_count: int
    avg_elixir: float
    cycle_cost: int
    elixir_curve: dict[int, int]
    troop_count: int
    building_count: int
    spell_count: int
    ground_dps: float
    air_dps: float
    anti_air_cards: list[str]
    air_offense_cards: list[str]
    has_small_spell: bool
    has_big_spell: bool
    has_building: bool


class ArchetypeOut(BaseModel):
    primary: str
    confidence: float
    signals: list[str] = []


class VulnerabilityOut(BaseModel):
    code: str
    severity: str  # high | medium | low
    title: str
    detail: str


class AnalysisReport(BaseModel):
    cards: list[AnalyzerCardOut]
    win_conditions: list[str]
    archetype: ArchetypeOut
    metrics: DeckMetricsOut
    vulnerabilities: list[VulnerabilityOut]
    stability_score: int
