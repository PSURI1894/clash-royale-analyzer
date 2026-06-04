"""Curated card-role taxonomy (Phase 1).

cr-api-data has no notion of "win condition", "bait" or "archetype", so these are
hand-curated sets keyed by the exact cr-api-data card keys. They are deliberately
editable/transparent and will be superseded/enriched by the Neo4j knowledge graph
in Phase 2. Keep keys in sync with the catalog (kebab-case).
"""
from __future__ import annotations

# Cards whose primary job is dealing tower damage (the deck's main game plan).
WIN_CONDITIONS: frozenset[str] = frozenset({
    "hog-rider", "royal-giant", "giant", "golem", "lava-hound", "super-lava-hound",
    "balloon", "x-bow", "mortar", "graveyard", "miner", "goblin-barrel", "goblin-drill",
    "royal-hogs", "ram-rider", "battle-ram", "wall-breakers", "three-musketeers",
    "sparky", "elixir-golem", "electro-giant", "goblin-giant", "royal-recruits",
    "skeleton-barrel", "santa-hog-rider",
})

# Cards that can serve as a win condition depending on the deck (counted only if
# no primary win condition is present).
FLEX_WIN_CONDITIONS: frozenset[str] = frozenset({
    "mega-knight", "pekka", "prince", "dark-prince", "bandit", "elite-barbarians",
    "lumberjack", "mighty-miner", "cannon-cart", "golden-knight",
})

# Heavy tanks that anchor a beatdown push.
BEATDOWN_TANKS: frozenset[str] = frozenset({
    "golem", "lava-hound", "super-lava-hound", "electro-giant", "giant",
    "goblin-giant", "elixir-golem",
})

AIR_WIN_CONDITIONS: frozenset[str] = frozenset({"lava-hound", "super-lava-hound", "balloon"})

SIEGE: frozenset[str] = frozenset({"x-bow", "mortar"})

BRIDGE_SPAM: frozenset[str] = frozenset({
    "bandit", "battle-ram", "ram-rider", "royal-ghost", "dark-prince", "prince",
    "raging-prince", "elite-barbarians", "lumberjack", "fisherman",
})

# Swarms / cheap units that bait out spells (spell-bait & log-bait archetypes).
BAIT_CARDS: frozenset[str] = frozenset({
    "goblin-barrel", "princess", "goblin-gang", "skeleton-army", "dart-goblin",
    "firecracker", "bats", "spear-goblins", "guards", "minion-horde", "rascals",
    "goblins", "skeletons",
})

# Cheap reactive spells (resets, chip, swarm clear).
SMALL_SPELLS: frozenset[str] = frozenset({
    "the-log", "zap", "giant-snowball", "barbarian-barrel", "arrows", "royal-delivery",
})

# Expensive damage spells (control / finisher).
BIG_SPELLS: frozenset[str] = frozenset({
    "fireball", "poison", "lightning", "rocket", "earthquake",
})

# Buildings primarily used for defense (pulling tanks / shredding win conditions).
DEFENSIVE_BUILDINGS: frozenset[str] = frozenset({
    "cannon", "tesla", "bomb-tower", "inferno-tower", "goblin-cage", "tombstone",
})

# One-shot / kamikaze units: their cr-api-data DPS is inflated (single hit), so they
# must not count as *sustained* damage / anti-air.
ONE_SHOT_UNITS: frozenset[str] = frozenset({
    "ice-spirit", "fire-spirit", "electro-spirit", "heal-spirit",
})
