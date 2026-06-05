"""Graph repository: fetch raw edges and resolve them into effective edges.

`GraphRepo` is the storage-agnostic interface. `SqlGraphRepo` backs it with the
relational `matchup_edges` table (SQLite/Postgres). A `Neo4jGraphRepo` with the
same surface lives in ``neo4j_repo`` for the full stack.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MatchupEdge
from .resolver import EdgeRow, ResolvedEdge, resolve


def _to_row(e: MatchupEdge) -> EdgeRow:
    return EdgeRow(
        source_key=e.source_key, target_key=e.target_key, relation=e.relation,
        value=e.value, source=e.source, confidence=e.confidence, sample_size=e.sample_size,
    )


def resolve_grouped(rows: list[EdgeRow]) -> list[ResolvedEdge]:
    groups: dict[tuple, list[EdgeRow]] = defaultdict(list)
    for r in rows:
        groups[(r.source_key, r.target_key, r.relation)].append(r)
    resolved = [resolve(g) for g in groups.values()]
    return sorted((r for r in resolved if r), key=lambda r: -r.value)


class GraphRepo:
    def answers_to(self, threat_key: str) -> list[ResolvedEdge]:
        """Cards that counter `threat_key` (best answers first)."""
        raise NotImplementedError

    def counters_by(self, card_key: str) -> list[ResolvedEdge]:
        """What `card_key` itself counters."""
        raise NotImplementedError

    def synergies_for(self, card_key: str) -> list[ResolvedEdge]:
        raise NotImplementedError


class SqlGraphRepo(GraphRepo):
    def __init__(self, session: Session):
        self.session = session

    def answers_to(self, threat_key: str) -> list[ResolvedEdge]:
        edges = self.session.scalars(
            select(MatchupEdge).where(
                MatchupEdge.relation == "counters", MatchupEdge.target_key == threat_key
            )
        ).all()
        return resolve_grouped([_to_row(e) for e in edges])

    def counters_by(self, card_key: str) -> list[ResolvedEdge]:
        edges = self.session.scalars(
            select(MatchupEdge).where(
                MatchupEdge.relation == "counters", MatchupEdge.source_key == card_key
            )
        ).all()
        return resolve_grouped([_to_row(e) for e in edges])

    def synergies_for(self, card_key: str) -> list[ResolvedEdge]:
        edges = self.session.scalars(
            select(MatchupEdge).where(
                MatchupEdge.relation == "synergizes_with",
                (MatchupEdge.source_key == card_key) | (MatchupEdge.target_key == card_key),
            )
        ).all()
        rows: list[EdgeRow] = []
        for e in edges:
            row = _to_row(e)
            if row.target_key == card_key:  # normalize so the queried card is the source
                row.source_key, row.target_key = card_key, row.source_key
            rows.append(row)
        return resolve_grouped(rows)
