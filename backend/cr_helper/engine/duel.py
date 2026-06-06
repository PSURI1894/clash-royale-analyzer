"""v0 trade calculator: deterministic discrete-hit 1v1 duel."""
from __future__ import annotations

from dataclasses import dataclass

from .units import Unit

_EPS = 1e-9


@dataclass
class DuelResult:
    winner: str | None      # "a" | "b" | None (stalemate / mutual KO)
    a_hp: float
    b_hp: float
    a_hp_pct: float
    b_hp_pct: float
    duration: float


def duel(a: Unit, b: Unit, max_time: float = 30.0) -> DuelResult:
    """Both units stand in range and trade blows every hit_speed seconds.

    Deterministic: hits land on a fixed schedule; simultaneous hits both apply.
    A unit that cannot target the other (wrong air/ground domain) deals no damage.
    """
    a_can = a.can_target(b) and a.damage > 0
    b_can = b.can_target(a) and b.damage > 0
    if not a_can and not b_can:
        return DuelResult(None, a.hp, b.hp, 1.0, 1.0, 0.0)

    hp_a, hp_b = a.hp, b.hp
    next_a = a.hit_speed if a_can else float("inf")
    next_b = b.hit_speed if b_can else float("inf")
    t = 0.0
    while True:
        t = min(next_a, next_b)
        if t == float("inf") or t > max_time:
            break
        if abs(next_a - t) < _EPS:
            hp_b -= a.damage
            next_a += a.hit_speed
        if abs(next_b - t) < _EPS:
            hp_a -= b.damage
            next_b += b.hit_speed
        if hp_a <= 0 or hp_b <= 0:
            break

    a_dead, b_dead = hp_a <= 0, hp_b <= 0
    if a_dead and b_dead:
        winner = None
    elif b_dead:
        winner = "a"
    elif a_dead:
        winner = "b"
    else:  # timed out — higher remaining HP fraction wins the trade
        winner = "a" if (hp_a / a.hp) >= (hp_b / b.hp) else "b"

    return DuelResult(
        winner=winner,
        a_hp=max(hp_a, 0.0), b_hp=max(hp_b, 0.0),
        a_hp_pct=round(max(hp_a, 0.0) / a.hp, 3), b_hp_pct=round(max(hp_b, 0.0) / b.hp, 3),
        duration=round(t, 2),
    )
