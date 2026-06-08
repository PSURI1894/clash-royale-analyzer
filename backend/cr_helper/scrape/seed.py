"""Seed the scraped source: card meta (dataset=scraped) + scraped counter edges.

    python -m cr_helper.scrape
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..models import CardMetaStat, MatchupEdge
from .reconcile import reconcile
from .sources import FixtureScrapeSource, ScrapeSource

SCRAPE_CONFIDENCE = 0.5  # low — a cross-check, not ground truth


def seed_scraped(session: Session, meta: dict) -> tuple[int, int]:
    cards = meta.get("cards", [])
    counters = meta.get("counters", [])

    for c in cards:
        row = session.scalar(
            select(CardMetaStat).where(
                CardMetaStat.card_key == c["key"], CardMetaStat.dataset == "scraped"
            )
        )
        if row is None:
            row = CardMetaStat(card_key=c["key"], dataset="scraped")
            session.add(row)
        row.win_rate = round(float(c["win_rate"]), 3)
        row.usage = round(float(c.get("usage", 0.0)), 3)
        row.games = int(c.get("games", 0))
        row.wins = 0

    session.execute(delete(MatchupEdge).where(MatchupEdge.source == "scraped"))
    for e in counters:
        session.add(MatchupEdge(
            source_key=e["a"], target_key=e["b"], relation="counters", target_kind="card",
            value=round(float(e["win_rate"]), 3), source="scraped",
            confidence=SCRAPE_CONFIDENCE, sample_size=1, note="scrape:fixture",
        ))
    session.commit()
    return len(cards), len(counters)


def run(source: ScrapeSource | None = None) -> dict:
    source = source or FixtureScrapeSource()
    meta = source.fetch_meta()
    init_db()
    with SessionLocal() as session:
        n_cards, n_counters = seed_scraped(session, meta)
        report = reconcile(session, meta.get("cards", []))
    return {"cards": n_cards, "counters": n_counters, "reconcile": report, "source": meta.get("source", "?")}


def main() -> None:
    result = run()
    r = result["reconcile"]
    print(f"Scraped {result['cards']} card metas + {result['counters']} counter edges (source={result['source']}).")
    print(f"Reconcile vs mined: {r['compared']} cards overlap, mean|delta|={r['mean_abs_delta']}, agreement={r['agreement']}.")
    worst = r["rows"][:3]
    for row in worst:
        print(f"  {row['key']}: scraped {row['scraped']} vs mined {row['mined']} (delta {row['delta']})")


if __name__ == "__main__":
    main()
