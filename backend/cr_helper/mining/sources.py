"""Battle sources: real official API (IP-locked) and offline synthetic generator."""
from __future__ import annotations

import math
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator

import httpx

from ..config import settings


class BattleSource(ABC):
    @abstractmethod
    def iter_raw_battles(self, limit: int) -> Iterator[dict]:
        """Yield up to `limit` raw battles in official-API shape."""

    def close(self) -> None:  # optional
        pass


class OfficialApiSource(BattleSource):
    """BFS-crawls real battle logs starting from seed player tags.

    Requires a token whose IP allowlist includes this host (keys are IP-locked).
    Opponent tags found in each log are enqueued to expand coverage.
    """

    def __init__(
        self,
        seed_tags: list[str],
        token: str | None = None,
        base_url: str | None = None,
        delay: float = 0.2,
    ):
        self.token = token or settings.clash_royale_api_token
        if not self.token:
            raise RuntimeError(
                "CLASH_ROYALE_API_TOKEN is not set. Create an IP-whitelisted key at "
                "developer.clashroyale.com and put it in .env."
            )
        if not seed_tags:
            raise RuntimeError("OfficialApiSource needs at least one seed player tag (e.g. #2PP).")
        self.base = (base_url or settings.cr_api_base_url).rstrip("/")
        self.seed_tags = seed_tags
        self.delay = delay
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
            timeout=20.0,
        )

    def _battlelog(self, tag: str) -> list[dict]:
        enc = tag.replace("#", "%23")
        r = self._client.get(f"{self.base}/players/{enc}/battlelog")
        if r.status_code == 403:
            raise PermissionError(
                "403 from the Clash Royale API — your token's IP allowlist almost certainly "
                "doesn't include this host. Add the host's public IP to the key at "
                f"developer.clashroyale.com. Server said: {r.text[:200]}"
            )
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()

    def iter_raw_battles(self, limit: int) -> Iterator[dict]:
        seen: set[str] = set()
        queue: list[str] = list(self.seed_tags)
        produced = 0
        while queue and produced < limit:
            tag = queue.pop(0)
            if tag in seen:
                continue
            seen.add(tag)
            try:
                battles = self._battlelog(tag)
            except PermissionError:
                raise
            except Exception:  # noqa: BLE001 — skip a flaky player, keep crawling
                continue
            for b in battles:
                yield b
                produced += 1
                for opp in b.get("opponent") or []:
                    ot = opp.get("tag")
                    if ot and ot not in seen:
                        queue.append(ot)
                if produced >= limit:
                    break
            time.sleep(self.delay)

    def close(self) -> None:
        self._client.close()


class SyntheticSource(BattleSource):
    """Offline generator of API-shaped battles for dev/test/demo.

    Outcomes are biased by the curated counter graph: a side gains advantage for
    each strong counter it holds against the other's cards. The resulting mined
    win-rates therefore correlate with expert priors but regress toward 0.5 from
    whole-deck noise — exactly the empirical signal real mining surfaces. This is
    NOT real data; it is always stored under dataset="synthetic".
    """

    def __init__(
        self,
        card_pool: list[dict],
        counter_value: Callable[[str, str], float | None],
        seed: int = 7,
    ):
        if len(card_pool) < 8:
            raise ValueError("SyntheticSource needs a card pool of at least 8 cards.")
        self.pool = card_pool
        self.counter_value = counter_value
        self.rng = random.Random(seed)

    def iter_raw_battles(self, limit: int) -> Iterator[dict]:
        for i in range(limit):
            t_deck = self.rng.sample(self.pool, 8)
            o_deck = self.rng.sample(self.pool, 8)
            adv = self._advantage([c["key"] for c in t_deck], [c["key"] for c in o_deck])
            skill = self.rng.gauss(0, 0.5)
            p_team = 1.0 / (1.0 + math.exp(-(1.2 * adv + skill)))
            if self.rng.random() < p_team:
                tc, oc = self.rng.choice([1, 2, 2, 3]), 0
            else:
                tc, oc = 0, self.rng.choice([1, 2, 2, 3])
            t_lvl = self.rng.randint(11, 14)
            o_lvl = max(11, min(14, t_lvl + self.rng.choice([-1, 0, 0, 1])))
            yield {
                "type": "PvP",
                "battleTime": f"202406{(i % 28) + 1:02d}T{(i % 24):02d}0000.000Z",
                "gameMode": {"id": 72000006, "name": "Ladder"},
                "team": [self._side(f"#T{i}", t_deck, tc, t_lvl)],
                "opponent": [self._side(f"#O{i}", o_deck, oc, o_lvl)],
            }

    def _advantage(self, team: list[str], opp: list[str]) -> float:
        s = 0.0
        for a in team:
            for b in opp:
                v = self.counter_value(a, b)
                if v is not None:
                    s += v - 0.5
        for a in opp:
            for b in team:
                v = self.counter_value(a, b)
                if v is not None:
                    s -= v - 0.5
        return s

    def _side(self, tag: str, deck: list[dict], crowns: int, level: int) -> dict:
        return {
            "tag": tag,
            "name": tag,
            "startingTrophies": 6000,
            "trophyChange": 30 if crowns > 0 else -30,
            "crowns": crowns,
            "cards": [
                {"name": c["name"], "id": c["id"], "level": level, "maxLevel": 14, "elixirCost": 0}
                for c in deck
            ],
        }
