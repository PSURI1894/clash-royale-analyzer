"""Knowledge-graph endpoints: card relations & deck matchups."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..analyzer.service import DeckValidationError, load_and_validate
from ..db import get_session
from ..graph.curated import ARCHETYPE_THREATS
from ..graph.repo import SqlGraphRepo
from ..graph.service import GraphService
from ..models import Card
from ..schemas import CardRelationsOut, MatchupReport, MatchupRequest

router = APIRouter(tags=["graph"])


def _service(session: Session) -> GraphService:
    return GraphService(SqlGraphRepo(session))


@router.get("/archetypes", response_model=list[str])
def list_archetypes() -> list[str]:
    return sorted(ARCHETYPE_THREATS)


@router.get("/cards/{key}/relations", response_model=CardRelationsOut)
def card_relations(key: str, session: Session = Depends(get_session)) -> CardRelationsOut:
    if session.get(Card, key) is None:
        raise HTTPException(status_code=404, detail=f"Card '{key}' not found")
    return _service(session).card_relations(key)


@router.post("/matchup", response_model=MatchupReport)
def matchup(req: MatchupRequest, session: Session = Depends(get_session)) -> MatchupReport:
    try:
        load_and_validate(session, req.cards)
    except DeckValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.problems) from exc

    if not req.opponent_cards and req.opponent and req.opponent not in ARCHETYPE_THREATS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown archetype '{req.opponent}'. See GET /archetypes.",
        )
    return _service(session).matchup(req.cards, opponent=req.opponent, opponent_cards=req.opponent_cards)
