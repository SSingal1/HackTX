import unittest
from decimal import Decimal

from nextmove.decision.engine import DecisionEngine
from nextmove.decision.models import DecisionRequest, OptionInput
from nextmove.integrations.gemini import GeminiClient
from nextmove.integrations.serpapi import SerpApiClient


class SerpApiTests(unittest.TestCase):
    def test_missing_key_is_a_graceful_fallback(self):
        r = SerpApiClient(None).search_market("RAV4")
        self.assertEqual(r.evidence, ())
        self.assertIn("not configured", r.warning)

    def test_normalizes_results(self):
        r = SerpApiClient(
            "x",
            getter=lambda u, t: {
                "organic_results": [
                    {
                        "title": "Dealer",
                        "link": "https://example.com/car",
                        "snippet": "asking price",
                    }
                ]
            },
        ).search_market("RAV4")
        self.assertEqual(r.evidence[0].status.value, "needs_verification")

    def test_transport_error_is_fallback(self):
        def fail(u, t):
            raise TimeoutError

        r = SerpApiClient("x", getter=fail).search_market("RAV4")
        self.assertEqual(r.evidence, ())
        self.assertIn("unavailable", r.warning)


class GeminiTests(unittest.TestCase):
    @staticmethod
    def decision():
        request = DecisionRequest(
            "p",
            "r",
            "lease_end",
            12,
            (OptionInput("keep", "Keep", Decimal("0"), monthly_payment=Decimal("400")),),
        )
        return DecisionEngine().evaluate(request)

    def test_missing_key_uses_deterministic_copy(self):
        result = GeminiClient(None, "gemini-model").explain(self.decision(), ())
        self.assertIn("verify the assumptions", result.summary)
        self.assertIn("not configured", result.warning)

    def test_unsupported_numeric_claim_is_rejected(self):
        def poster(url, payload, timeout):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"summary":"Save 999 dollars",'
                                        '"option_explanations":{},'
                                        '"cited_evidence_ids":[]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

        result = GeminiClient("key", "gemini-model", poster=poster).explain(self.decision(), ())
        self.assertIn("unavailable", result.warning)
        self.assertNotIn("999", result.summary)
