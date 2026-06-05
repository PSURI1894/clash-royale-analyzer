"""Optional Celery wrapper for scheduled mining (full stack; needs Redis).

    celery -A cr_helper.mining.tasks worker --beat

Not required for the CLI or tests — `celery` is an optional dependency
(`pip install -e ".[celery]"`). Kept thin: the real work lives in `pipeline`.
"""
from __future__ import annotations

import os

try:
    from celery import Celery
except ImportError:  # celery not installed — CLI/tests don't need it
    Celery = None  # type: ignore[assignment,misc]


if Celery is not None:
    app = Celery("cr_helper", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    @app.task(name="cr_helper.mining.mine")
    def mine(dataset: str = "api", limit: int = 3000, seed_tags: list[str] | None = None) -> dict:
        from .pipeline import run_mining

        return run_mining(dataset=dataset, limit=limit, seed_tags=seed_tags)

    # Nightly refresh once the official-API harvester is configured.
    app.conf.beat_schedule = {
        "nightly-mining": {
            "task": "cr_helper.mining.mine",
            "schedule": 24 * 3600.0,
            "kwargs": {"dataset": "api", "limit": 5000},
        }
    }
