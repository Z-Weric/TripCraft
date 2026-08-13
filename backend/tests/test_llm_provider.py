import json
import unittest
from unittest.mock import patch

import httpx

from services.llm_provider import (
    DisabledProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderUnavailableError,
)
from services.llm_service import build_provider, get_default_provider


class LLMProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_health_and_json_generation(self):
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [{"name": "qwen3.5:9b"}]})
            return httpx.Response(
                200,
                json={"message": {"content": json.dumps({"summary": "ok"})}},
            )

        provider = OllamaProvider(
            "http://ollama.local",
            "qwen3.5:9b",
            transport=httpx.MockTransport(handler),
        )
        self.assertTrue(await provider.health_check())
        result = await provider.generate_json(
            [{"role": "user", "content": "test"}],
            {"type": "object", "properties": {"summary": {"type": "string"}}},
        )

        self.assertEqual(result, {"summary": "ok"})
        body = json.loads(requests[-1].content)
        self.assertEqual(body["model"], "qwen3.5:9b")
        self.assertEqual(body["format"]["type"], "object")
        self.assertFalse(body["stream"])

    def test_ollama_normalizes_openai_compatible_endpoint(self):
        provider = OllamaProvider(
            "http://localhost:11434/v1/chat/completions",
            "qwen3.5:9b",
        )

        self.assertEqual(provider.base_url, "http://localhost:11434")

    async def test_openai_compatible_json_generation(self):
        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"summary":"ok"}'}}]},
            )

        provider = OpenAICompatibleProvider(
            api_url="https://example.test/v1/chat/completions",
            api_key="secret",
            model="test-model",
            transport=httpx.MockTransport(handler),
        )
        result = await provider.generate_json(
            [{"role": "user", "content": "test"}],
            {"type": "object"},
        )

        self.assertEqual(result, {"summary": "ok"})
        self.assertEqual(captured["headers"]["authorization"], "Bearer secret")
        self.assertEqual(captured["body"]["response_format"]["type"], "json_schema")

    async def test_disabled_provider_is_explicitly_unavailable(self):
        provider = DisabledProvider()

        self.assertFalse(provider.available)
        self.assertFalse(await provider.health_check())
        with self.assertRaises(ProviderUnavailableError):
            await provider.generate_json([], {})

    async def test_ollama_circuit_opens_after_failure_threshold(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"error": "offline"})

        provider = OllamaProvider(
            "http://ollama.local",
            "qwen3.5:9b",
            retries=0,
            circuit_failure_threshold=1,
            circuit_cooldown=60,
            transport=httpx.MockTransport(handler),
        )
        with self.assertRaises(ProviderUnavailableError):
            await provider.generate_json([], {})
        with self.assertRaisesRegex(ProviderUnavailableError, "熔断器"):
            await provider.generate_json([], {})

    def test_provider_can_be_switched_by_configuration(self):
        self.assertIsInstance(build_provider("ollama"), OllamaProvider)
        self.assertIsInstance(build_provider("openai_compatible"), OpenAICompatibleProvider)
        self.assertIsInstance(build_provider("disabled"), DisabledProvider)

        with patch("services.llm_service.settings.llm_enabled_scopes", "chat"):
            self.assertIsInstance(get_default_provider("itinerary"), DisabledProvider)


if __name__ == "__main__":
    unittest.main()
