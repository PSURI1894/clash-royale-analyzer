"""System prompt, evidence formatter, and tool schema for the Claude advisor."""
from __future__ import annotations

SYSTEM = (
    "You are an elite Clash Royale coach. You are given an EVIDENCE block containing "
    "hard, pre-computed facts (deck stats, matchup numbers, anti-air DPS, mined win-rates) "
    "and retrieved strategy NOTES, each with an id.\n\n"
    "Strict rules:\n"
    "1. Use ONLY numbers that appear in the EVIDENCE. Never invent or estimate percentages, "
    "DPS, elixir costs, win-rates, or tile counts that are not present in the evidence.\n"
    "2. Ground every tactical recommendation in the NOTES, and cite the note ids you used.\n"
    "3. Be concrete, specific, and concise. Respond ONLY by calling the emit_tactical_report tool."
)

TOOL = {
    "name": "emit_tactical_report",
    "description": "Return the structured tactical coaching report for the player's deck and matchup.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "description": "One-line matchup verdict."},
            "key_facts": {
                "type": "array", "items": {"type": "string"},
                "description": "The most important grounded facts (numbers must come from EVIDENCE).",
            },
            "game_plan": {"type": "array", "items": {"type": "string"}},
            "defensive_routine": {
                "type": "array", "items": {"type": "string"},
                "description": "Ordered defensive steps for the matchup.",
            },
            "placements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"card": {"type": "string"}, "note": {"type": "string"}},
                    "required": ["card", "note"],
                },
            },
            "citations": {
                "type": "array", "items": {"type": "string"},
                "description": "Ids of the NOTES you used.",
            },
        },
        "required": ["verdict", "key_facts", "game_plan", "defensive_routine", "placements", "citations"],
    },
}


def user_message(pack) -> str:
    lines = ["# EVIDENCE", "", "## Hard facts"]
    lines += [f"- {f}" for f in pack.facts]
    if pack.meta:
        lines += ["", "## Mined card win-rates"]
        lines += [f"- {m['name']}: win rate {m['win_rate']}, usage {m['usage']}" for m in pack.meta]
    lines += ["", "## Retrieved strategy notes"]
    lines += [f"- [{c.id}] {c.title}: {c.text}" for c in pack.chunks]
    lines += [
        "",
        "# TASK",
        f"Coach this {pack.deck_archetype} deck against {pack.opponent}. Produce a tactical "
        "report grounded only in the evidence above, citing note ids.",
    ]
    return "\n".join(lines)
