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

    # Phase 3+ (left blank until needed).
    clash_royale_api_token: str = ""
    anthropic_api_key: str = ""

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"


settings = Settings()
