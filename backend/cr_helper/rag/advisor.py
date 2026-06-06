"""Advisor orchestrator: Context Fusion -> client -> grounding guardrail."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..schemas import AdviceReport, GroundingOut
from .clients import AdvisorClient, get_client
from .fusion import ContextFusion
from .guardrail import check_grounding
from .retrieve import Retriever


class Advisor:
    def __init__(
        self,
        session: Session,
        client: AdvisorClient | None = None,
        retriever: Retriever | None = None,
    ):
        self.fusion = ContextFusion(session, retriever)
        self.client = client or get_client()

    def advise(self, deck_keys, opponent=None, opponent_cards=None) -> AdviceReport:
        pack = self.fusion.build(deck_keys, opponent=opponent, opponent_cards=opponent_cards)
        report = self.client.generate(pack)
        grounding = check_grounding(report, pack.allowed_numbers, self.client.engine)
        report.grounding = GroundingOut(
            ok=grounding.ok, engine=grounding.engine, unverified_numbers=grounding.unverified_numbers
        )
        return report
