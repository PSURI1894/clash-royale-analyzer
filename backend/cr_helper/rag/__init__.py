"""RAG tactical advisor (Phase 4).

Retrieves original strategy/placement notes and fuses them with hard facts from
the analyzer, graph and mining into an EvidencePack. An advisor client (offline
deterministic Stub, or real Claude) emits a structured report, and a grounding
guardrail verifies every number in the output came from the evidence — the
anti-hallucination spine. Embeddings/vector search run on SQLite (Python cosine)
by default; swap in Voyage + pgvector for the full stack.
"""
