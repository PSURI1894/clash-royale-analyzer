"""Tests for Phase 5 battle engine: v0 duel + spatial arena (deterministic)."""
from __future__ import annotations

from cr_helper.engine.arena import Arena
from cr_helper.engine.duel import duel
from cr_helper.engine.units import Unit, make_tower, tower_layout


def U(uid, key, side, x, y, hp, dmg, hs=1.0, rng=1.0, spd=1.0,
      air=False, ground=True, fly=False, bo=False, splash=0.0):
    return Unit(
        uid=uid, key=key, name=key, side=side, x=x, y=y, hp=hp, max_hp=hp, damage=dmg,
        hit_speed=hs, rng=rng, speed=spd, targets_air=air, targets_ground=ground,
        flying=fly, buildings_only=bo, splash=splash,
    )


def def_towers():
    return [make_tower(i, "defender", x, y, k) for i, (x, y, k) in enumerate(tower_layout("defender"))]


# ---- v0 duel ----

def test_duel_known_outcome():
    # a: 100hp/10dmg, b: 50hp/5dmg, both 1s hit speed -> a wins, b dies at t=5, a took 4 hits (75 hp).
    r = duel(U(1, "a", "attacker", 0, 0, 100, 10), U(2, "b", "defender", 0, 0, 50, 5))
    assert r.winner == "a"
    assert r.a_hp == 75
    assert r.b_hp == 0


def test_duel_one_sided_when_cannot_be_targeted():
    ground_only = U(1, "ar", "attacker", 0, 0, 100, 20, air=False)        # can't hit air
    flyer = U(2, "ba", "defender", 0, 0, 80, 10, fly=True, air=True)      # hits ground
    r = duel(ground_only, flyer)
    assert r.winner == "b"
    assert r.b_hp_pct == 1.0  # took no damage


def test_duel_is_deterministic():
    a1, b1 = U(1, "a", "attacker", 0, 0, 300, 40), U(2, "b", "defender", 0, 0, 260, 35)
    a2, b2 = U(1, "a", "attacker", 0, 0, 300, 40), U(2, "b", "defender", 0, 0, 260, 35)
    assert duel(a1, b1) == duel(a2, b2)


# ---- spatial arena ----

def _undefended():
    units = def_towers()
    units.append(U(10, "tank", "attacker", 3.5, 9.0, 3000, 300, hs=1.0, rng=1.0, spd=1.0))
    return Arena(units)


def test_arena_undefended_push_takes_a_tower():
    res = _undefended().run(duration=40.0)
    assert res.winner == "attacker"
    assert res.defender_tower_damage > 0


def test_arena_is_deterministic():
    r1 = _undefended().run(duration=40.0)
    r2 = _undefended().run(duration=40.0)
    assert (r1.winner, r1.defender_tower_damage, r1.duration) == (r2.winner, r2.defender_tower_damage, r2.duration)


def test_arena_defender_holds():
    units = def_towers()
    units.append(U(10, "glass", "attacker", 3.5, 9.0, 200, 20, spd=1.0))
    units.append(U(11, "wall", "defender", 3.5, 8.3, 2000, 300, spd=1.0))
    res = Arena(units).run(duration=40.0)
    assert res.winner == "defender"
    assert res.attacker_survivors == []


def test_arena_splash_clears_swarm():
    units = def_towers()
    units.append(U(10, "splasher", "attacker", 3.5, 12.0, 1500, 200, hs=1.0, rng=5.0, spd=1.0, splash=1.5))
    for i in range(3):  # three clustered weak defenders
        units.append(U(20 + i, "skel", "defender", 3.4 + i * 0.1, 9.0, 80, 30, spd=1.0))
    res = Arena(units).run(duration=12.0)
    assert res.defender_survivors == []
