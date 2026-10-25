from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from nextmove.data.guardian import GuardianProfileRepository
from nextmove.integrations.guardian_providers import ProviderEvidence


class ProviderSearch(Protocol):
    def search(self, *, query: str, location: str): ...


class GuardianProviderService:
    def __init__(
        self,
        repository: GuardianProfileRepository,
        search: ProviderSearch,
        database_path: str,
        ttl_seconds: int,
    ) -> None:
        self.repository = repository
        self.search = search
        self.database_path = Path(database_path).expanduser()
        self.ttl_seconds = ttl_seconds

    def discover(self, profile_id: str, *, refresh: bool = False) -> dict[str, Any] | None:
        profile = self.repository.get_guardian_profile(profile_id)
        if profile is None:
            return None
        query, location = self._safe_search_context(profile)
        if not refresh:
            cached = self._read_cache(profile_id)
            if cached is not None:
                cached["cached"] = True
                return cached
            providers = self._fallback(location)
            return {
                "profile_id": profile_id,
                "location": location,
                "providers": [asdict(provider) for provider in providers],
                "retrieved_at": providers[0].retrieved_at,
                "source": "synthetic_fallback",
                "cached": False,
                "warning": (
                    "No cached provider evidence is available. Showing synthetic examples; "
                    "click Refresh to request live provider evidence."
                ),
            }

        result = self.search.search(query=query, location=location)
        providers = result.providers
        warning = result.warning
        source = "serpapi"
        if not providers:
            providers = self._fallback(location)
            source = "synthetic_fallback"
            reason = warning or "No live provider evidence is available."
            warning = f"{reason} Showing synthetic examples; verify every provider before use."

        response = {
            "profile_id": profile_id,
            "location": location,
            "providers": [asdict(provider) for provider in providers],
            "retrieved_at": providers[0].retrieved_at,
            "source": source,
            "cached": False,
            "warning": warning,
        }
        self._write_cache(profile_id, response)
        return response

    @staticmethod
    def _safe_search_context(profile: dict[str, Any]) -> tuple[str, str]:
        vehicle = profile.get("vehicle", {})
        make = str(vehicle.get("make") or "Toyota")[:30]
        location = str(profile.get("region") or "Austin, TX")[:100]
        return f"{make} authorized service center", location

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS guardian_provider_cache "
            "(profile_id TEXT PRIMARY KEY, cached_at REAL NOT NULL, body TEXT NOT NULL)"
        )
        return connection

    def _read_cache(self, profile_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT cached_at, body FROM guardian_provider_cache WHERE profile_id=?",
                (profile_id,),
            ).fetchone()
        if row is None or datetime.now(UTC).timestamp() - row[0] >= self.ttl_seconds:
            return None
        return json.loads(row[1])

    def get_cached(self, profile_id: str) -> dict[str, Any] | None:
        """Read cached evidence without triggering or refreshing an external search."""
        return self._read_cache(profile_id)

    def _write_cache(self, profile_id: str, response: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO guardian_provider_cache(profile_id, cached_at, body) VALUES(?,?,?) "
                "ON CONFLICT(profile_id) DO UPDATE SET "
                "cached_at=excluded.cached_at, body=excluded.body",
                (profile_id, datetime.now(UTC).timestamp(), json.dumps(response)),
            )

    @staticmethod
    def _fallback(location: str) -> tuple[ProviderEvidence, ...]:
        now = datetime.now(UTC).isoformat()
        return (
            ProviderEvidence(
                name="Synthetic Toyota Service Example",
                address=f"Example location near {location}",
                rating=None,
                review_count=None,
                position=1,
                distance=None,
                link=None,
                image_url=None,
                retrieved_at=now,
                evidence_id="synthetic_provider_toyota_1",
                synthetic=True,
            ),
            ProviderEvidence(
                name="Synthetic Independent Service Example",
                address=f"Example location near {location}",
                rating=None,
                review_count=None,
                position=2,
                distance=None,
                link=None,
                image_url=None,
                retrieved_at=now,
                evidence_id="synthetic_provider_independent_1",
                synthetic=True,
            ),
        )
