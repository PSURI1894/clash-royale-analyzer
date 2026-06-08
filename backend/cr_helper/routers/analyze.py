"""Deck analysis endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..analyzer.service import DeckValidationError, analyze_deck
from ..db import get_session
from ..runtime import analysis_cache
from ..schemas import AnalysisReport, DeckRequest

router = APIRouter(tags=["analyzer"])


@router.post("/analyze", response_model=AnalysisReport)
def analyze(req: DeckRequest, session: Session = Depends(get_session)) -> AnalysisReport:
    key = ",".join(sorted(req.cards))
    cached = analysis_cache.get(key)
    if cached is not None:
        return cached
    try:
        report = analyze_deck(session, req.cards)
    except DeckValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.problems) from exc
    analysis_cache.set(key, report)
    return report
