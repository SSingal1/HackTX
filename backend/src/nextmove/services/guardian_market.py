"""Cached, opt-in market evidence for the synthetic Guardian demo."""

from __future__ import annotations

import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from nextmove.data.guardian import GuardianProfileRepository


class MarketSearch(Protocol):
    def search_market(self, query: str, *, location: str | None = None, limit: int = 5): ...


class GuardianMarketEvidenceService:
    """Retrieves no live data until a caller explicitly requests refresh=True."""

    def __init__(
        self,
        repository: GuardianProfileRepository,
        search: MarketSearch,
        database_path: str,
        ttl_seconds: int,
    ) -> None:
        self.repository = repository
        self.search = search
        self.database_path = Path(database_path).expanduser()
        self.ttl_seconds = ttl_seconds

    def evidence(self, profile_id: str, *, refresh: bool = False) -> dict[str, Any] | None:
        profile = self.repository.get_guardian_profile(profile_id)
        if profile is None:
            return None
        if not refresh:
            cached = self._read_cache(profile_id)
            if cached is not None:
                cached["cached"] = True
                return cached
            return self._empty(
                profile, "No cached live evidence. Select Refresh to search public sources."
            )

        location = str(profile.get("region") or "United States")[:100]
        vehicle = profile.get("vehicle") or {}
        model = self._vehicle_label(vehicle)
        replacement = "Toyota Corolla Hybrid LE"
        # Five bounded public-web searches per deliberate refresh. These are
        # references for a planning conversation, never a quote, offer, approval, or
        # automatic change to a comparison.
        searches = (
            ("fuel", "site:gasprices.aaa.com Austin TX regular gasoline price today", location),
            ("corolla", "site:toyota.com Corolla Hybrid LE MSRP lease Texas 2026", None),
            ("camry", "site:toyota.com Camry LE MSRP lease Texas 2026", None),
            ("prius", "site:toyota.com Prius LE MSRP lease Texas 2026", None),
            (
                "finance",
                'site:toyota.com/deals-incentives/texas Toyota "APR" financing',
                None,
            ),
        )
        with ThreadPoolExecutor(max_workers=len(searches)) as executor:
            futures = {
                key: executor.submit(self.search.search_market, query, location=place, limit=3)
                for key, query, place in searches
            }
            results = {key: future.result() for key, future in futures.items()}
        fuel = results["fuel"]
        corolla_reference = results["corolla"]
        camry_reference = results["camry"]
        prius_reference = results["prius"]
        finance_reference = results["finance"]
        categories = [
            self._category("Fuel-price research", fuel),
            self._category("Corolla Hybrid pricing and lease research", corolla_reference),
            self._category("Camry pricing and lease research", camry_reference),
            self._category("Prius pricing and lease research", prius_reference),
            self._category("Toyota regional finance and lease research", finance_reference),
        ]
        body = {
            "profile_id": profile_id,
            "location": location,
            "vehicle": model,
            "replacement_vehicle": replacement,
            "cached": False,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "source": "serpapi",
            "categories": [category for category in categories if category["evidence"]],
            "fuel_reference": self._fuel_reference(fuel),
            "notice": (
                "Public-web evidence only. A fuel reference is available only when an explicit "
                "AAA result contains a dollar amount. It must be confirmed before being used in "
                "a scenario. Vehicle pricing, lease payments, APRs, incentives, availability, "
                "coverage and eligibility need verification and do not silently alter this demo's "
                "synthetic calculation."
            ),
        }
        self._write_cache(profile_id, body)
        return body

    def adopt_fuel_reference(self, profile_id: str, evidence_id: str) -> dict[str, Any] | None:
        """Return a user-confirmation payload; never mutate a comparison automatically."""
        if self.repository.get_guardian_profile(profile_id) is None:
            return None
        cached = self._read_cache(profile_id)
        if cached is None:
            raise ValueError(
                "No current fuel research is available. Refresh public research first."
            )
        reference = cached.get("fuel_reference")
        if not isinstance(reference, dict) or reference.get("evidence_id") != evidence_id:
            raise ValueError("That evidence is not an adoptable fuel reference.")
        return {
            "profile_id": profile_id,
            "fuel_price_per_gallon": reference["price_per_gallon"],
            "fuel_evidence": reference,
            "requires_confirmation": True,
            "notice": (
                "This is a proposed planning input only. Confirm it in the scenario before "
                "recalculating; it has not changed any saved profile or comparison."
            ),
        }

    @staticmethod
    def _vehicle_label(vehicle: dict[str, Any]) -> str:
        return " ".join(
            str(vehicle.get(field) or "") for field in ("year", "make", "model", "trim")
        ).strip()[:100]

    @staticmethod
    def _category(label: str, result: Any) -> dict[str, Any]:
        items = []
        for evidence in result.evidence:
            item = asdict(evidence)
            item["status"] = str(item["status"])
            items.append(item)
        return {
            "label": label,
            "query": result.query,
            "evidence": items,
            "warning": result.warning,
            "status": "needs_verification",
        }

    @staticmethod
    def _fuel_reference(result: Any) -> dict[str, Any] | None:
        """Accept a numeric price only when it is attributable to AAA's public site."""
        for evidence in result.evidence:
            hostname = (urlparse(evidence.url).hostname or "").lower()
            if hostname != "gasprices.aaa.com" and not hostname.endswith(".gasprices.aaa.com"):
                continue
            match = re.search(r"\$\s*(\d+(?:\.\d+)?)", evidence.fact or "")
            if match is None:
                continue
            price = round(float(match.group(1)), 3)
            if not 1 <= price <= 10:
                continue
            return {
                "evidence_id": evidence.evidence_id,
                "price_per_gallon": price,
                "title": evidence.title,
                "url": evidence.url,
                "retrieved_at": evidence.retrieved_at,
                "status": "needs_verification",
                "attribution": "AAA public gas-price research",
            }
        return None

    def _empty(self, profile: dict[str, Any], notice: str) -> dict[str, Any]:
        vehicle = profile.get("vehicle") or {}
        return {
            "profile_id": profile["profile_id"],
            "location": str(profile.get("region") or "United States"),
            "vehicle": self._vehicle_label(vehicle),
            "cached": False,
            "retrieved_at": None,
            "source": "cache_only",
            "categories": [],
            "fuel_reference": None,
            "notice": notice,
        }

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS guardian_market_cache "
            "(profile_id TEXT PRIMARY KEY, cached_at REAL NOT NULL, body TEXT NOT NULL)"
        )
        return connection

    def _read_cache(self, profile_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT cached_at, body FROM guardian_market_cache WHERE profile_id=?",
                (profile_id,),
            ).fetchone()
        if row is None or datetime.now(UTC).timestamp() - row[0] >= self.ttl_seconds:
            return None
        return json.loads(row[1])

    def _write_cache(self, profile_id: str, body: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO guardian_market_cache(profile_id, cached_at, body) VALUES(?,?,?) "
                "ON CONFLICT(profile_id) DO UPDATE SET "
                "cached_at=excluded.cached_at, body=excluded.body",
                (profile_id, datetime.now(UTC).timestamp(), json.dumps(body)),
            )
