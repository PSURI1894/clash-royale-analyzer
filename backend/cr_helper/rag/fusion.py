"""Context Fusion — merge hard facts (analyzer + graph + mining) with retrieved notes."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analyzer.service import analyze_deck
from ..config import settings
from ..graph.repo import SqlGraphRepo
from ..graph.service import GraphService
from ..models import Card, CardMetaStat
from .guardrail import collect_numbers
from .retrieve import Retriever


@dataclass
class RetrievedChunk:
    id: str
    title: str
    text: str
    score: float


@dataclass
class EvidencePack:
    deck_keys: list[str]
    deck_archetype: str
    opponent: str
    verdict: str
    matchup_score: int
    win_conditions: list[str]
    facts: list[str]
    threats: list[dict]
    danger: list[str]
    anti_air: list[dict]
    weak_against: list[str]
    meta: list[dict]
    chunks: list[RetrievedChunk]
    allowed_numbers: set[str]
    names: dict[str, str]


class ContextFusion:
    def __init__(self, session: Session, retriever: Retriever | None = None):
        self.session = session
        self.retriever = retriever or Retriever(session)

    def build(self, deck_keys, opponent=None, opponent_cards=None) -> EvidencePack:
        report = analyze_deck(self.session, deck_keys)  # validates + analyzes + weak_against
        matchup = GraphService(SqlGraphRepo(self.session)).matchup(
            deck_keys, opponent=opponent, opponent_cards=opponent_cards
        )

        cards = {c.key: c for c in self.session.scalars(select(Card).where(Card.key.in_(deck_keys)))}
        names = {k: (cards[k].name if k in cards else k) for k in deck_keys}

        anti_air = []
        for ac in report.metrics.anti_air_cards:
            stats = cards[ac].stats if ac in cards else None
            dps = round(stats.dps, 1) if stats and stats.dps else None
            anti_air.append({"key": ac, "name": names.get(ac, ac), "dps": dps})

        meta = [
            {"key": m.card_key, "name": names.get(m.card_key, m.card_key),
             "win_rate": m.win_rate, "usage": m.usage}
            for m in self.session.scalars(
                select(CardMetaStat).where(
                    CardMetaStat.card_key.in_(deck_keys), CardMetaStat.dataset == "synthetic"
                )
            )
        ]

        facts = [
            f"Deck archetype: {report.archetype.primary}.",
            f"Average elixir cost: {report.metrics.avg_elixir}.",
            f"Cheapest 4-card cycle: {report.metrics.cycle_cost} elixir.",
            f"Defensive air DPS {report.metrics.air_dps}, ground DPS {report.metrics.ground_dps}.",
            f"Matchup vs {matchup.opponent}: {matchup.score} out of 100 ({matchup.verdict}).",
        ]
        if anti_air:
            aa = ", ".join(f"{a['name']} (DPS {a['dps']})" for a in anti_air if a["dps"])
            facts.append(f"Anti-air units: {aa or 'none with listed DPS'}.")
        else:
            facts.append("Anti-air units: none — this deck struggles to hit air targets.")
        for t in matchup.threats:
            ans = ", ".join(names.get(a, a) for a in t.answers) or "no in-deck answer"
            facts.append(f"Threat {t.threat}: {int(round(t.coverage * 100))}% coverage (answers: {ans}).")
        if report.weak_against:
            facts.append("No hard answer to: " + ", ".join(report.weak_against) + ".")

        query = self._query(report.archetype.primary, matchup.opponent, report.win_conditions)
        chunks = [
            RetrievedChunk(r.id, r.title, r.text, round(s, 3))
            for r, s in self.retriever.retrieve(query, k=settings.rag_top_k, archetype=matchup.opponent)
        ]

        allowed = collect_numbers(
            facts
            + [c.text for c in chunks]
            + [str(matchup.score)]
            + [f"{m['win_rate']} {m['usage']}" for m in meta]
        )
        return EvidencePack(
            deck_keys=deck_keys, deck_archetype=report.archetype.primary, opponent=matchup.opponent,
            verdict=matchup.verdict, matchup_score=matchup.score,
            win_conditions=report.win_conditions, facts=facts,
            threats=[t.model_dump() for t in matchup.threats], danger=matchup.danger,
            anti_air=anti_air, weak_against=report.weak_against, meta=meta, chunks=chunks,
            allowed_numbers=allowed, names=names,
        )

    @staticmethod
    def _query(archetype: str, opponent: str, win_conditions: list[str]) -> str:
        wc = " ".join(win_conditions) or archetype
        return f"how to defend against {opponent} using a {archetype} deck with {wc}; placement and counters"
