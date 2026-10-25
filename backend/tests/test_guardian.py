import pytest
from fastapi.testclient import TestClient

import nextmove.data.guardian as guardian_data
from nextmove.api.dependencies import get_guardian_repository
from nextmove.data.guardian import LOCAL_SYNTHETIC_PROFILES, ResilientGuardianProfileRepository
from nextmove.main import create_app
from nextmove.settings import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_DATABASE_PATH", str(tmp_path / "guardian.sqlite3"))
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_guardian_repository] = lambda: ResilientGuardianProfileRepository(
        None
    )
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_synthetic_comparisons(client):
    listed = client.get("/api/v1/guardian/profiles").json()
    assert len(listed["profiles"]) == 3
    assert listed["sources"] == ["local_synthetic_fallback"]
    assert listed["profiles"]["alex"]["vehicle"]["model"] == "Camry"
    assert listed["profiles"]["covered"]["contract"]["contract_type"] == "CASH"
    assert listed["profiles"]["limited"]["service_history"]

    def compare(**inputs):
        response = client.post("/api/v1/guardian/compare", json=inputs)
        assert response.status_code == 200
        return response.json()

    base = compare()
    assert base["calculation"]["keep"] == 3800
    assert base["calculation"]["replace"] == 9420
    assert base["calculation"]["keepReserveOK"] is True
    assert base["calculation"]["keepMonthlyOK"] is True
    assert len(base["upgrade_options"]) == 3
    assert base["decision"]["comparison_basis"] == "cash_flow"
    assert base["profile"]["name"] == "Alex Morgan"
    assert base["source"]["type"] == "local_synthetic_fallback"
    assert compare(discount=True)["calculation"]["oop"] == 1750
    covered = compare(profile="covered", discount=True, repair=500)["calculation"]
    assert covered["coverage"] == 500
    assert covered["discount"] == covered["oop"] == 0
    limited = compare(profile="limited")
    assert not limited["calculation"]["keepOK"]
    assert not limited["calculation"]["replaceOK"]
    assert all(x["rank"] is None for x in limited["decision"]["options"])
    assert limited["recommendation"]["warning"]
    assert compare(miles=24000)["calculation"]["fuelKeep"] == 2800
    monthly = compare(monthly_free_cash_flow=500)
    assert monthly["calculation"]["keepMonthlyOK"] is True
    assert monthly["calculation"]["replaceMonthlyOK"] is False
    liquid = compare(cash_on_hand=21000, repair=4500, reserve=2000)
    assert liquid["calculation"]["startingCash"] == 21000
    assert liquid["calculation"]["keepCash"] == 16500
    assert liquid["calculation"]["keepReserveOK"] is True
    lease = compare(upgrade_id="prius_le", upgrade_mode="lease")
    assert lease["selected_upgrade"]["label"] == "2025 Prius LE"
    assert lease["calculation"]["replacementPayment"] == 399
    assert client.post("/api/v1/guardian/compare", json={"profile": "missing"}).status_code == 404
    assert client.post("/api/v1/guardian/compare", json={"miles": -1}).status_code == 422
    assert client.post("/api/v1/guardian/compare", json={"cash": 999999}).status_code == 422


def test_inquiries_persist_and_are_profile_scoped(client):
    payload = {"inputs": {"profile": "covered"}, "consent": True, "request_id": "test-save"}
    assert (
        client.post("/api/v1/guardian/inquiries", json={**payload, "consent": False}).status_code
        == 422
    )
    saved = client.post("/api/v1/guardian/inquiries", json=payload).json()
    assert saved["cost"] == 800
    assert saved["simulated"]
    assert client.post("/api/v1/guardian/inquiries", json=payload).json() == saved
    assert client.get("/api/v1/guardian/history?profile=alex").json()["inquiries"] == []
    other_app = create_app()
    other_app.dependency_overrides[get_guardian_repository] = lambda: (
        ResilientGuardianProfileRepository(None)
    )
    with TestClient(other_app) as other:
        history = other.get("/api/v1/guardian/history?profile=covered").json()["inquiries"]
    assert history == [saved]
    conflict = {**payload, "inputs": {"profile": "alex"}}
    assert client.post("/api/v1/guardian/inquiries", json=conflict).status_code == 409


def test_site_is_served_with_api(client):
    assert client.get("/").url.path == "/site/index.html"
    assert client.get("/site/guardian.html").status_code == 200
    assert "apiBase" in client.get("/site/guardian.js").text


def test_fallback_is_only_used_when_snowflake_fails():
    class Available:
        def list_guardian_profiles(self):
            return {"alex": {"profile_id": "alex", "source": {"type": "snowflake"}}}

        def get_guardian_profile(self, profile_id):
            return {"profile_id": profile_id, "source": {"type": "snowflake"}}

    live = ResilientGuardianProfileRepository(Available())
    assert live.get_guardian_profile("alex")["source"]["type"] == "snowflake"

    class Unavailable:
        def list_guardian_profiles(self):
            raise ConnectionError

        def get_guardian_profile(self, profile_id):
            raise ConnectionError

    fallback = ResilientGuardianProfileRepository(Unavailable())
    assert fallback.get_guardian_profile("alex")["name"] == LOCAL_SYNTHETIC_PROFILES["alex"]["name"]
    assert fallback.get_guardian_profile("alex")["source"]["type"] == "local_synthetic_fallback"


def test_profile_reads_reuse_the_complete_cached_snowflake_load():
    class CountingProfiles:
        def __init__(self):
            self.loads = 0

        def list_guardian_profiles(self):
            self.loads += 1
            return {
                "alex": {"profile_id": "alex", "vehicle": {"model": "Camry"}},
                "covered": {"profile_id": "covered", "vehicle": {"model": "Corolla"}},
            }

        def get_guardian_profile(self, profile_id):
            raise AssertionError("Profile reads must use the complete profile cache")

    snowflake = CountingProfiles()
    repository = ResilientGuardianProfileRepository(snowflake)
    assert repository.list_guardian_profiles()["alex"]["vehicle"]["model"] == "Camry"
    assert repository.get_guardian_profile("covered")["vehicle"]["model"] == "Corolla"
    assert repository.get_guardian_profile("alex")["vehicle"]["model"] == "Camry"
    assert snowflake.loads == 1


def test_profile_cache_returns_independent_deep_copies():
    class Profiles:
        def list_guardian_profiles(self):
            return {"alex": {"profile_id": "alex", "vehicle": {"model": "Camry"}}}

    repository = ResilientGuardianProfileRepository(Profiles())
    listed = repository.list_guardian_profiles()
    listed["alex"]["vehicle"]["model"] = "Changed"
    profile = repository.get_guardian_profile("alex")
    profile["vehicle"]["model"] = "Also changed"
    assert repository.get_guardian_profile("alex")["vehicle"]["model"] == "Camry"


def test_expired_profile_cache_reloads(monkeypatch):
    class Profiles:
        def __init__(self):
            self.loads = 0

        def list_guardian_profiles(self):
            self.loads += 1
            return {"alex": {"profile_id": "alex", "load": self.loads}}

    now = 0.0
    monkeypatch.setattr(guardian_data, "monotonic", lambda: now)
    snowflake = Profiles()
    repository = ResilientGuardianProfileRepository(snowflake)
    assert repository.list_guardian_profiles()["alex"]["load"] == 1
    now += 299
    assert repository.get_guardian_profile("alex")["load"] == 1
    now += 1
    assert repository.list_guardian_profiles()["alex"]["load"] == 2
    assert snowflake.loads == 2


@pytest.mark.parametrize("profiles", [{}, {"alex": None}, {"wrong": {"profile_id": "alex"}}])
def test_invalid_snowflake_profile_results_are_not_cached(profiles):
    class InvalidProfiles:
        def __init__(self):
            self.loads = 0

        def list_guardian_profiles(self):
            self.loads += 1
            return profiles

    snowflake = InvalidProfiles()
    repository = ResilientGuardianProfileRepository(snowflake)
    assert repository.list_guardian_profiles()["alex"]["source"]["type"] == (
        "local_synthetic_fallback"
    )
    repository.list_guardian_profiles()
    assert snowflake.loads == 2
