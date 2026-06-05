"""Graph-driven analysis: card relations, deck-vs-opponent matchups, weak spots."""
from __future__ import annotations

from ..analyzer.card_roles import FLEX_WIN_CONDITIONS, WIN_CONDITIONS
from ..schemas import (
    CardRelationsOut,
    MatchupReport,
    ResolvedEdgeOut,
    SourceComponentOut,
    ThreatCoverageOut,
)
from .curated import ARCHETYPE_THREATS, META_THREATS
from .repo import GraphRepo
from .resolver import ResolvedEdge


def _to_out(e: ResolvedEdge) -> ResolvedEdgeOut:
    return ResolvedEdgeOut(
        source_key=e.source_key, target_key=e.target_key, relation=e.relation,
        value=e.value, confidence=e.confidence, sources=e.sources,
        components=[
            SourceComponentOut(source=c.source, value=c.value, weight=c.weight, sample_size=c.sample_size)
            for c in e.components
        ],
    )


class GraphService:
    def __init__(self, repo: GraphRepo):
        self.repo = repo

    def card_relations(self, key: str) -> CardRelationsOut:
        return CardRelationsOut(
            key=key,
            counters=[_to_out(e) for e in self.repo.counters_by(key)],
            countered_by=[_to_out(e) for e in self.repo.answers_to(key)],
            synergies=[_to_out(e) for e in self.repo.synergies_for(key)],
        )

    def _threat_profile(
        self, opponent: str | None, opponent_cards: list[str] | None
    ) -> tuple[str, list[tuple[str, float]]]:
        if opponent_cards:
            wins = [k for k in opponent_cards if k in WIN_CONDITIONS]
            if not wins:
                wins = [k for k in opponent_cards if k in FLEX_WIN_CONDITIONS]
            threats = [(k, 1.0) for k in wins] or [(k, 0.5) for k in opponent_cards]
            return "custom deck", threats
        label = opponent or "Lavaloon"
        return label, ARCHETYPE_THREATS.get(label, [])

    def matchup(
        self,
        deck_keys: list[str],
        opponent: str | None = None,
        opponent_cards: list[str] | None = None,
    ) -> MatchupReport:
        deck = set(deck_keys)
        label, threats = self._threat_profile(opponent, opponent_cards)

        coverages: list[ThreatCoverageOut] = []
        danger: list[str] = []
        total_sev = 0.0
        weighted = 0.0
        for threat, severity in threats:
            answers = [e for e in self.repo.answers_to(threat) if e.source_key in deck]
            best = answers[0] if answers else None  # already sorted by value desc
            coverage = best.value if best else 0.0
            coverages.append(ThreatCoverageOut(
                threat=threat, severity=severity, coverage=round(coverage, 3),
                best_answer=best.source_key if best else None,
                answers=[e.source_key for e in answers],
            ))
            total_sev += severity
            weighted += coverage * severity
            if coverage <= 0.0:
                danger.append(threat)

        score = int(round((weighted / total_sev) * 100)) if total_sev else 0
        return MatchupReport(
            opponent=label, score=score, verdict=_verdict(score, danger),
            threats=coverages, danger=danger,
        )

    def weak_against(self, deck_keys: list[str], threshold: float = 0.55) -> list[str]:
        """Meta threats with no in-deck answer (resolved counter value >= threshold).

        The threshold ensures a merely-neutral (~0.5) edge — e.g. a noisy mined
        pairing — does not count as a real answer and mask a genuine weakness.
        """
        deck = set(deck_keys)
        weak: list[str] = []
        for threat in META_THREATS:
            if threat in deck:
                continue
            answers = [
                e for e in self.repo.answers_to(threat)
                if e.source_key in deck and e.value >= threshold
            ]
            if not answers:
                weak.append(threat)
        return weak


def _verdict(score: int, danger: list[str]) -> str:
    if score >= 75:
        base = "Favorable"
    elif score >= 55:
        base = "Even"
    elif score >= 35:
        base = "Tricky"
    else:
        base = "Unfavorable"
    if danger:
        return f"{base} — no answer to {', '.join(danger)}"
    return base
