"""Application settings.

Loads from environment / a repo-root .env file. Defaults are tuned for local
development with **no Docker required** (SQLite). Switch `DATABASE_URL` to the
Postgres URL to run against the full Docker stack.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]  # .../Clash Royale Helper/backend
_REPO_ROOT = _BACKEND_DIR.parent                    # .../Clash Royale Helper


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local dev default: SQLite file in the backend dir (absolute, cwd-independent).
    database_url: str = f"sqlite:///{(_BACKEND_DIR / 'cr_helper.sqlite3').as_posix()}"

    # Static combat-stats source (RoyaleAPI/cr-api-data, served via GitHub Pages).
    cr_data_base_url: str = "https://royaleapi.github.io/cr-api-data/json"

    # Where downloaded source JSON is cached.
    data_dir: Path = _REPO_ROOT / "data"

    # Knowledge graph backend: "sql" (Docker-free, default) or "neo4j" (full stack).
    graph_backend: str = "sql"
    neo4j_uri: str = ""  # e.g. bolt://localhost:7687 — enables Neo4j seeding when set
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # Official Clash Royale API — battle-log mining (Phase 3). Token is IP-locked:
    # create it at developer.clashroyale.com for your harvesting host's IP.
    clash_royale_api_token: str = ""
    cr_api_base_url: str = "https://api.clashroyale.com/v1"
    # Aggregation guards: min games for a mined edge; max |avg card-level diff| for a "fair" battle.
    mining_min_sample: int = 20
    mining_level_tolerance: float = 1.5

    # RAG tactical advisor (Phase 4).
    embed_backend: str = "hashing"  # hashing (offline, default) | voyage | openai
    embed_dim: int = 512
    advisor_backend: str = "auto"   # auto (Claude if key else stub) | stub | claude
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"        # synthesis (configurable)
    anthropic_router_model: str = "claude-haiku-4-5"  # routing (configurable)
    voyage_api_key: str = ""
    rag_top_k: int = 5

    # Phase 6 — scraping + productionization.
    rate_limit_per_min: int = 120          # per-client request budget (0 disables)
    cache_ttl_seconds: int = 60            # response cache TTL for analyze
    scrape_allow_network: bool = False     # must be explicitly enabled to hit the network
    scrape_user_agent: str = "cr-helper-bot/1.0 (+https://github.com/PSURI1894/clash-royale-analyzer)"
    scrape_min_interval: float = 2.0       # politeness delay between requests (seconds)

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"


settings = Settings()
