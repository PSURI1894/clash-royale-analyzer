"""Run the full ingest pipeline:  python -m cr_helper.ingest [--force-refresh]"""
from __future__ import annotations

import argparse

from ..config import settings
from ..db import SessionLocal, init_db
from .load import load_records
from .normalize import normalize
from .sources import download_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest cr-api-data into the database.")
    parser.add_argument(
        "--force-refresh", action="store_true", help="re-download source JSON files"
    )
    args = parser.parse_args()

    print("Downloading cr-api-data sources...")
    sources = download_sources(force_refresh=args.force_refresh)
    for name, rows in sources.items():
        print(f"  {name:<26} {len(rows):>4} rows")

    print("Normalizing...")
    records = normalize(sources)
    with_stats = sum(1 for r in records if r.stats)
    with_dps = sum(1 for r in records if r.stats and r.stats.dps)
    print(f"  {len(records)} cards  |  {with_stats} with stats  |  {with_dps} with DPS")

    print("Loading into the database...")
    init_db()
    with SessionLocal() as session:
        count = load_records(session, records)
    print(f"Done. Upserted {count} cards -> {settings.database_url}")


if __name__ == "__main__":
    main()
