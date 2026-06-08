"""Saved decks — CRUD keyed by an opaque client token (no passwords/PII)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analyzer.service import DeckValidationError, load_and_validate
from ..db import get_session
from ..models import SavedDeck
from ..schemas import SavedDeckIn, SavedDeckOut

router = APIRouter(tags=["decks"])


def _token(value: str | None) -> str:
    if not value or len(value) < 6:
        raise HTTPException(status_code=401, detail="Provide an X-User-Token header (>= 6 chars).")
    return value


@router.get("/decks", response_model=list[SavedDeckOut])
def list_decks(
    x_user_token: str | None = Header(default=None), session: Session = Depends(get_session)
) -> list[SavedDeckOut]:
    token = _token(x_user_token)
    rows = session.scalars(
        select(SavedDeck).where(SavedDeck.user_token == token).order_by(SavedDeck.created_at.desc())
    ).all()
    return [SavedDeckOut(id=d.id, name=d.name, cards=d.cards) for d in rows]


@router.post("/decks", response_model=SavedDeckOut)
def save_deck(
    body: SavedDeckIn,
    x_user_token: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> SavedDeckOut:
    token = _token(x_user_token)
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="deck name is required")
    try:
        load_and_validate(session, body.cards)
    except DeckValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.problems) from exc

    deck = session.scalar(
        select(SavedDeck).where(SavedDeck.user_token == token, SavedDeck.name == body.name)
    )
    if deck:
        deck.cards = body.cards
    else:
        deck = SavedDeck(user_token=token, name=body.name, cards=body.cards)
        session.add(deck)
    session.commit()
    return SavedDeckOut(id=deck.id, name=deck.name, cards=deck.cards)


@router.delete("/decks/{deck_id}")
def delete_deck(
    deck_id: int,
    x_user_token: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> dict:
    token = _token(x_user_token)
    deck = session.get(SavedDeck, deck_id)
    if not deck or deck.user_token != token:
        raise HTTPException(status_code=404, detail="deck not found")
    session.delete(deck)
    session.commit()
    return {"deleted": deck_id}
