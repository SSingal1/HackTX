from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nextmove.api.dependencies import get_guardian_market_service
from nextmove.data.guardian import ResilientGuardianProfileRepository
from nextmove.decision.models import Evidence, EvidenceStatus
from nextmove.integrations.serpapi import SearchEvidenceResult
from nextmove.main import create_app
from nextmove.services.guardian_market import GuardianMarketEvidenceService


class CountingMarketSearch:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, int]] = []

    def search_market(self, query: str, *, location: str | None = None, limit: int = 5):
        self.calls.append((query, location, limit))
        is_fuel_query = "gasprices.aaa.com" in query
        evidence = Evidence(
            evidence_id=f"evidence-{len(self.calls)}",
            title="AAA fuel research" if is_fuel_query else "Toyota public reference",
            url=(
                "https://gasprices.aaa.com/?state=TX"
                if is_fuel_query
                else "https://www.toyota.com/owners/"
            ),
            retrieved_at="2026-10-24T00:00:00+00:00",
            status=EvidenceStatus.NEEDS_VERIFICATION,
            fact=(
                "AAA reports regular gasoline at $3.42 per gallon."
                if is_fuel_query
                else "Toyota owner reference."
            ),
        )
        return SearchEvidenceResult((evidence,), query)


def service(tmp_path: Path, search: CountingMarketSearch) -> GuardianMarketEvidenceService:
    return GuardianMarketEvidenceService(
        ResilientGuardianProfileRepository(None), search, str(tmp_path / "guardian.sqlite3"), 21600
    )


def test_cache_only_market_evidence_never_calls_serpapi(tmp_path):
    search = CountingMarketSearch()
    result = service(tmp_path, search).evidence("alex")
    assert search.calls == []
    assert result["source"] == "cache_only"
    assert result["categories"] == []


def test_explicit_refresh_runs_five_bounded_queries_then_uses_cache(tmp_path):
    search = CountingMarketSearch()
    market = service(tmp_path, search)
    refreshed = market.evidence("alex", refresh=True)
    cached = market.evidence("alex")
    assert len(search.calls) == 5
    queries = [query for query, _location, _limit in search.calls]
    assert any("site:gasprices.aaa.com" in query for query in queries)
    assert all(limit == 3 for _query, _location, limit in search.calls)
    assert any("Corolla Hybrid LE" in query for query in queries)
    assert any("Camry LE" in query for query in queries)
    assert any("Prius LE" in query for query in queries)
    assert any("site:toyota.com/deals-incentives/texas" in query for query in queries)
    assert any('"APR" financing' in query for query in queries)
    assert refreshed["source"] == "serpapi"
    assert refreshed["categories"][0]["status"] == "needs_verification"
    assert refreshed["categories"][0]["evidence"][0]["url"] == "https://gasprices.aaa.com/?state=TX"
    assert refreshed["fuel_reference"]["price_per_gallon"] == 3.42
    assert cached["cached"] is True
    assert len(search.calls) == 5


def test_unknown_profile_returns_none_without_search(tmp_path):
    search = CountingMarketSearch()
    assert service(tmp_path, search).evidence("missing", refresh=True) is None
    assert search.calls == []


def test_adopted_fuel_reference_is_confirmation_only(tmp_path):
    search = CountingMarketSearch()
    market = service(tmp_path, search)
    refreshed = market.evidence("alex", refresh=True)

    adopted = market.adopt_fuel_reference("alex", refreshed["fuel_reference"]["evidence_id"])

    assert adopted["fuel_price_per_gallon"] == 3.42
    assert adopted["requires_confirmation"] is True
    assert "has not changed" in adopted["notice"]
    assert len(search.calls) == 5


def test_non_aaa_fuel_evidence_cannot_be_adopted(tmp_path):
    search = CountingMarketSearch()
    market = service(tmp_path, search)
    market.evidence("alex", refresh=True)
    with market._connect() as connection:
        row = connection.execute("SELECT body FROM guardian_market_cache").fetchone()
        body = json.loads(row[0])
        body["fuel_reference"] = None
        connection.execute("UPDATE guardian_market_cache SET body=?", (json.dumps(body),))

    with pytest.raises(ValueError, match="not an adoptable"):
        market.adopt_fuel_reference("alex", "evidence-1")


def test_adopt_fuel_endpoint_prepares_a_confirmation_only_input(tmp_path):
    search = CountingMarketSearch()
    market = service(tmp_path, search)
    evidence_id = market.evidence("alex", refresh=True)["fuel_reference"]["evidence_id"]
    app = create_app()
    app.dependency_overrides[get_guardian_market_service] = lambda: market
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/guardian/market-evidence/adopt-fuel",
            json={"profile": "alex", "evidence_id": evidence_id},
        )
        invalid = client.post(
            "/api/v1/guardian/market-evidence/adopt-fuel",
            json={"profile": "alex", "evidence_id": "not-a-fuel-source"},
        )
    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True
    assert invalid.status_code == 422
    app.dependency_overrides.clear()
