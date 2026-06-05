"""The confidence-weighted ensemble resolver.

Each (source_key, target_key, relation) may have several edges from different
data sources. We blend them with a precision-weighted average where each edge's
weight reflects how much evidence it carries:

    curated   -> a fixed prior weight (expert opinion, cold-start)
    scraped   -> a small fixed weight (cross-check only)
    mined      -> grows with the number of observed battles (sample_size)
    simulated  -> grows with the number of simulations, discounted for fidelity

So as real battle data accumulates (Phase 3) the value moves off the curated
prior toward empirical reality, and the blended confidence rises with total
evidence. This is the single abstraction that makes "use all sources" coherent.
"""
from __future__ import annotations

from dataclasses import dataclass

# Tunables (pseudo-observation weights).
K_CURATED = 5.0
K_SCRAPED = 3.0
SIM_TRUST = 0.5
MINED_CAP = 400
SIM_CAP = 100
K0 = 3.0  # smoothing for blended confidence


@dataclass
class EdgeRow:
    source_key: str
    target_key: str
    relation: str
    value: float
    source: str
    confidence: float
    sample_size: int = 0


@dataclass
class ResolvedEdge:
    source_key: str
    target_key: str
    relation: str
    value: float
    confidence: float
    sources: list[str]


def edge_weight(row: EdgeRow) -> float:
    if row.source == "mined":
        return row.confidence * min(row.sample_size, MINED_CAP)
    if row.source == "simulated":
        return row.confidence * min(row.sample_size or SIM_CAP, SIM_CAP) * SIM_TRUST
    if row.source == "scraped":
        return row.confidence * K_SCRAPED
    return row.confidence * K_CURATED  # curated (default)


def resolve(rows: list[EdgeRow]) -> ResolvedEdge | None:
    if not rows:
        return None

    total = 0.0
    weighted_value = 0.0
    contribution: dict[str, float] = {}
    for r in rows:
        w = edge_weight(r)
        if w <= 0:
            continue
        total += w
        weighted_value += r.value * w
        contribution[r.source] = contribution.get(r.source, 0.0) + w

    head = rows[0]
    if total <= 0:
        # No weighted evidence (e.g. only mined rows with sample_size 0): plain mean, tiny confidence.
        mean = sum(r.value for r in rows) / len(rows)
        return ResolvedEdge(
            head.source_key, head.target_key, head.relation,
            round(mean, 3), 0.1, sorted({r.source for r in rows}),
        )

    sources = [s for s, _ in sorted(contribution.items(), key=lambda kv: -kv[1])]
    return ResolvedEdge(
        head.source_key, head.target_key, head.relation,
        value=round(weighted_value / total, 3),
        confidence=round(total / (total + K0), 3),
        sources=sources,
    )
