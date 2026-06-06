"""Battle-engine endpoints: 1v1 duels and push simulations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_session
from ..engine.service import EngineError, simulate_duel, simulate_push
from ..schemas import (
    DuelOut,
    DuelRequest,
    SimEventOut,
    SimRequest,
    SimResultOut,
    SimUnitOut,
    TowerOut,
)

router = APIRouter(tags=["engine"])


@router.post("/simulate/duel", response_model=DuelOut)
def simulate_duel_ep(req: DuelRequest, session: Session = Depends(get_session)) -> DuelOut:
    try:
        result, a_name, b_name = simulate_duel(session, req.a, req.b)
    except EngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result.winner == "a":
        winner, pct = a_name, int(result.a_hp_pct * 100)
        summary = f"{a_name} wins with {pct}% HP after {result.duration}s."
    elif result.winner == "b":
        winner, pct = b_name, int(result.b_hp_pct * 100)
        summary = f"{b_name} wins with {pct}% HP after {result.duration}s."
    else:
        winner, summary = None, "Neither can damage the other (mismatched air/ground)."
    return DuelOut(
        a=a_name, b=b_name, winner=winner,
        a_hp_pct=result.a_hp_pct, b_hp_pct=result.b_hp_pct,
        duration=result.duration, summary=summary,
    )


@router.post("/simulate", response_model=SimResultOut)
def simulate_push_ep(req: SimRequest, session: Session = Depends(get_session)) -> SimResultOut:
    if not req.attacker or not req.defender:
        raise HTTPException(status_code=422, detail="attacker and defender card lists are required")
    result, warnings = simulate_push(session, req.attacker, req.defender, lane=req.lane)
    return SimResultOut(
        winner=result.winner, duration=result.duration, summary=result.summary,
        attacker_survivors=result.attacker_survivors, defender_survivors=result.defender_survivors,
        defender_tower_damage=result.defender_tower_damage,
        towers=[TowerOut(**t) for t in result.towers],
        units=[SimUnitOut(**u) for u in result.units],
        events=[SimEventOut(t=e.t, text=e.text) for e in result.events],
        warnings=warnings,
    )
