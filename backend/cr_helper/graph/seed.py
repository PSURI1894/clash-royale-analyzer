"""Seed the knowledge graph from curated data.

    python -m cr_helper.graph.seed

Idempotent: re-running updates existing curated edges in place. Seeds the SQL
graph always; also seeds Neo4j when NEO4J_URI is configured.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal, init_db
from ..models import Card, MatchupEdge

CURATED_CONFIDENCE = 0.6


def _curated_path():
    return settings.data_dir / "curated" / "matchups.json"


def load_curated_edges() -> list[dict]:
    data = json.loads(_curated_path().read_text(encoding="utf-8"))
    rows: list[dict] = []
    for e in data.get("counters", []):
        rows.append({"source_key": e["a"], "target_key": e["b"], "relation": "counters",
                     "value": float(e.get("value", 0.7)), "note": e.get("note")})
    for e in data.get("synergies", []):
        rows.append({"source_key": e["a"], "target_key": e["b"], "relation": "synergizes_with",
                     "value": float(e.get("value", 0.6)), "note": e.get("note")})
    return rows


def seed_sql(session: Session, rows: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    for r in rows:
        existing = session.scalar(
            select(MatchupEdge).where(
                MatchupEdge.source_key == r["source_key"],
                MatchupEdge.target_key == r["target_key"],
                MatchupEdge.relation == r["relation"],
                MatchupEdge.source == "curated",
            )
        )
        if existing:
            existing.value = r["value"]
            existing.confidence = CURATED_CONFIDENCE
            existing.note = r.get("note")
            updated += 1
        else:
            session.add(MatchupEdge(
                source_key=r["source_key"], target_key=r["target_key"], relation=r["relation"],
                target_kind="card", value=r["value"], source="curated",
                confidence=CURATED_CONFIDENCE, sample_size=0, note=r.get("note"),
            ))
            inserted += 1
    session.commit()
    return inserted, updated


def main() -> None:
    rows = load_curated_edges()
    print(f"Loaded {len(rows)} curated edges from {_curated_path()}")

    init_db()
    with SessionLocal() as session:
        known = set(session.scalars(select(Card.key)).all())
        if known:
            unknown = sorted({k for r in rows for k in (r["source_key"], r["target_key"]) if k not in known})
            if unknown:
                print(f"WARNING: {len(unknown)} unknown card keys in curated data: {unknown}")
        inserted, updated = seed_sql(session, rows)
    print(f"SQL graph: {inserted} inserted, {updated} updated.")

    if settings.neo4j_uri:
        try:
            from .neo4j_repo import seed_neo4j

            count = seed_neo4j(rows)
            print(f"Neo4j graph: {count} edges merged into {settings.neo4j_uri}.")
        except Exception as exc:  # noqa: BLE001 — optional path
            print(f"Neo4j seeding skipped ({type(exc).__name__}): {exc}")


if __name__ == "__main__":
    main()
