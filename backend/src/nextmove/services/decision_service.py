from dataclasses import replace
from typing import Protocol

from nextmove.decision.engine import DecisionEngine
from nextmove.decision.models import DecisionRequest, DecisionResult, Evidence
from nextmove.integrations.gemini import GeminiClient


class EvidenceProvider(Protocol):
    def search_market(self, query: str, *, location: str | None = None, limit: int = 5): ...


class DecisionStore(Protocol):
    def save_decision(self, result: DecisionResult, evidence: tuple[Evidence, ...]) -> None: ...


class DecisionService:
    def __init__(
        self,
        engine: DecisionEngine,
        evidence: EvidenceProvider,
        explainer: GeminiClient,
        store: DecisionStore | None = None,
    ):
        self.engine, self.evidence, self.explainer, self.store = engine, evidence, explainer, store

    def decide(
        self, request: DecisionRequest, *, market_query: str, location: str | None = None
    ) -> DecisionResult:
        search, result = (
            self.evidence.search_market(market_query, location=location),
            self.engine.evaluate(request),
        )
        explanation = self.explainer.explain(result, search.evidence)
        enriched = replace(
            result,
            unknowns=result.unknowns + ((search.warning,) if search.warning else ()),
            explanation=explanation.summary,
        )
        if self.store:
            self.store.save_decision(enriched, search.evidence)
        return enriched
