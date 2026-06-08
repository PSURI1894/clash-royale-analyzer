"""Spatial arena simulation: movement, targeting, splash, towers, river routing.

Deterministic: units act in a fixed (uid) order each tick, no randomness. Reduced
fidelity — straight-line pathing with bridge routing for ground units, circular
engagement ranges, instantaneous projectiles.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .units import BRIDGE_X, RIVER_Y, Unit

ENGAGE_PAD = 0.6  # body-size allowance added to attack range


@dataclass
class SimEvent:
    t: float
    text: str


@dataclass
class SimResult:
    winner: str  # attacker | defender | draw
    duration: float
    summary: str
    attacker_survivors: list[str] = field(default_factory=list)
    defender_survivors: list[str] = field(default_factory=list)
    defender_tower_damage: int = 0
    towers: list[dict] = field(default_factory=list)
    units: list[dict] = field(default_factory=list)
    events: list[SimEvent] = field(default_factory=list)


def _dist(a: Unit, b: Unit) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


class Arena:
    def __init__(self, units: list[Unit]):
        self.units = units
        self.by_uid = {u.uid: u for u in units}
        self.t = 0.0
        self.events: list[SimEvent] = []

    # ---- targeting ----
    def _nearest_target(self, u: Unit) -> Unit | None:
        best: Unit | None = None
        best_d = float("inf")
        for v in self.units:
            if not v.alive or v.side == u.side or not u.can_target(v):
                continue
            if u.is_tower and v.is_tower:
                continue  # towers don't fire on towers
            d = _dist(u, v)
            if d < best_d:
                best_d, best = d, v
        return best

    def _acquire(self, u: Unit) -> Unit | None:
        if u.target_uid is not None:
            cur = self.by_uid.get(u.target_uid)
            if cur and cur.alive and u.can_target(cur):
                return cur
        tgt = self._nearest_target(u)
        u.target_uid = tgt.uid if tgt else None
        return tgt

    # ---- actions ----
    def _attack(self, u: Unit, target: Unit) -> None:
        u.cooldown = u.hit_speed
        if u.splash > 0:
            victims = [
                v for v in self.units
                if v.alive and v.side != u.side and u.can_target(v)
                and math.hypot(v.x - target.x, v.y - target.y) <= u.splash
            ]
        else:
            victims = [target]
        for v in victims:
            v.hp -= u.damage
            if v.hp <= 0 and v.alive:
                v.alive = False
                if v.is_tower:
                    self.events.append(SimEvent(round(self.t, 1), f"{v.name} ({v.side}) destroyed"))
        if u.one_shot:  # spirit expends itself on its single hit
            u.alive = False

    def _advance(self, u: Unit, target: Unit, dt: float) -> None:
        tx, ty = target.x, target.y
        stop = u.rng + ENGAGE_PAD
        if not u.flying and (u.y - RIVER_Y) * (ty - RIVER_Y) < 0 and abs(u.y - RIVER_Y) > 0.4:
            # ground unit must cross at a bridge first
            tx, ty, stop = min(BRIDGE_X, key=lambda b: abs(b - u.x)), RIVER_Y, 0.0
        dx, dy = tx - u.x, ty - u.y
        d = math.hypot(dx, dy)
        if d <= stop or d == 0:
            return
        step = min(u.speed * dt, d - stop)
        u.x += dx / d * step
        u.y += dy / d * step

    def step(self, dt: float) -> None:
        for u in self.units:  # constructed in uid order
            if not u.alive:
                continue
            if u.cooldown > 0:
                u.cooldown = max(0.0, u.cooldown - dt)
            target = self._acquire(u)
            if target is None:
                continue
            if _dist(u, target) <= u.rng + ENGAGE_PAD:
                if u.cooldown <= 0:
                    self._attack(u, target)
            elif u.speed > 0:
                self._advance(u, target, dt)
        self.t += dt

    def _nontower(self, side: str) -> list[Unit]:
        return [u for u in self.units if u.alive and u.side == side and not u.is_tower]

    def run(self, duration: float = 40.0, dt: float = 0.1) -> SimResult:
        while self.t < duration:
            self.step(dt)
            king = next((u for u in self.units if u.is_tower and u.side == "defender" and u.key == "king-tower"), None)
            if king and not king.alive:
                break
            if not self._nontower("attacker"):  # push spent
                break
        return self._result()

    def _result(self) -> SimResult:
        att_surv = [u.name for u in self._nontower("attacker")]
        def_surv = [u.name for u in self._nontower("defender")]
        def_towers = [u for u in self.units if u.is_tower and u.side == "defender"]
        def_king = next(t for t in def_towers if t.key == "king-tower")
        tower_dmg = int(sum(t.max_hp - max(t.hp, 0.0) for t in def_towers))

        if not def_king.alive:
            winner, summary = "attacker", "Attacker destroyed the King Tower."
        elif any(not t.alive for t in def_towers):
            winner, summary = "attacker", "Attacker took a Princess Tower."
        elif not att_surv and tower_dmg < 50:
            winner, summary = "defender", "Defender shut the push down cleanly."
        elif not att_surv:
            winner, summary = "defender", f"Defender held; the push chipped {tower_dmg} tower HP."
        else:
            winner, summary = "draw", "Push still developing at the time limit."

        towers = [
            {"side": t.side, "kind": t.key, "x": round(t.x, 1), "y": round(t.y, 1),
             "hp": round(max(t.hp, 0.0)), "max_hp": round(t.max_hp), "alive": t.alive}
            for t in self.units if t.is_tower
        ]
        units = [
            {"name": u.name, "side": u.side, "x": round(u.x, 1), "y": round(u.y, 1),
             "hp_pct": round(max(u.hp, 0.0) / u.max_hp, 2)}
            for u in self.units if not u.is_tower and u.alive
        ]
        return SimResult(
            winner=winner, duration=round(self.t, 1), summary=summary,
            attacker_survivors=att_surv, defender_survivors=def_surv,
            defender_tower_damage=tower_dmg, towers=towers, units=units, events=self.events,
        )
