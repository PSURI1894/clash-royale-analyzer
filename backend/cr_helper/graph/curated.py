"""Curated archetype threat profiles (Phase 2).

Maps a meta archetype to the opponent cards a deck must answer, weighted by how
punishing each is. Kept small and editable; the counter/synergy *edges* live in
``data/curated/matchups.json`` (seeded into the graph).
"""
from __future__ import annotations

# archetype -> [(threat_card_key, severity 0..1), ...]
ARCHETYPE_THREATS: dict[str, list[tuple[str, float]]] = {
    "Lavaloon": [("balloon", 1.0), ("lava-hound", 0.6)],
    "Air Beatdown": [("balloon", 0.9), ("lava-hound", 0.6), ("minion-horde", 0.5)],
    "Golem Beatdown": [("golem", 1.0), ("night-witch", 0.4)],
    "Hog Cycle": [("hog-rider", 1.0)],
    "X-Bow Siege": [("x-bow", 1.0)],
    "Mortar Cycle": [("mortar", 1.0)],
    "Royal Giant": [("royal-giant", 1.0)],
    "Graveyard Control": [("graveyard", 1.0)],
    "P.E.K.K.A Bridge Spam": [("pekka", 0.8), ("battle-ram", 0.7), ("bandit", 0.5)],
    "Mega Knight Bait": [("mega-knight", 0.9), ("goblin-barrel", 0.6)],
    "Balloon Cycle": [("balloon", 1.0)],
    "Sparky Beatdown": [("sparky", 1.0), ("goblin-giant", 0.6)],
}

# Punishing meta threats used for the deck-level "weak against" scan (these have
# broad answer coverage seeded into the graph, so an empty answer set is meaningful).
META_THREATS: list[str] = [
    "balloon", "golem", "hog-rider", "mega-knight", "x-bow",
    "graveyard", "sparky", "pekka", "lava-hound", "royal-giant",
]
