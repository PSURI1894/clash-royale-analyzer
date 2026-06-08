"""Operational endpoints: liveness and runtime stats."""
from __future__ import annotations

from fastapi import APIRouter

from ..runtime import analysis_cache, metrics

router = APIRouter(tags=["system"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/stats")
def stats() -> dict:
    return {"metrics": metrics.snapshot(), "analysis_cache": analysis_cache.stats()}
