from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from nextmove.api.dependencies import get_guardian_provider_service
from nextmove.data.guardian import ResilientGuardianProfileRepository
from nextmove.integrations.guardian_providers import (
    GuardianProviderSearchClient,
    ProviderEvidence,
    ProviderSearchResult,
)
from nextmove.main import create_app
from nextmove.services.guardian_providers import GuardianProviderService


class CountingSearch:
    def __init__(self) -> None:
        self.calls = 0
        self.contexts: list[tuple[str, str]] = []

    def search(self, *, query: str, location: str) -> ProviderSearchResult:
        self.calls += 1
        self.contexts.append((query, location))
        provider = ProviderEvidence(
            name="Example Toyota",
            address="100 Example St",
            rating=4.7,
            review_count=125,
            position=1,
            distance=None,
            link="https://example.test/provider",
            retrieved_at=datetime.now(UTC).isoformat(),
            evidence_id="serp_provider_test",
        )
        return ProviderSearchResult((provider,))


def service(tmp_path, search) -> GuardianProviderService:
    return GuardianProviderService(
        ResilientGuardianProfileRepository(None),
        search,
        str(tmp_path / "guardian.sqlite3"),
        ttl_seconds=21600,
    )


def test_cache_hit_avoids_second_serpapi_call(tmp_path):
    search = CountingSearch()
    providers = service(tmp_path, search)
    first = providers.discover("alex", refresh=True)
    second = providers.discover("alex")
    assert search.calls == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert search.contexts == [("Toyota authorized service center", "Austin, TX")]


def test_refresh_performs_another_call(tmp_path):
    search = CountingSearch()
    providers = service(tmp_path, search)
    providers.discover("alex", refresh=True)
    refreshed = providers.discover("alex", refresh=True)
    assert search.calls == 2
    assert refreshed["cached"] is False


def test_non_refresh_lookup_without_cache_never_searches(tmp_path):
    search = CountingSearch()
    result = service(tmp_path, search).discover("alex")
    assert search.calls == 0
    assert result["source"] == "synthetic_fallback"
    assert "click Refresh" in result["warning"]


def test_missing_key_returns_labeled_synthetic_fallback_without_call(tmp_path):
    def forbidden_getter(url, timeout):
        raise AssertionError("No external call is allowed in this test")

    search = GuardianProviderSearchClient(None, getter=forbidden_getter)
    result = service(tmp_path, search).discover("alex", refresh=True)
    assert result["source"] == "synthetic_fallback"
    assert "not configured" in result["warning"]
    assert all(provider["synthetic"] for provider in result["providers"])
    assert all(provider["status"] == "needs_verification" for provider in result["providers"])
    assert all(
        "price" not in provider and "discount" not in provider for provider in result["providers"]
    )


def test_serpapi_normalization_ignores_offer_snippets():
    requested_urls = []

    def getter(url, timeout):
        requested_urls.append(url)
        return {
            "local_results": {
                "places": [
                    {
                        "position": 1,
                        "title": "Toyota Service Center",
                        "address": "200 Service Rd",
                        "rating": 4.6,
                        "reviews": 88,
                        "website": "https://example.test/service",
                        "description": "$50 discount this week",
                    }
                ]
            }
        }

    result = GuardianProviderSearchClient("test-key", getter=getter).search(
        query="Toyota authorized service center", location="Austin, TX"
    )
    provider = result.providers[0]
    assert provider.name == "Toyota Service Center"
    assert provider.rating == 4.6
    assert provider.review_count == 88
    assert provider.link == "https://example.test/service"
    assert not hasattr(provider, "price")
    assert not hasattr(provider, "discount")
    assert "engine=google_maps" in requested_urls[0]
    assert "location=Austin%2C+TX" in requested_urls[0]
    assert "z=12" in requested_urls[0]


def test_serpapi_normalizes_current_local_results_list_shape():
    payload = {
        "local_results": [
            {
                "position": 1,
                "title": "Current Shape Toyota",
                "address": "300 Current St",
                "rating": 4.8,
                "reviews": 42,
                "website": "https://example.test/current",
            }
        ]
    }
    result = GuardianProviderSearchClient("test-key", getter=lambda url, timeout: payload).search(
        query="Toyota authorized service center", location="Austin, TX"
    )
    assert [provider.name for provider in result.providers] == ["Current Shape Toyota"]


def test_serpapi_treats_invalid_local_results_shape_as_empty():
    result = GuardianProviderSearchClient(
        "test-key", getter=lambda url, timeout: {"local_results": "unexpected"}
    ).search(query="Toyota authorized service center", location="Austin, TX")
    assert result.providers == ()
    assert "No live providers" in result.warning


def test_provider_links_reject_place_ids_relative_urls_and_arbitrary_schemes():
    def getter(url, timeout):
        return {
            "local_results": {
                "places": [
                    {"title": "Place ID only", "place_id_search": "ChIJ123"},
                    {"title": "Relative", "link": "/maps/place/example"},
                    {"title": "Unsafe", "website": "javascript:alert(1)"},
                    {"title": "Secure", "website": "https://example.test/service"},
                ]
            }
        }

    result = GuardianProviderSearchClient("test-key", getter=getter).search(
        query="Toyota authorized service center", location="Austin, TX"
    )
    by_name = {provider.name: provider for provider in result.providers}
    assert by_name["Place ID only"].link is None
    assert by_name["Relative"].link is None
    assert by_name["Unsafe"].link is None
    assert by_name["Secure"].link == "https://example.test/service"


def test_endpoint_uses_profile_id_and_refresh_only(tmp_path):
    search = CountingSearch()
    app = create_app()
    app.dependency_overrides[get_guardian_provider_service] = lambda: service(tmp_path, search)
    with TestClient(app) as client:
        response = client.get("/api/v1/guardian/providers?profile=alex&refresh=true")
        invalid = client.get("/api/v1/guardian/providers?profile=missing")
    assert response.status_code == 200
    assert response.json()["providers"][0]["review_count"] == 125
    assert invalid.status_code == 404
    app.dependency_overrides.clear()
