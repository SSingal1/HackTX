import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

import certifi

from nextmove.decision.models import DecisionResult, Evidence

JsonPoster = Callable[[str, dict[str, Any], float], dict[str, Any]]


@dataclass(frozen=True)
class GeminiExplanation:
    summary: str
    option_explanations: dict[str, str]
    cited_evidence_ids: tuple[str, ...]
    warning: str | None = None


def _default_post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read())


class GeminiClient:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        *,
        poster: JsonPoster = _default_post,
        timeout: float = 12.0,
    ):
        self.api_key, self.model, self.poster, self.timeout = api_key, model, poster, timeout

    def explain(
        self, decision: DecisionResult, evidence: tuple[Evidence, ...]
    ) -> GeminiExplanation:
        fallback = self._fallback(decision)
        if not self.api_key:
            return GeminiExplanation(
                **fallback, warning="Gemini is not configured; using deterministic copy."
            )
        prompt = {
            "decision": decision.to_api_dict(),
            "evidence": [e.__dict__ for e in evidence],
            "instructions": (
                "Explain only supplied computed results. Do not calculate, invent numbers, "
                "claim approval, or treat asking prices as offers. Cite only supplied "
                "evidence_ids. Return JSON."
            ),
        }
        schema = {
            "type": "OBJECT",
            "properties": {
                "summary": {"type": "STRING"},
                "option_explanations": {"type": "OBJECT"},
                "cited_evidence_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["summary", "option_explanations", "cited_evidence_ids"],
        }
        body = {
            "contents": [{"parts": [{"text": json.dumps(prompt, default=str)}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        try:
            response = self.poster(url, body, self.timeout)
            value = json.loads(response["candidates"][0]["content"]["parts"][0]["text"])
            citations = tuple(value.get("cited_evidence_ids", ()))
            if not set(citations).issubset({e.evidence_id for e in evidence}):
                raise ValueError("unsupported citation")
            combined = " ".join(
                [
                    str(value.get("summary", "")),
                    *map(str, value.get("option_explanations", {}).values()),
                ]
            )
            allowed = set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(decision.to_api_dict())))
            if any(n not in allowed for n in re.findall(r"-?\d+(?:\.\d+)?", combined)):
                raise ValueError("unsupported numeric claim")
            return GeminiExplanation(
                str(value["summary"]), dict(value["option_explanations"]), citations
            )
        except Exception as exc:
            return GeminiExplanation(
                **fallback, warning=f"Gemini explanation unavailable: {type(exc).__name__}."
            )

    @staticmethod
    def _fallback(decision: DecisionResult) -> dict[str, Any]:
        explanations = {
            o.option_id: (
                f"{o.label} has ${o.total_cash_outflow:.2f} in projected cash outflow "
                f"over {decision.horizon_months} months."
            )
            for o in decision.options
        }
        return {
            "summary": decision.next_action,
            "option_explanations": explanations,
            "cited_evidence_ids": (),
        }
