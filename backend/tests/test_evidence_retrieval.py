import unittest
from unittest.mock import patch

import httpx

from config import settings
from services.evidence_retrieval_service import claim_hash, retrieve_claim_evidence


class _FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json, headers):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 200,
                "data": {
                    "webPages": {
                        "value": [{
                            "name": "Official boating notice",
                            "url": "https://official.example/boating",
                            "snippet": "Boats are available.",
                            "siteName": "Official",
                            "datePublished": "2026-01-01",
                        }]
                    }
                },
            },
        )


class EvidenceRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_parses_citation_sources_without_exposing_key(self):
        original_enabled = settings.auto_eval_evidence_enabled
        original_key = settings.bocha_api_key
        settings.auto_eval_evidence_enabled = True
        settings.bocha_api_key = "test-key"
        try:
            with patch("services.evidence_retrieval_service.httpx.AsyncClient", return_value=_FakeClient()):
                result = await retrieve_claim_evidence("杭州", "西湖可划船")
        finally:
            settings.auto_eval_evidence_enabled = original_enabled
            settings.bocha_api_key = original_key
        self.assertEqual(result.claim_hash, claim_hash("西湖可划船"))
        self.assertEqual(result.sources[0].url, "https://official.example/boating")
        self.assertIsNone(result.error)


if __name__ == "__main__":
    unittest.main()
