"""Load the curated strategy corpus (original, paraphrased notes)."""
from __future__ import annotations

import json

from ..config import settings


def corpus_path():
    return settings.data_dir / "curated" / "strategy.json"


def load_corpus() -> list[dict]:
    data = json.loads(corpus_path().read_text(encoding="utf-8"))
    return data["chunks"]
