"""Advisor clients: offline deterministic Stub and the real Claude integration."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import settings
from ..schemas import AdviceReport, PlacementOut, RetrievedChunkOut
from .fusion import EvidencePack


def _sources(pack: EvidencePack) -> list[RetrievedChunkOut]:
    return [RetrievedChunkOut(id=c.id, title=c.title, score=c.score) for c in pack.chunks]


class AdvisorClient(ABC):
    engine = "abstract"

    @abstractmethod
    def generate(self, pack: EvidencePack) -> AdviceReport: ...


class StubClient(AdvisorClient):
    """Deterministic, fully-grounded report composed from the evidence pack.

    Emits only facts/numbers present in the evidence, so it passes the grounding
    guardrail by construction — and exercises the whole pipeline with no API key.
    """

    engine = "stub"

    def generate(self, pack: EvidencePack) -> AdviceReport:
        return AdviceReport(
            deck_archetype=pack.deck_archetype,
            opponent=pack.opponent,
            verdict=f"{pack.verdict} (matchup {pack.matchup_score}/100).",
            key_facts=pack.facts[:8],
            game_plan=self._plan(pack),
            defensive_routine=self._defense(pack),
            placements=self._placements(pack),
            citations=[c.id for c in pack.chunks],
            sources=_sources(pack),
        )

    def _plan(self, pack: EvidencePack) -> list[str]:
        plan: list[str] = []
        if pack.matchup_score >= 55:
            plan.append(f"The matchup reads {pack.matchup_score} out of 100 — take the tempo and apply pressure.")
        else:
            plan.append(f"The matchup reads {pack.matchup_score} out of 100 — defend efficiently and win on chip; do not overcommit.")
        if pack.chunks:
            plan.append(pack.chunks[0].text)
        if pack.danger:
            plan.append("You have no hard answer to " + ", ".join(pack.danger) + " — kite it and trade down its support.")
        return plan

    def _defense(self, pack: EvidencePack) -> list[str]:
        steps: list[str] = []
        for t in pack.threats:
            if t["answers"]:
                who = ", ".join(pack.names.get(a, a) for a in t["answers"])
                steps.append(f"Handle {t['threat']} with {who}.")
            else:
                steps.append(f"You lack a clean answer to {t['threat']} — distract it and chip its support.")
        for c in pack.chunks[1:3]:
            steps.append(f"{c.title}: {c.text}")
        return steps

    def _placements(self, pack: EvidencePack) -> list[PlacementOut]:
        out = [
            PlacementOut(card=a["name"], note=f"Keep {a['name']} alive to cover the air — deploy it away from spell value.")
            for a in pack.anti_air
        ]
        for wc in pack.win_conditions:
            out.append(PlacementOut(card=pack.names.get(wc, wc), note=f"Commit {pack.names.get(wc, wc)} only once a defence is set, ideally on a counter-push."))
        return out or [PlacementOut(
            card=pack.names.get(pack.deck_keys[0], pack.deck_keys[0]),
            note="Lead with a defensive answer before committing offence.",
        )]


class ClaudeClient(AdvisorClient):
    """Real advisor via Claude — prompt-cached system prompt + tool-use structured output."""

    engine = "claude"

    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
        self.model = model or settings.anthropic_model

    def generate(self, pack: EvidencePack) -> AdviceReport:
        from .prompts import SYSTEM, TOOL, user_message

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=[TOOL],
            tool_choice={"type": "tool", "name": "emit_tactical_report"},
            messages=[{"role": "user", "content": user_message(pack)}],
        )
        data = next(b.input for b in resp.content if getattr(b, "type", None) == "tool_use")
        return AdviceReport(
            deck_archetype=pack.deck_archetype,
            opponent=pack.opponent,
            verdict=data["verdict"],
            key_facts=data["key_facts"],
            game_plan=data["game_plan"],
            defensive_routine=data["defensive_routine"],
            placements=[PlacementOut(**p) for p in data["placements"]],
            citations=data.get("citations", []),
            sources=_sources(pack),
        )


def get_client() -> AdvisorClient:
    backend = settings.advisor_backend
    if backend == "claude" or (backend == "auto" and settings.anthropic_api_key):
        return ClaudeClient()
    return StubClient()
