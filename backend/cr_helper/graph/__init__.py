"""Knowledge graph (Phase 2).

A provenance-bearing matchup graph (counters / synergies / win-condition edges)
with a confidence-weighted ensemble resolver that blends curated, mined,
simulated and scraped sources into one effective edge. Storage-agnostic: a
relational backend (SQLite/Postgres) runs Docker-free now; a Neo4j adapter is
provided for the full stack.
"""
