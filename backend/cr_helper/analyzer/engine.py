"""The deterministic analysis engine: metrics, archetype, vulnerabilities.

Operates on lightweight ``AnalyzerCard`` objects so it is testable without a DB.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..schemas import (
    AnalysisReport,
    AnalyzerCardOut,
    ArchetypeOut,
    DeckMetricsOut,
    VulnerabilityOut,
)
from . import card_roles as roles

_SEVERITY_PENALTY = {"high": 25, "medium": 12, "low": 5}


@dataclass
class AnalyzerCard:
    key: str
    name: str
    type: str | None
    elixir: int | None
    rarity: str | None
    dps: float | None
    count: int
    hitpoints: int | None
    damage: int | None
    targets_air: bool
    targets_ground: bool
    is_flying: bool
    targets_buildings_only: bool = False

    @classmethod
    def from_orm(cls, card) -> "AnalyzerCard":
        st = card.stats
        return cls(
            key=card.key,
            name=card.name,
            type=card.type,
            elixir=card.elixir,
            rarity=card.rarity,
            dps=st.dps if st else None,
            count=(st.count if st and st.count else 1),
            hitpoints=st.hitpoints if st else None,
            damage=st.damage if st else None,
            targets_air=bool(st and st.targets_air),
            targets_ground=bool(st and st.targets_ground),
            is_flying=bool(st and st.is_flying),
            targets_buildings_only=bool(st and st.targets_buildings_only),
        )

    @property
    def _defends(self) -> bool:
        """Building-only attackers (Golem, Lava Hound, Hog, Balloon) don't defend at all."""
        return bool(self.dps) and not self.targets_buildings_only

    @property
    def air_dps(self) -> float:
        return round((self.dps or 0) * self.count, 1) if (self._defends and self.targets_air) else 0.0

    @property
    def ground_dps(self) -> float:
        return round((self.dps or 0) * self.count, 1) if (self._defends and self.targets_ground) else 0.0

    @property
    def is_one_shot(self) -> bool:
        """Spirits etc.: one hit then gone, so DPS overstates sustained output."""
        return self.key in roles.ONE_SHOT_UNITS

    @property
    def is_anti_air(self) -> bool:
        """A real anti-air source: damages air AND isn't a building-only attacker."""
        return self.type in ("Troop", "Building") and self.targets_air and self._defends

    def role(self) -> str:
        if self.key in roles.WIN_CONDITIONS or self.key in roles.FLEX_WIN_CONDITIONS:
            return "win-condition"
        if self.type == "Spell":
            return "spell"
        if self.type == "Building":
            return "building"
        if self.is_anti_air:
            return "anti-air"
        return "support"


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def compute_metrics(cards: list[AnalyzerCard]) -> DeckMetricsOut:
    elixirs = [c.elixir for c in cards if c.elixir is not None]
    avg = round(sum(elixirs) / len(elixirs), 2) if elixirs else 0.0
    cycle_cost = sum(sorted(elixirs)[:4])

    curve: dict[int, int] = {}
    for e in elixirs:
        curve[e] = curve.get(e, 0) + 1

    keys = {c.key for c in cards}
    return DeckMetricsOut(
        card_count=len(cards),
        avg_elixir=avg,
        cycle_cost=cycle_cost,
        elixir_curve=dict(sorted(curve.items())),
        troop_count=sum(c.type == "Troop" for c in cards),
        building_count=sum(c.type == "Building" for c in cards),
        spell_count=sum(c.type == "Spell" for c in cards),
        ground_dps=round(sum(c.ground_dps for c in cards if not c.is_one_shot), 1),
        air_dps=round(sum(c.air_dps for c in cards if not c.is_one_shot), 1),
        anti_air_cards=[c.key for c in cards if c.is_anti_air],
        air_offense_cards=[c.key for c in cards if c.is_flying],
        has_small_spell=bool(keys & roles.SMALL_SPELLS),
        has_big_spell=bool(keys & roles.BIG_SPELLS),
        has_building=any(c.type == "Building" for c in cards),
    )


# --------------------------------------------------------------------------- #
# Win conditions & archetype
# --------------------------------------------------------------------------- #
def detect_win_conditions(cards: list[AnalyzerCard]) -> list[str]:
    keys = {c.key for c in cards}
    primary = [c.key for c in cards if c.key in roles.WIN_CONDITIONS]
    if primary:
        return primary
    return [c.key for c in cards if c.key in roles.FLEX_WIN_CONDITIONS]


def classify_archetype(cards: list[AnalyzerCard], metrics: DeckMetricsOut) -> ArchetypeOut:
    keys = {c.key for c in cards}
    scores: dict[str, float] = {}
    signals: list[str] = []

    def add(name: str, score: float, signal: str) -> None:
        scores[name] = scores.get(name, 0) + score
        signals.append(signal)

    siege = keys & roles.SIEGE
    air = keys & roles.AIR_WIN_CONDITIONS
    beat = keys & roles.BEATDOWN_TANKS
    bridge = keys & roles.BRIDGE_SPAM
    bait = keys & roles.BAIT_CARDS

    if siege:
        add("Siege", 5, f"siege win condition: {', '.join(sorted(siege))}")
    if air:
        add("Air Beatdown", 4, f"air win condition: {', '.join(sorted(air))}")
    if beat and not air:
        add("Beatdown", 3 + (1 if metrics.avg_elixir >= 3.8 else 0),
            f"heavy tank: {', '.join(sorted(beat))}")
    if len(bait) >= 3:
        add("Spell Bait", len(bait), f"{len(bait)} spell-bait cards")
    if len(bridge) >= 2 and not beat:
        add("Bridge Spam", len(bridge), f"bridge-spam cards: {', '.join(sorted(bridge))}")
    if metrics.avg_elixir <= 3.0 and (keys & {"hog-rider", "miner", "mortar", "x-bow", "wall-breakers"}):
        add("Cycle", 4, f"low avg elixir ({metrics.avg_elixir}) with a cheap win condition")

    if not scores:
        primary = "Beatdown/Midrange" if metrics.avg_elixir >= 3.8 else "Control"
        return ArchetypeOut(
            primary=primary,
            confidence=0.4,
            signals=["no strong archetype signal; classified by elixir profile"],
        )

    primary = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = round(scores[primary] / total, 2) if total else 0.5
    return ArchetypeOut(primary=primary, confidence=confidence, signals=signals)


# --------------------------------------------------------------------------- #
# Vulnerabilities + stability score
# --------------------------------------------------------------------------- #
def assess_vulnerabilities(
    cards: list[AnalyzerCard], metrics: DeckMetricsOut, win_conditions: list[str]
) -> list[VulnerabilityOut]:
    keys = {c.key for c in cards}
    out: list[VulnerabilityOut] = []

    # Air defense — counts only *sustained* anti-air (>= 40 defensive air DPS per card).
    strong_anti_air = [
        c.key for c in cards if c.is_anti_air and not c.is_one_shot and c.air_dps >= 40
    ]
    if not metrics.anti_air_cards:
        out.append(VulnerabilityOut(
            code="no_air_defense", severity="high", title="No air defense",
            detail="No card can damage air. Air win conditions (Lava Hound, Balloon, "
                   "Minion Horde) will be nearly unanswerable.",
        ))
    elif len(strong_anti_air) <= 1:
        only = ", ".join(metrics.anti_air_cards)
        out.append(VulnerabilityOut(
            code="limited_air_defense", severity="medium", title="Limited air defense",
            detail=f"Sustained anti-air rests on {', '.join(strong_anti_air) or 'chip damage only'} "
                   f"(anti-air cards: {only}; defensive air DPS {metrics.air_dps}). "
                   "If it is spelled or distracted, air beatdown (Lavaloon) punishes hard.",
        ))

    # Win condition coverage
    if not win_conditions:
        out.append(VulnerabilityOut(
            code="no_win_condition", severity="high", title="No clear win condition",
            detail="No reliable tower-damage threat — the deck may struggle to close games.",
        ))

    # Archetype drift / conflicting win conditions
    if (keys & roles.SIEGE) and (keys & roles.BEATDOWN_TANKS):
        out.append(VulnerabilityOut(
            code="conflicting_win_conditions", severity="high",
            title="Conflicting win conditions",
            detail="Mixes a siege building with a heavy beatdown tank — these want opposite "
                   "elixir tempos and dilute each other.",
        ))
    elif len([k for k in keys if k in roles.WIN_CONDITIONS]) >= 3:
        out.append(VulnerabilityOut(
            code="too_many_win_conditions", severity="medium",
            title="Too many win conditions",
            detail="Three or more win conditions leaves little defensive support.",
        ))

    # Spell coverage
    if not metrics.has_small_spell:
        out.append(VulnerabilityOut(
            code="no_small_spell", severity="medium", title="No cheap spell",
            detail="No small spell (Log/Zap/Snowball) to reset chargers or clear swarms cheaply.",
        ))
    if not metrics.has_big_spell:
        out.append(VulnerabilityOut(
            code="no_damage_spell", severity="low", title="No damage spell",
            detail="No medium/large spell (Fireball/Poison/Lightning) for clustered support or chip.",
        ))

    # Elixir profile
    if metrics.avg_elixir >= 4.2:
        out.append(VulnerabilityOut(
            code="heavy_cycle", severity="medium", title="Heavy average elixir",
            detail=f"Average elixir {metrics.avg_elixir} is slow to cycle — fast control decks "
                   "can out-tempo and punish in double elixir.",
        ))

    # Building defense (matters most vs Hog/Ram if not a beatdown/bridge deck)
    if not metrics.has_building and not (keys & roles.BEATDOWN_TANKS):
        out.append(VulnerabilityOut(
            code="no_building", severity="low", title="No defensive building",
            detail="No building to pull/kite Hog Rider, Ram Rider or Royal Giant.",
        ))

    return out


def stability_score(vulnerabilities: list[VulnerabilityOut]) -> int:
    penalty = sum(_SEVERITY_PENALTY.get(v.severity, 0) for v in vulnerabilities)
    return max(0, 100 - penalty)


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def build_report(cards: list[AnalyzerCard]) -> AnalysisReport:
    metrics = compute_metrics(cards)
    win_conditions = detect_win_conditions(cards)
    archetype = classify_archetype(cards, metrics)
    vulnerabilities = assess_vulnerabilities(cards, metrics, win_conditions)

    card_out = [
        AnalyzerCardOut(
            key=c.key, name=c.name, elixir=c.elixir, type=c.type, rarity=c.rarity,
            dps=c.dps, count=c.count, targets_air=c.targets_air,
            targets_ground=c.targets_ground, targets_buildings_only=c.targets_buildings_only,
            is_flying=c.is_flying, role=c.role(),
        )
        for c in cards
    ]
    return AnalysisReport(
        cards=card_out,
        win_conditions=win_conditions,
        archetype=archetype,
        metrics=metrics,
        vulnerabilities=vulnerabilities,
        stability_score=stability_score(vulnerabilities),
    )
