from __future__ import annotations

import hashlib
import json
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

import certifi


@dataclass(frozen=True)
class ProviderEvidence:
    name: str
    address: str | None
    rating: float | None
    review_count: int | None
    position: int | None
    distance: str | None
    link: str | None
    retrieved_at: str
    evidence_id: str
    status: str = "needs_verification"
    synthetic: bool = False
    image_url: str | None = None


@dataclass(frozen=True)
class ProviderSearchResult:
    providers: tuple[ProviderEvidence, ...]
    warning: str | None = None


JsonGetter = Callable[[str, float], dict[str, Any]]


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(  # noqa: S310 - fixed endpoint with verified certifi CA bundle
        url, timeout=timeout, context=context
    ) as response:
        return json.loads(response.read())


class GuardianProviderSearchClient:
    """Bounded Google Maps search that never interprets snippets as offers."""

    def __init__(
        self,
        api_key: str | None,
        *,
        getter: JsonGetter = _get_json,
        timeout: float = 8,
        limit: int = 5,
    ) -> None:
        self.api_key = api_key
        self.getter = getter
        self.timeout = timeout
        self.limit = limit

    def search(self, *, query: str, location: str) -> ProviderSearchResult:
        if not self.api_key:
            return ProviderSearchResult((), "SerpApi is not configured.")
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "location": location,
            "z": "12",
            "api_key": self.api_key,
        }
        try:
            payload = self.getter(
                f"https://serpapi.com/search.json?{urlencode(params)}", self.timeout
            )
        except Exception as exc:
            return ProviderSearchResult(
                (), f"Live provider search is unavailable ({type(exc).__name__})."
            )

        retrieved_at = datetime.now(UTC).isoformat()
        providers: list[ProviderEvidence] = []
        for item in _local_places(payload)[: self.limit]:
            name = item.get("title") or item.get("name")
            if not name:
                continue
            address = item.get("address")
            link = _absolute_web_url(
                item.get("website") or item.get("links", {}).get("website") or item.get("link")
            )
            image_url = _absolute_web_url(
                item.get("thumbnail") or item.get("image") or (item.get("images") or [None])[0]
            )
            identity = f"{name}|{address or ''}|{link or ''}"
            evidence_id = "serp_provider_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
            providers.append(
                ProviderEvidence(
                    name=str(name),
                    address=str(address) if address else None,
                    rating=_float_or_none(item.get("rating")),
                    review_count=_int_or_none(item.get("reviews")),
                    position=_int_or_none(item.get("position")),
                    distance=str(item["distance"]) if item.get("distance") else None,
                    link=str(link) if link else None,
                    image_url=str(image_url) if image_url else None,
                    retrieved_at=retrieved_at,
                    evidence_id=evidence_id,
                )
            )
        warning = None if providers else "No live providers were returned by SerpApi."
        return ProviderSearchResult(tuple(providers), warning)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _absolute_web_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _local_places(payload: dict[str, Any]) -> list[dict[str, Any]]:
    local_results = payload.get("local_results")
    if isinstance(local_results, list):
        candidates = local_results
    elif isinstance(local_results, dict):
        candidates = local_results.get("places", [])
    else:
        return []
    if not isinstance(candidates, list):
        return []
    return [item for item in candidates if isinstance(item, dict)]
