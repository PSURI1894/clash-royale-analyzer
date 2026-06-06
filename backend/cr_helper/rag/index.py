"""Build the RAG index: embed the corpus and upsert into the vector store.

    python -m cr_helper.rag.index
"""
from __future__ import annotations

from ..db import SessionLocal, init_db
from .corpus import load_corpus
from .embed import get_embedder
from .store import SqlVectorStore


def main() -> None:
    init_db()
    chunks = load_corpus()
    embedder = get_embedder()
    texts = [f"{c['title']}. {c['text']}" for c in chunks]
    vectors = embedder.embed_many(texts)

    with SessionLocal() as session:
        store = SqlVectorStore(session)
        for chunk, vec in zip(chunks, vectors):
            store.upsert(chunk, vec, embedder.name)
        session.commit()
        print(f"Indexed {len(chunks)} chunks with {embedder.name} -> {store.count()} in store.")


if __name__ == "__main__":
    main()
