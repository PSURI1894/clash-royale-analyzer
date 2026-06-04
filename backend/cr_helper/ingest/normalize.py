"""Normalize raw cr-api-data into unified card records.

Pure functions (no DB, no network) so they are trivially unit-testable.

cr-api-data spreads combat numbers across files and links them inconsistently,
so each playable card is resolved by trying several join keys in order
(``key`` -> ``sc_key`` -> normalized name):

    Troop:    cards -> cards_stats_troop (count + summon_character)
                    -> cards_stats_characters (hp/damage/hit_speed/...)
    Building: cards -> cards_stats_building
    Spell:    cards -> cards_stats_spell (radius/duration/buff)
              damage chain: spell.damage -> spell.projectile -> normalized projectile

Damage spells (Fireball, Rocket, ...) have *no* spell record and live only in
the projectile file; some (Zap) carry damage on the spell record; Lightning
points at a (typo'd) projectile name. DoT spells (Poison/Earthquake) keep a null
single-hit damage by design.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

# cr-api-data movement speed (game units) -> in-game label.
_SPEED_BUCKETS = [(45, "Slow"), (60, "Medium"), (90, "Fast")]
_PROJ_SUFFIX_RE = re.compile(r"(spell|projectile|rolling|deco)", re.IGNORECASE)


def speed_label(speed: int | None) -> str | None:
    if not speed:
        return None
    for threshold, label in _SPEED_BUCKETS:
        if speed <= threshold:
            return label
    return "Very Fast"


def _norm(s: str | None) -> str:
    """Lowercase, strip non-alphanumerics (so 'Elixir Collector' == 'ElixirCollector')."""
    return re.sub(r"[^a-z0-9]", "", s.lower()) if s else ""


def _norm_proj(name: str) -> str:
    """Normalized projectile key with common suffixes removed (FireballSpell -> fireball)."""
    return _norm(_PROJ_SUFFIX_RE.sub("", name))


def _flag(record: dict | None, key: str) -> bool:
    return bool(record.get(key)) if record else False


class CardStatsRecord(BaseModel):
    hitpoints: int | None = None
    damage: int | None = None
    dps: float | None = None
    hit_speed_ms: int | None = None
    load_time_ms: int | None = None
    range_raw: int | None = None
    range_tiles: float | None = None
    sight_range_raw: int | None = None
    speed_raw: int | None = None
    speed_label: str | None = None
    targets_ground: bool = False
    targets_air: bool = False
    targets_buildings_only: bool = False
    is_flying: bool = False
    count: int = 1
    radius_raw: int | None = None
    radius_tiles: float | None = None
    duration_ms: int | None = None
    hitpoints_per_level: list | None = None
    damage_per_level: list | None = None
    raw: dict | None = None


class CardRecord(BaseModel):
    key: str
    card_id: int | None = None
    name: str
    elixir: int | None = None
    rarity: str | None = None
    type: str | None = None
    arena: int | None = None
    description: str | None = None
    is_evolved: bool = False
    has_evolution: bool = False
    stats: CardStatsRecord | None = None


def _by(rows: list[dict], field: str) -> dict[str, dict]:
    return {r[field]: r for r in rows if r.get(field)}


def _by_norm(rows: list[dict], field: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        value = r.get(field)
        if value:
            out.setdefault(_norm(value), r)
    return out


def _index_projectiles(projs: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_name = {p["name"]: p for p in projs if p.get("name")}
    by_norm: dict[str, dict] = {}
    for p in projs:
        name = p.get("name")
        if name and p.get("damage"):
            by_norm.setdefault(_norm_proj(name), p)
    return by_name, by_norm


def _resolve_unit_damage(unit: dict, proj_by_name: dict) -> tuple[int | None, list | None]:
    """Damage from the unit directly, else from its referenced projectile."""
    damage = unit.get("damage") or 0
    dpl = unit.get("damage_per_level")
    if damage:
        return damage, dpl
    proj_name = unit.get("projectile")
    if proj_name and proj_name in proj_by_name:
        proj = proj_by_name[proj_name]
        return (proj.get("damage") or None), proj.get("damage_per_level")
    return (damage or None), dpl


def _stats_from_unit(unit: dict, count: int, proj_by_name: dict) -> CardStatsRecord:
    damage, dpl = _resolve_unit_damage(unit, proj_by_name)
    hit_speed = unit.get("hit_speed") or None
    dps = round(damage / (hit_speed / 1000), 2) if damage and hit_speed else None
    rng = unit.get("range")
    return CardStatsRecord(
        hitpoints=unit.get("hitpoints") or None,
        damage=damage,
        dps=dps,
        hit_speed_ms=hit_speed,
        load_time_ms=unit.get("load_time") or None,
        range_raw=rng,
        range_tiles=round(rng / 1000, 3) if rng else None,
        sight_range_raw=unit.get("sight_range") or None,
        speed_raw=unit.get("speed") or None,
        speed_label=speed_label(unit.get("speed")),
        targets_ground=bool(unit.get("attacks_ground")),
        targets_air=bool(unit.get("attacks_air")),
        targets_buildings_only=bool(unit.get("target_only_buildings")),
        is_flying=bool(unit.get("flying_height")),
        count=count,
        hitpoints_per_level=unit.get("hitpoints_per_level"),
        damage_per_level=dpl,
        raw=unit,
    )


def _stats_from_spell(
    spell: dict | None, card: dict, proj_by_name: dict, proj_by_norm: dict
) -> CardStatsRecord | None:
    damage: int | None = None
    dpl: list | None = None
    proj: dict | None = None

    # 1. Damage carried directly on the spell record (e.g. Zap).
    if spell and spell.get("damage"):
        damage, dpl = spell.get("damage"), spell.get("damage_per_level")
    # 2. Explicit projectile reference on the spell record (e.g. Lightning -> "LighningSpell").
    if damage is None and spell:
        pname = spell.get("projectile") or spell.get("spawn_projectile")
        if pname and pname in proj_by_name:
            proj = proj_by_name[pname]
            damage, dpl = proj.get("damage"), proj.get("damage_per_level")
    # 3. Damage spells with no spell record live only as a projectile (Fireball, Rocket, ...).
    if damage is None:
        for cand in (_norm(card.get("sc_key")), _norm(card.get("name"))):
            if cand and cand in proj_by_norm:
                proj = proj_by_norm[cand]
                damage, dpl = proj.get("damage"), proj.get("damage_per_level")
                break

    # Nothing to record (e.g. Mirror).
    if spell is None and proj is None and damage is None:
        return None

    radius = (spell.get("radius") if spell else None) or (proj.get("radius") if proj else None)
    duration = (spell.get("life_duration") or spell.get("buff_time")) if spell else None
    return CardStatsRecord(
        damage=damage or None,
        damage_per_level=dpl,
        radius_raw=radius,
        radius_tiles=round(radius / 1000, 3) if radius else None,
        duration_ms=duration,
        targets_ground=_flag(spell, "hits_ground") or _flag(proj, "aoe_to_ground"),
        targets_air=_flag(spell, "hits_air") or _flag(proj, "aoe_to_air"),
        raw=spell or proj,
    )


def _find_unit(card: dict, by_key: dict, by_name: dict, by_norm: dict) -> dict | None:
    """Resolve a card to its stat record via key -> sc_key -> name -> normalized name."""
    sc, name = card.get("sc_key"), card.get("name")
    return (
        by_key.get(card.get("key"))
        or by_name.get(sc)
        or by_name.get(name)
        or by_norm.get(_norm(sc))
        or by_norm.get(_norm(name))
    )


def normalize(sources: dict[str, list[dict]]) -> list[CardRecord]:
    cards = sources.get("cards", [])
    troop_by_key = _by(sources.get("cards_stats_troop", []), "key")

    chars = sources.get("cards_stats_characters", [])
    char_by_key, char_by_name, char_by_norm = _by(chars, "key"), _by(chars, "name"), _by_norm(chars, "name")

    blds = sources.get("cards_stats_building", [])
    bld_by_key, bld_by_name, bld_by_norm = _by(blds, "key"), _by(blds, "name"), _by_norm(blds, "name")

    spell_by_key = _by(sources.get("cards_stats_spell", []), "key")
    proj_by_name, proj_by_norm = _index_projectiles(sources.get("cards_stats_projectile", []))

    records: list[CardRecord] = []
    for c in cards:
        key = c.get("key")
        if not key:
            continue
        ctype = c.get("type")
        stats: CardStatsRecord | None = None

        if ctype == "Troop":
            troop = troop_by_key.get(key)
            count = 1
            unit = None
            if troop:
                summon_n = troop.get("summon_number") or 0
                count = summon_n if summon_n > 0 else 1
                summon = troop.get("summon_character")
                if summon:
                    unit = char_by_name.get(summon)
            unit = unit or _find_unit(c, char_by_key, char_by_name, char_by_norm)
            if unit:
                stats = _stats_from_unit(unit, count, proj_by_name)
        elif ctype == "Building":
            unit = _find_unit(c, bld_by_key, bld_by_name, bld_by_norm)
            if unit:
                stats = _stats_from_unit(unit, 1, proj_by_name)
        elif ctype == "Spell":
            stats = _stats_from_spell(spell_by_key.get(key), c, proj_by_name, proj_by_norm)

        records.append(
            CardRecord(
                key=key,
                card_id=c.get("id"),
                name=c.get("name", key),
                elixir=c.get("elixir"),
                rarity=c.get("rarity"),
                type=ctype,
                arena=c.get("arena"),
                description=c.get("description"),
                is_evolved=bool(c.get("is_evolved")),
                has_evolution=bool(c.get("evolved_spells_sc_key")),
                stats=stats,
            )
        )
    return records
