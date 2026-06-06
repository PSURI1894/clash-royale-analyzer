"""Vector store. SqlVectorStore brute-forces cosine over GuideChunk rows.

Fine for a curated corpus (hundreds of chunks). For the full stack, swap in a
pgvector-backed store (a `<->` ORDER BY query) behind the same surface.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import GuideChunk
from .embed import cosine


class SqlVectorStore:
    def __init__(self, session: Session):
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(GuideChunk)) or 0

    def upsert(self, chunk: dict, embedding: list[float], model: str) -> None:
        row = self.session.get(GuideChunk, chunk["id"])
        if row is None:
            row = GuideChunk(id=chunk["id"])
            self.session.add(row)
        row.title = chunk["title"]
        row.topic = chunk["topic"]
        row.archetype = chunk.get("archetype", "general")
        row.cards = chunk.get("cards", [])
        row.text = chunk["text"]
        row.embedding = embedding
        row.embed_model = model

    def search(
        self,
        query_vec: list[float],
        k: int = 5,
        archetype: str | None = None,
        boost: float = 0.12,
    ) -> list[tuple[GuideChunk, float]]:
        rows = self.session.scalars(
            select(GuideChunk).where(GuideChunk.embedding.is_not(None))
        ).all()
        scored: list[tuple[GuideChunk, float]] = []
        for r in rows:
            score = cosine(query_vec, r.embedding)
            if archetype:  # hybridize: nudge toward chunks tagged for this opponent
                if r.archetype == archetype:
                    score += boost
                elif r.archetype != "general":
                    score -= boost * 0.5
            scored.append((r, score))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]
