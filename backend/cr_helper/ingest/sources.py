"""Download (and cache) the cr-api-data JSON source files.

Cached under ``data/raw/`` so re-runs are offline and reproducible. The card
combat model is a *join across files*: a playable card resolves to a unit via
the troop/building/spell records, whose combat numbers live in the characters /
building / projectile files.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from ..config import settings

FILES: list[str] = [
    "cards",                    # catalog: key, name, elixir, type, rarity, arena, id
    "cards_stats_troop",        # card -> summon_character + summon_number (count)
    "cards_stats_characters",   # troop combat stats: hp, damage, hit_speed, range...
    "cards_stats_building",     # building & tower combat stats
    "cards_stats_spell",        # spell radius / duration / buff
    "cards_stats_projectile",   # projectile/spell damage
]


def _cache_path(name: str) -> Path:
    return settings.raw_data_dir / f"{name}.json"


def download_sources(force_refresh: bool = False) -> dict[str, list[dict]]:
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, list[dict]] = {}
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for name in FILES:
            path = _cache_path(name)
            if path.exists() and not force_refresh:
                out[name] = json.loads(path.read_text(encoding="utf-8"))
                continue
            resp = client.get(f"{settings.cr_data_base_url}/{name}.json")
            resp.raise_for_status()
            data = resp.json()
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            out[name] = data
    return out
