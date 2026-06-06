"""RAG advisor endpoint: grounded tactical coaching for a deck + matchup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..analyzer.service import DeckValidationError
from ..db import get_session
from ..graph.curated import ARCHETYPE_THREATS
from ..rag.advisor import Advisor
from ..schemas import AdviceReport, AdviceRequest

router = APIRouter(tags=["advisor"])


@router.post("/advise", response_model=AdviceReport)
def advise(req: AdviceRequest, session: Session = Depends(get_session)) -> AdviceReport:
    if not req.opponent_cards and req.opponent and req.opponent not in ARCHETYPE_THREATS:
        raise HTTPException(
            status_code=422, detail=f"unknown archetype '{req.opponent}'. See GET /archetypes."
        )
    try:
        return Advisor(session).advise(
            req.cards, opponent=req.opponent, opponent_cards=req.opponent_cards
        )
    except DeckValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.problems) from exc
