"""Mining / meta endpoints: pipeline coverage stats and the card meta leaderboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Battle, Card, CardMetaStat, MatchupEdge
from ..schemas import CardMetaOut, MiningStatsOut

router = APIRouter(tags=["mining"])


@router.get("/mining/stats", response_model=MiningStatsOut)
def mining_stats(session: Session = Depends(get_session)) -> MiningStatsOut:
    battles = session.scalar(select(func.count()).select_from(Battle)) or 0
    by_dataset = {
        ds: n
        for ds, n in session.execute(
            select(Battle.dataset, func.count()).group_by(Battle.dataset)
        ).all()
    }
    mined = (
        session.scalar(
            select(func.count()).select_from(MatchupEdge).where(MatchupEdge.source == "mined")
        )
        or 0
    )
    players = session.scalar(select(func.count(func.distinct(Battle.player_tag)))) or 0
    return MiningStatsOut(battles=battles, by_dataset=by_dataset, mined_edges=mined, players=players)


@router.get("/meta/cards", response_model=list[CardMetaOut])
def meta_cards(
    dataset: str = "synthetic",
    sort: str = Query("win_rate", pattern="^(win_rate|usage)$"),
    limit: int = Query(25, ge=1, le=120),
    min_games: int = Query(20, ge=0),
    session: Session = Depends(get_session),
) -> list[CardMetaOut]:
    rows = session.execute(
        select(CardMetaStat, Card.name)
        .join(Card, Card.key == CardMetaStat.card_key)
        .where(CardMetaStat.dataset == dataset, CardMetaStat.games >= min_games)
    ).all()
    items = [
        CardMetaOut(key=m.card_key, name=name, games=m.games, win_rate=m.win_rate, usage=m.usage)
        for m, name in rows
    ]
    items.sort(key=lambda x: x.win_rate if sort == "win_rate" else x.usage, reverse=True)
    return items[:limit]
