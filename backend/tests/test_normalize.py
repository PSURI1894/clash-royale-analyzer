"""Unit tests for the pure normalization layer (no DB, no network)."""
from __future__ import annotations

from cr_helper.ingest.normalize import normalize, speed_label


def test_speed_label_buckets():
    assert speed_label(45) == "Slow"
    assert speed_label(60) == "Medium"
    assert speed_label(90) == "Fast"
    assert speed_label(120) == "Very Fast"
    assert speed_label(0) is None
    assert speed_label(None) is None


def test_normalize_troop_resolves_character_stats():
    sources = {
        "cards": [
            {
                "key": "knight", "name": "Knight", "sc_key": "Knight", "elixir": 3,
                "type": "Troop", "rarity": "Common", "arena": 0, "id": 26000000,
                "is_evolved": False, "evolved_spells_sc_key": "Knight_EV1",
                "description": "A tough melee fighter.",
            }
        ],
        "cards_stats_troop": [
            {"key": "knight", "name": "Knight", "summon_character": "Knight", "summon_number": 0}
        ],
        "cards_stats_characters": [
            {
                "key": "knight", "name": "Knight", "hitpoints": 690, "damage": 79,
                "hit_speed": 1200, "load_time": 700, "range": 1200, "sight_range": 5500,
                "speed": 60, "attacks_ground": True,
                "hitpoints_per_level": [690, 759], "damage_per_level": [79, 86],
            }
        ],
    }
    [knight] = normalize(sources)

    assert knight.elixir == 3 and knight.type == "Troop"
    assert knight.has_evolution is True
    s = knight.stats
    assert s is not None
    assert s.hitpoints == 690
    assert s.damage == 79
    assert s.dps == round(79 / 1.2, 2)  # ~65.83
    assert s.hit_speed_ms == 1200
    assert s.range_tiles == 1.2
    assert s.speed_label == "Medium"
    assert s.targets_ground is True and s.targets_air is False
    assert s.count == 1


def test_normalize_multi_spawn_uses_summon_number():
    sources = {
        "cards": [{"key": "archers", "name": "Archers", "elixir": 3, "type": "Troop", "id": 1}],
        "cards_stats_troop": [
            {"key": "archers", "summon_character": "Archer", "summon_number": 2}
        ],
        "cards_stats_characters": [
            {"name": "Archer", "hitpoints": 119, "damage": 42, "hit_speed": 900,
             "range": 5000, "speed": 60, "attacks_ground": True, "attacks_air": True}
        ],
    }
    [archers] = normalize(sources)
    assert archers.stats.count == 2
    assert archers.stats.targets_air is True


def test_normalize_spell_damage_via_projectile():
    sources = {
        "cards": [
            {"key": "fireball", "name": "Fireball", "sc_key": "Fireball", "elixir": 4,
             "type": "Spell", "rarity": "Rare", "id": 28000000}
        ],
        "cards_stats_spell": [
            {"key": "fireball", "name": "Fireball", "radius": 2500, "hits_ground": True,
             "hits_air": True}
        ],
        "cards_stats_projectile": [
            {"name": "FireballSpell", "damage": 325, "damage_per_level": [325, 357]}
        ],
    }
    [fireball] = normalize(sources)
    assert fireball.type == "Spell"
    assert fireball.stats is not None
    assert fireball.stats.damage == 325  # resolved via "<sc_key>Spell" projectile
    assert fireball.stats.radius_tiles == 2.5
    assert fireball.stats.targets_air is True


def test_normalize_damage_spell_with_no_spell_record():
    """Fireball/Rocket-style: no spell record at all, damage lives only on a projectile."""
    sources = {
        "cards": [
            {"key": "rocket", "name": "Rocket", "sc_key": "Rocket", "elixir": 6, "type": "Spell"}
        ],
        "cards_stats_projectile": [
            {"name": "RocketSpell", "damage": 700, "radius": 2000, "aoe_to_ground": True,
             "aoe_to_air": True}
        ],
    }
    [rocket] = normalize(sources)
    assert rocket.stats is not None
    assert rocket.stats.damage == 700
    assert rocket.stats.radius_tiles == 2.0  # radius falls back to the projectile's
    assert rocket.stats.targets_air is True


def test_normalize_spell_damage_on_spell_record():
    """Zap-style: damage is carried directly on the spell record."""
    sources = {
        "cards": [{"key": "zap", "name": "Zap", "sc_key": "Zap", "elixir": 2, "type": "Spell"}],
        "cards_stats_spell": [
            {"key": "zap", "name": "Zap", "radius": 2500, "damage": 75,
             "damage_per_level": [75, 82]}
        ],
    }
    [zap] = normalize(sources)
    assert zap.stats.damage == 75
    assert zap.stats.radius_tiles == 2.5


def test_normalize_buff_spell_has_no_damage_but_keeps_radius():
    sources = {
        "cards": [{"key": "rage", "name": "Rage", "sc_key": "Rage", "elixir": 2, "type": "Spell"}],
        "cards_stats_spell": [
            {"key": "rage", "name": "Rage", "radius": 3000, "buff_time": 2000}
        ],
    }
    [rage] = normalize(sources)
    assert rage.stats is not None
    assert rage.stats.damage is None
    assert rage.stats.radius_tiles == 3.0


def test_normalize_building_matched_by_sc_key_name():
    """Elixir Collector: building record has no key; match via sc_key -> record name."""
    sources = {
        "cards": [
            {"key": "elixir-collector", "name": "Elixir Collector", "sc_key": "ElixirCollector",
             "elixir": 6, "type": "Building"}
        ],
        "cards_stats_building": [
            {"name": "ElixirCollector", "hitpoints": 505, "life_time": 65000,
             "hitpoints_per_level": [505, 555]}
        ],
    }
    [collector] = normalize(sources)
    assert collector.stats is not None
    assert collector.stats.hitpoints == 505


def test_mirror_has_no_stats():
    sources = {"cards": [{"key": "mirror", "name": "Mirror", "sc_key": "Mirror", "type": "Spell"}]}
    [mirror] = normalize(sources)
    assert mirror.stats is None
