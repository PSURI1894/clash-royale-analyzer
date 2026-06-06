"""Grounding guardrail — the anti-hallucination spine.

Every statistic in the advisor's output must trace back to the evidence. We
collect the numbers present in the evidence, then scan the report; any non-trivial
number (decimal, percentage, or >= 10) not found in the evidence is flagged. Small
integers (list steps, tile counts) are treated as structural and ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _norm(token: str) -> str:
    f = float(token)
    return str(int(f)) if f == int(f) else str(round(f, 3))


def collect_numbers(texts: list[str]) -> set[str]:
    out: set[str] = set()
    for t in texts:
        for m in _NUM_RE.findall(str(t)):
            out.add(_norm(m))
    return out


def find_unverified(text: str, allowed: set[str]) -> list[str]:
    bad: list[str] = []
    for m in _NUM_RE.findall(text):
        if _norm(m) in allowed:
            continue
        # benign structural integers (steps, tile counts) — ignore values < 10 with no decimal
        if "." not in m and float(m) < 10:
            continue
        bad.append(m)
    return sorted(set(bad))


@dataclass
class GroundingResult:
    ok: bool
    engine: str
    unverified_numbers: list[str]


def report_text(report) -> str:
    parts: list[str] = [report.verdict, *report.key_facts, *report.game_plan, *report.defensive_routine]
    parts += [p.note for p in report.placements]
    return "  ".join(parts)


def check_grounding(report, allowed_numbers: set[str], engine: str) -> GroundingResult:
    bad = find_unverified(report_text(report), allowed_numbers)
    return GroundingResult(ok=not bad, engine=engine, unverified_numbers=bad)
