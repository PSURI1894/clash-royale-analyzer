"""Reconcile scraped card meta against our mined meta (cross-source validation)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CardMetaStat


def reconcile(session: Session, scraped_cards: list[dict], mined_dataset: str = "synthetic") -> dict:
    mined = {
        m.card_key: m.win_rate
        for m in session.scalars(select(CardMetaStat).where(CardMetaStat.dataset == mined_dataset))
    }
    rows: list[dict] = []
    deltas: list[float] = []
    for c in scraped_cards:
        mw = mined.get(c["key"])
        if mw is None:
            continue
        delta = round(c["win_rate"] - mw, 3)
        deltas.append(abs(delta))
        rows.append({"key": c["key"], "scraped": c["win_rate"], "mined": mw, "delta": delta})

    mad = round(sum(deltas) / len(deltas), 3) if deltas else None
    if mad is None:
        agreement = "no overlap"
    elif mad < 0.05:
        agreement = "strong"
    elif mad < 0.1:
        agreement = "moderate"
    else:
        agreement = "weak"
    rows.sort(key=lambda r: -abs(r["delta"]))
    return {"compared": len(rows), "mean_abs_delta": mad, "agreement": agreement, "rows": rows}
