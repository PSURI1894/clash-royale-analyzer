"""Query-time retrieval: embed the query, search the vector store."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import GuideChunk
from .embed import Embedder, get_embedder
from .store import SqlVectorStore


class Retriever:
    def __init__(self, session: Session, embedder: Embedder | None = None):
        self.store = SqlVectorStore(session)
        self.embedder = embedder or get_embedder()

    def retrieve(
        self, query: str, k: int = 5, archetype: str | None = None
    ) -> list[tuple[GuideChunk, float]]:
        return self.store.search(self.embedder.embed(query), k=k, archetype=archetype)
