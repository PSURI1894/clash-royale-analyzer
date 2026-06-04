"""Card catalog endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Card
from ..schemas import CardDetail, CardSummary

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=list[CardSummary])
def list_cards(
    type: str | None = Query(None, description="Troop | Building | Spell"),
    rarity: str | None = Query(None),
    max_elixir: int | None = Query(None, ge=0, le=12),
    session: Session = Depends(get_session),
) -> list[Card]:
    stmt = select(Card)
    if type:
        stmt = stmt.where(Card.type == type)
    if rarity:
        stmt = stmt.where(Card.rarity == rarity)
    if max_elixir is not None:
        stmt = stmt.where(Card.elixir <= max_elixir)
    stmt = stmt.order_by(Card.elixir.is_(None), Card.elixir, Card.name)
    return list(session.scalars(stmt).all())


@router.get("/{key}", response_model=CardDetail)
def get_card(key: str, session: Session = Depends(get_session)) -> Card:
    card = session.get(Card, key)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Card '{key}' not found")
    return card
