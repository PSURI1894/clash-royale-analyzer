"""Deck validation + orchestration: keys -> validated cards -> analysis report."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..graph.repo import SqlGraphRepo
from ..graph.service import GraphService
from ..models import Card
from ..schemas import AnalysisReport
from .engine import AnalyzerCard, build_report

DECK_SIZE = 8


class DeckValidationError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


def load_and_validate(session: Session, keys: list[str]) -> list[Card]:
    problems: list[str] = []
    if len(keys) != DECK_SIZE:
        problems.append(f"a deck must have exactly {DECK_SIZE} cards (got {len(keys)})")
    if len(set(keys)) != len(keys):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        problems.append(f"duplicate cards: {', '.join(dupes)}")

    found = {
        c.key: c
        for c in session.scalars(select(Card).where(Card.key.in_(set(keys)))).all()
    }
    for k in keys:
        if k not in found:
            problems.append(f"unknown card: '{k}'")

    if problems:
        raise DeckValidationError(problems)
    return [found[k] for k in keys]


def analyze_deck(session: Session, keys: list[str]) -> AnalysisReport:
    cards = load_and_validate(session, keys)
    report = build_report([AnalyzerCard.from_orm(c) for c in cards])
    # Enrich with graph-driven matchup awareness (meta threats with no in-deck answer).
    report.weak_against = GraphService(SqlGraphRepo(session)).weak_against(keys)
    return report
