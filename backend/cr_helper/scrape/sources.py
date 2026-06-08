"""Scrape sources: offline fixture (default) and a guarded HTTP scraper."""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from ..config import settings


class ScrapeSource(ABC):
    @abstractmethod
    def fetch_meta(self) -> dict:
        """Return {"cards": [{key, win_rate, usage}], "counters": [{a, b, win_rate}]}."""


class FixtureScrapeSource(ScrapeSource):
    """Reads the synthetic placeholder meta — no network, deterministic, safe."""

    def __init__(self, path: Path | None = None):
        self.path = path or (settings.data_dir / "curated" / "scraped_meta.json")

    def fetch_meta(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))


class HttpScrapeSource(ScrapeSource):
    """Real scraper: respects robots.txt, rate-limits, and is network-gated.

    Disabled unless `settings.scrape_allow_network` is True. You must supply a
    site-specific `parser(html) -> dict` and confirm the site's Terms of Service
    permit scraping. Results should be treated as a cross-check, never redistributed.
    """

    def __init__(self, url: str, parser: Callable[[str], dict]):
        self.url = url
        self.parser = parser
        self._last = 0.0
        self._robot = None

    def _robots_allow(self, url: str) -> bool:
        from urllib.robotparser import RobotFileParser

        if self._robot is None:
            self._robot = RobotFileParser()
            p = urlparse(url)
            self._robot.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
            try:
                self._robot.read()
            except Exception:  # noqa: BLE001 — if robots is unreachable, refuse
                return False
        return self._robot.can_fetch(settings.scrape_user_agent, url)

    def _get(self, url: str) -> str:
        if not settings.scrape_allow_network:
            raise RuntimeError(
                "Network scraping is disabled. Set SCRAPE_ALLOW_NETWORK=true only after "
                "confirming the target site's Terms of Service permit it."
            )
        if not self._robots_allow(url):
            raise PermissionError(f"robots.txt disallows {url} for {settings.scrape_user_agent}")
        wait = settings.scrape_min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        import httpx

        resp = httpx.get(url, headers={"User-Agent": settings.scrape_user_agent}, timeout=20.0)
        self._last = time.monotonic()
        resp.raise_for_status()
        return resp.text

    def fetch_meta(self) -> dict:
        return self.parser(self._get(self.url))
