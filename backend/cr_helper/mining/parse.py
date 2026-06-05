"""Parse official-API-shaped battle JSON into normalized, catalog-native records."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Card

# 1v1 ladder / ranked battle types we mine (exclude 2v2, challenges, friendlies, clan war collection).
ALLOWED_TYPES = {"PvP", "pathOfLegend", "Ranked1v1", "Ranked1v1_NewArena2025", "casual1v1"}


@dataclass
class BattleRecord:
    battle_uid: str
    dataset: str
    player_tag: str | None
    opponent_tag: str | None
    won: bool
    mode: str | None
    team_cards: list[str]
    opponent_cards: list[str]
    team_avg_level: float | None
    opponent_avg_level: float | None
    trophies: int | None
    battle_time: datetime | None
    opponent_tags_seen: list[str] = field(default_factory=list)


class CardIndex:
    """Maps battle-log card refs ({id, name, ...}) to catalog card keys."""

    def __init__(self, by_id: dict[int, str], by_name: dict[str, str]):
        self.by_id = by_id
        self.by_name = by_name

    @classmethod
    def from_session(cls, session: Session) -> "CardIndex":
        by_id: dict[int, str] = {}
        by_name: dict[str, str] = {}
        for key, card_id, name in session.execute(select(Card.key, Card.card_id, Card.name)):
            if card_id is not None:
                by_id[card_id] = key
            if name:
                by_name[name.lower()] = key
        return cls(by_id, by_name)

    def key_for(self, card: dict) -> str | None:
        cid = card.get("id")
        if cid is not None and cid in self.by_id:
            return self.by_id[cid]
        return self.by_name.get((card.get("name") or "").lower())


def _parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _avg_level(cards: list[dict]) -> float | None:
    """Average card level normalized to the 1..14 king-tower scale (rarity-agnostic)."""
    levels: list[int] = []
    for c in cards:
        lvl = c.get("level")
        if lvl is None:
            continue
        maxl = c.get("maxLevel") or 14
        levels.append(lvl + (14 - maxl))
    return round(sum(levels) / len(levels), 2) if levels else None


def _deck_keys(cards: list[dict], idx: CardIndex) -> list[str] | None:
    keys: list[str] = []
    for c in cards:
        k = idx.key_for(c)
        if k is None:
            return None  # unmappable card -> drop battle for data integrity
        keys.append(k)
    return keys if len(keys) == 8 else None


def battle_uid(team_tag, opp_tag, time_str, team_crowns, opp_crowns) -> str:
    """Stable id so the same battle, seen from both players' logs, dedupes."""
    tags = "|".join(sorted([team_tag or "?", opp_tag or "?"]))
    raw = f"{tags}|{time_str}|{min(team_crowns, opp_crowns)}-{max(team_crowns, opp_crowns)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def parse_battle(raw: dict, idx: CardIndex, dataset: str) -> BattleRecord | None:
    if raw.get("type") not in ALLOWED_TYPES:
        return None
    team = raw.get("team") or []
    opp = raw.get("opponent") or []
    if len(team) != 1 or len(opp) != 1:  # 1v1 only
        return None
    t, o = team[0], opp[0]
    team_keys = _deck_keys(t.get("cards") or [], idx)
    opp_keys = _deck_keys(o.get("cards") or [], idx)
    if not team_keys or not opp_keys:
        return None
    tc, oc = t.get("crowns", 0), o.get("crowns", 0)
    if tc == oc:  # exclude draws
        return None
    return BattleRecord(
        battle_uid=battle_uid(t.get("tag"), o.get("tag"), raw.get("battleTime", ""), tc, oc),
        dataset=dataset,
        player_tag=t.get("tag"),
        opponent_tag=o.get("tag"),
        won=tc > oc,
        mode=(raw.get("gameMode") or {}).get("name") or raw.get("type"),
        team_cards=team_keys,
        opponent_cards=opp_keys,
        team_avg_level=_avg_level(t.get("cards") or []),
        opponent_avg_level=_avg_level(o.get("cards") or []),
        trophies=t.get("startingTrophies"),
        battle_time=_parse_time(raw.get("battleTime")),
        opponent_tags_seen=[o["tag"]] if o.get("tag") else [],
    )
