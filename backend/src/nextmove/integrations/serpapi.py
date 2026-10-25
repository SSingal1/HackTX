import hashlib
import json
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import certifi

from nextmove.decision.models import Evidence, EvidenceStatus

JsonGetter = Callable[[str, float], dict[str, Any]]


@dataclass(frozen=True)
class SearchEvidenceResult:
    evidence: tuple[Evidence, ...]
    query: str
    warning: str | None = None


def _default_get(url: str, timeout: float) -> dict[str, Any]:
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(url, timeout=timeout, context=context) as response:
        return json.loads(response.read())


class SerpApiClient:
    def __init__(
        self, api_key: str | None, *, getter: JsonGetter = _default_get, timeout: float = 8.0
    ):
        self.api_key, self.getter, self.timeout = api_key, getter, timeout

    def search_market(
        self, query: str, *, location: str | None = None, limit: int = 5
    ) -> SearchEvidenceResult:
        return self._search("google", query, location, limit)

    def search_local(self, query: str, *, location: str, limit: int = 5) -> SearchEvidenceResult:
        return self._search("google_maps", query, location, limit)

    def _search(
        self, engine: str, query: str, location: str | None, limit: int
    ) -> SearchEvidenceResult:
        if not self.api_key:
            return SearchEvidenceResult(
                (), query, "SerpApi is not configured; verify market terms manually."
            )
        params = {"engine": engine, "q": query, "api_key": self.api_key}
        if location:
            params["location"] = location
        try:
            payload = self.getter(
                f"https://serpapi.com/search.json?{urlencode(params)}", self.timeout
            )
        except Exception as exc:
            return SearchEvidenceResult(
                (), query, f"Market evidence is temporarily unavailable: {type(exc).__name__}."
            )
        items = (
            payload.get("local_results", {}).get("places", [])
            if engine == "google_maps"
            else payload.get("organic_results", [])
        )
        now, evidence = datetime.now(UTC).isoformat(), []
        for item in items[: max(0, limit)]:
            url, title = (
                item.get("link") or item.get("website"),
                item.get("title") or item.get("name"),
            )
            if not url or not title:
                continue
            eid = hashlib.sha256(f"{url}|{now}".encode()).hexdigest()[:16]
            evidence.append(
                Evidence(
                    f"serp_{eid}",
                    str(title),
                    str(url),
                    now,
                    status=EvidenceStatus.NEEDS_VERIFICATION,
                    fact=item.get("snippet") or item.get("address"),
                )
            )
        return SearchEvidenceResult(
            tuple(evidence),
            query,
            None
            if evidence
            else "No supported search evidence was found; leave market values unknown.",
        )
