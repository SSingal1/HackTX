from __future__ import annotations

from typing import Any

from nextmove.data.guardian import GuardianProfileRepository
from nextmove.integrations.guardian_chat import GuardianChatResult, GuardianGeminiClient
from nextmove.services.guardian_market import GuardianMarketEvidenceService
from nextmove.services.guardian_providers import GuardianProviderService


class GuardianChatService:
    def __init__(
        self,
        repository: GuardianProfileRepository,
        provider_service: GuardianProviderService,
        gemini: GuardianGeminiClient,
        market_service: GuardianMarketEvidenceService | None = None,
    ) -> None:
        self.repository = repository
        self.provider_service = provider_service
        self.gemini = gemini
        self.market_service = market_service

    def respond(
        self,
        *,
        profile_id: str,
        scenario: dict[str, Any],
        comparison: dict[str, Any],
        view: str,
        message: str,
        history: list[dict[str, str]],
        user_context: dict[str, Any] | None = None,
    ) -> GuardianChatResult | None:
        profile = self.repository.get_guardian_profile(profile_id)
        if profile is None:
            return None
        cached = self.provider_service.get_cached(profile_id)
        providers = cached.get("providers", []) if cached else []
        market = (
            self.market_service.evidence(profile_id, refresh=False)
            if self.market_service is not None
            else None
        )
        context = {
            "authoritative": {
                "profile": profile,
                "scenario": scenario,
                "comparison": {
                    "calculation": comparison["calculation"],
                    "recommendation": comparison["recommendation"],
                    "decision": comparison["decision"],
                    "banking": comparison.get("banking", {}),
                    "finance_plan": comparison.get("finance_plan", {}),
                    "selected_upgrade": comparison.get("selected_upgrade", {}),
                },
                "providers": providers,
                "provider_warning": cached.get("warning") if cached else "No cached evidence.",
                "user_reported_context": user_context or {},
            },
            "scenario_bounds": {
                "miles": {"type": "number", "min": 6000, "max": 30000},
                "repair": {"type": "number", "min": 0, "max": 4500},
                "reserve": {"type": "number", "min": 500, "max": 6000},
                "discount": {"type": "boolean"},
            },
            "untrusted": {
                "view": view,
                "message": message,
                "history": history,
                "provider_content": providers,
                # Public-web results are intentionally untrusted and cache-only here. Chat never
                # requests a refresh, so a message cannot spend a SerpApi search.
                "market_content": _bounded_market_content(market),
            },
        }
        return self.gemini.answer(context)


def _bounded_market_content(market: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Keep the model context small and expose public evidence as references, never facts."""
    if not market:
        return []
    categories: list[dict[str, Any]] = []
    for category in market.get("categories", [])[:5]:
        evidence = []
        for item in category.get("evidence", [])[:1]:
            evidence.append(
                {
                    "evidence_id": str(item.get("evidence_id", ""))[:80],
                    "title": str(item.get("title", ""))[:220],
                    "url": str(item.get("url", ""))[:500],
                    "fact": str(item.get("fact", ""))[:300],
                    "status": str(item.get("status", "needs_verification"))[:60],
                    "retrieved_at": str(item.get("retrieved_at", ""))[:80],
                }
            )
        categories.append(
            {
                "label": str(category.get("label", "Public research"))[:100],
                "evidence": evidence,
                "status": "needs_verification",
            }
        )
    return categories
