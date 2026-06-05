"""Neo4j adapter for the knowledge graph (full-stack path).

Same surface as `SqlGraphRepo`. The `neo4j` driver is an optional dependency
(install with `pip install -e ".[neo4j]"`); it is imported lazily so the SQL
path never requires it. Verify this path once Neo4j is up (docker compose up).
"""
from __future__ import annotations

from ..config import settings
from .repo import GraphRepo, resolve_grouped
from .resolver import EdgeRow, ResolvedEdge

_REL = {"counters": "COUNTERS", "synergizes_with": "SYNERGIZES_WITH"}


def _driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )


def _rows(result, relation: str) -> list[EdgeRow]:
    return [
        EdgeRow(
            source_key=r["src"], target_key=r["tgt"], relation=relation,
            value=r["value"], source=r["source"], confidence=r["confidence"],
            sample_size=r["sample_size"],
        )
        for r in result
    ]


class Neo4jGraphRepo(GraphRepo):
    def __init__(self, driver=None):
        self.driver = driver or _driver()

    def _run(self, cypher: str, relation: str, **params) -> list[ResolvedEdge]:
        with self.driver.session() as s:
            return resolve_grouped(_rows(s.run(cypher, **params), relation))

    def answers_to(self, threat_key: str) -> list[ResolvedEdge]:
        return self._run(
            "MATCH (a:Card)-[e:COUNTERS]->(b:Card {key:$k}) "
            "RETURN a.key AS src, b.key AS tgt, e.value AS value, e.source AS source, "
            "e.confidence AS confidence, e.sample_size AS sample_size",
            "counters", k=threat_key,
        )

    def counters_by(self, card_key: str) -> list[ResolvedEdge]:
        return self._run(
            "MATCH (a:Card {key:$k})-[e:COUNTERS]->(b:Card) "
            "RETURN a.key AS src, b.key AS tgt, e.value AS value, e.source AS source, "
            "e.confidence AS confidence, e.sample_size AS sample_size",
            "counters", k=card_key,
        )

    def synergies_for(self, card_key: str) -> list[ResolvedEdge]:
        return self._run(
            "MATCH (a:Card {key:$k})-[e:SYNERGIZES_WITH]-(b:Card) "
            "RETURN $k AS src, b.key AS tgt, e.value AS value, e.source AS source, "
            "e.confidence AS confidence, e.sample_size AS sample_size",
            "synergizes_with", k=card_key,
        )


def seed_neo4j(rows: list[dict]) -> int:
    driver = _driver()
    count = 0
    with driver.session() as s:
        s.run("CREATE CONSTRAINT card_key IF NOT EXISTS FOR (c:Card) REQUIRE c.key IS UNIQUE")
        for r in rows:
            rel = _REL.get(r["relation"], "COUNTERS")
            s.run(
                f"MERGE (a:Card {{key:$a}}) MERGE (b:Card {{key:$b}}) "
                f"MERGE (a)-[e:{rel}]->(b) "
                f"SET e.value=$value, e.source='curated', e.confidence=0.6, e.sample_size=0",
                a=r["source_key"], b=r["target_key"], value=r["value"],
            )
            count += 1
    driver.close()
    return count
