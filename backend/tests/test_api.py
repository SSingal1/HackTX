from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient

from nextmove.api.dependencies import get_decision_service, get_profile_repository
from nextmove.decision.engine import DecisionEngine
from nextmove.integrations.gemini import GeminiClient
from nextmove.integrations.serpapi import SerpApiClient
from nextmove.main import app
from nextmove.services.decision_service import DecisionService


class FakeProfileRepository:
    def list_profile_ids(self) -> list[str]:
        return ["demo-profile"]

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        if profile_id != "demo-profile":
            return None
        return {
            "profile_id": profile_id,
            "region": "Austin, TX",
            "budget_monthly": Decimal("650"),
            "simulated": True,
        }


def deterministic_service() -> DecisionService:
    return DecisionService(
        engine=DecisionEngine(),
        evidence=SerpApiClient(None),
        explainer=GeminiClient(None, "gemini-3.8-flash"),
    )


def setup_module() -> None:
    app.dependency_overrides[get_profile_repository] = FakeProfileRepository
    app.dependency_overrides[get_decision_service] = deterministic_service


def teardown_module() -> None:
    app.dependency_overrides.clear()


def test_list_and_get_profiles() -> None:
    with TestClient(app) as client:
        listed = client.get("/api/v1/profiles")
        found = client.get("/api/v1/profiles/demo-profile")
        missing = client.get("/api/v1/profiles/missing")
    assert listed.json() == {"profile_ids": ["demo-profile"]}
    assert found.json()["simulated"] is True
    assert found.json()["budget_monthly"] == "650"
    assert missing.status_code == 404


def test_evaluate_decision_without_external_keys() -> None:
    payload = {
        "profile_id": "demo-profile",
        "run_id": "demo-run",
        "horizon_months": 12,
        "market_query": "2024 Toyota RAV4 lease offers Austin",
        "max_cash_due": "3000",
        "max_monthly_outflow": "700",
        "options": [
            {
                "option_id": "buyout",
                "label": "Buy the current RAV4",
                "cash_due": "1000",
                "finance": {
                    "principal": "22000",
                    "annual_rate": "0.06",
                    "term_months": 60,
                },
                "estimated_ending_value": "21000",
            },
            {
                "option_id": "new-lease",
                "label": "Lease a new RAV4",
                "cash_due": "2500",
                "monthly_payment": "520",
            },
        ],
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/decisions/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "demo-run"
    assert body["comparison_basis"] == "cash_flow"
    assert len(body["options"]) == 2
    assert "SerpApi is not configured" in body["unknowns"][0]
    assert body["explanation"]
