"""Engine entity model, arena constants, and CardStats -> Unit conversion."""
from __future__ import annotations

from dataclasses import dataclass

# Arena (tiles). Defender holds the bottom (small y), attacker the top (large y).
ARENA_W = 18.0
ARENA_H = 32.0
RIVER_Y = 16.0
BRIDGE_X = (3.5, 14.5)


@dataclass
class TowerSpec:
    hp: float
    damage: float
    hit_speed: float
    rng: float


# Tournament-standard (~level 11) tower values; towers are not playable cards.
PRINCESS = TowerSpec(hp=2534, damage=109, hit_speed=0.8, rng=7.5)
KING = TowerSpec(hp=4824, damage=109, hit_speed=1.0, rng=7.0)

# Movement label -> tiles/second (fallback when speed_raw is missing).
_SPEED_LABEL = {"slow": 0.75, "medium": 1.0, "fast": 1.45, "very fast": 1.9, "veryfast": 1.9}

# One-shot units: deal a single hit then expire (spirits). Without this they
# "win" long duels against targets that can't retaliate (e.g. a Balloon), which
# wrongly reads as a hard counter.
ONE_SHOT_UNITS = {"ice-spirit", "fire-spirit", "electro-spirit", "heal-spirit"}

# Splash attackers and their area radius (tiles). Reliable curated set — the raw
# stat files don't cleanly separate body radius from splash radius.
SPLASH_UNITS = {
    "wizard": 1.3, "baby-dragon": 1.3, "valkyrie": 1.2, "bomb-tower": 1.5,
    "executioner": 1.3, "bowler": 1.6, "magic-archer": 1.0, "dark-prince": 1.0,
    "princess": 1.2, "witch": 1.2, "electro-wizard": 0.9, "electro-dragon": 1.0,
    "bomber": 1.3, "firecracker": 1.0, "hunter": 0.9, "mega-knight": 1.5,
    "sparky": 2.0, "wizard-ev1": 1.3, "flying-machine": 0.0,
}


def tower_layout(side: str) -> list[tuple[float, float, str]]:
    if side == "defender":
        return [(3.5, 6.0, "princess"), (14.5, 6.0, "princess"), (9.0, 2.0, "king")]
    return [(3.5, 26.0, "princess"), (14.5, 26.0, "princess"), (9.0, 30.0, "king")]


@dataclass
class Unit:
    uid: int
    key: str
    name: str
    side: str            # attacker | defender
    x: float
    y: float
    hp: float
    max_hp: float
    damage: float
    hit_speed: float     # seconds
    rng: float           # tiles
    speed: float         # tiles/second (0 = immobile building/tower)
    targets_air: bool
    targets_ground: bool
    flying: bool
    buildings_only: bool
    splash: float = 0.0
    one_shot: bool = False
    is_tower: bool = False
    is_building: bool = False
    cooldown: float = 0.0
    target_uid: int | None = None
    alive: bool = True

    def can_target(self, other: "Unit") -> bool:
        if self.buildings_only and not (other.is_tower or other.is_building):
            return False
        if other.flying and not self.targets_air:
            return False
        if not other.flying and not self.targets_ground:
            return False
        return True


def _speed(stats) -> float:
    if getattr(stats, "speed_raw", None):
        return max(0.3, stats.speed_raw / 60.0)
    return _SPEED_LABEL.get((stats.speed_label or "medium").strip().lower(), 1.0)


def make_tower(uid: int, side: str, x: float, y: float, kind: str) -> Unit:
    spec = KING if kind == "king" else PRINCESS
    return Unit(
        uid=uid, key=f"{kind}-tower", name=f"{kind.title()} Tower", side=side, x=x, y=y,
        hp=spec.hp, max_hp=spec.hp, damage=spec.damage, hit_speed=spec.hit_speed, rng=spec.rng,
        speed=0.0, targets_air=True, targets_ground=True, flying=False, buildings_only=False,
        is_tower=True, is_building=True,
    )


def make_unit(uid: int, card, stats, side: str, x: float, y: float) -> Unit:
    """Build a combat Unit from a Card + CardStats row. Robust to missing fields."""
    is_building = (card.type == "Building")
    hp = float(stats.hitpoints or 200)
    dmg = float(stats.damage or 0)
    hs = (stats.hit_speed_ms or 1000) / 1000.0
    return Unit(
        uid=uid, key=card.key, name=card.name, side=side, x=x, y=y,
        hp=hp, max_hp=hp, damage=dmg, hit_speed=hs,
        rng=float(stats.range_tiles or 1.0),
        speed=0.0 if is_building else _speed(stats),
        targets_air=bool(stats.targets_air),
        targets_ground=bool(stats.targets_ground) or is_building,
        flying=bool(stats.is_flying),
        buildings_only=bool(stats.targets_buildings_only),
        splash=SPLASH_UNITS.get(card.key, 0.0),
        one_shot=card.key in ONE_SHOT_UNITS,
        is_building=is_building,
    )
