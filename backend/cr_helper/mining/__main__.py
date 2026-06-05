"""CLI: python -m cr_helper.mining [--source synthetic|api] [--limit N] ...

Examples:
    python -m cr_helper.mining --source synthetic --limit 5000
    python -m cr_helper.mining --source api --seed-tags "#2PP0" "#9YJUPU9LV" --limit 3000
"""
from __future__ import annotations

import argparse

from .pipeline import run_mining


def main() -> None:
    p = argparse.ArgumentParser(prog="cr_helper.mining", description="Battle-log mining ETL")
    p.add_argument("--source", choices=["synthetic", "api"], default="synthetic")
    p.add_argument("--limit", type=int, default=4000, help="max battles to ingest this run")
    p.add_argument("--seed", type=int, default=7, help="RNG seed for the synthetic source")
    p.add_argument("--seed-tags", nargs="*", default=None, help="starting player tags (api source)")
    args = p.parse_args()

    dataset = "synthetic" if args.source == "synthetic" else "api"
    summary = run_mining(
        dataset=dataset, limit=args.limit, seed=args.seed, seed_tags=args.seed_tags
    )
    print("Mining summary:", summary)


if __name__ == "__main__":
    main()
