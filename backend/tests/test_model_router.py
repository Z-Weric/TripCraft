import unittest
from unittest.mock import patch

from services.llm_provider import DisabledProvider
from services.model_router import route_model_request


class FakeProvider:
    def __init__(self, model_id: str, available: bool = True):
        self._model_id = model_id
        self._available = available

    @property
    def model_id(self):
        return self._model_id

    @property
    def available(self):
        return self._available


class ModelRouterTest(unittest.TestCase):
    def test_standard_request_prefers_local_provider(self):
        local = FakeProvider("ollama:qwen")
        external = FakeProvider("openai-compatible:external")
        with (
            patch("services.llm_service.get_default_provider", return_value=local),
            patch("services.llm_service.get_fallback_provider", return_value=external),
        ):
            route = route_model_request("itinerary", destination="杭州", days=3)

        self.assertIs(route.primary, local)
        self.assertEqual(route.reason, "standard_local_request")
        self.assertTrue(route.fallback_allowed)

    def test_complex_request_explicitly_routes_to_external_provider(self):
        local = FakeProvider("ollama:qwen")
        external = FakeProvider("openai-compatible:external")
        with (
            patch("services.llm_service.get_default_provider", return_value=local),
            patch("services.llm_service.get_fallback_provider", return_value=external),
        ):
            route = route_model_request(
                "itinerary",
                destination="杭州、上海",
                days=8,
                preferences=["自然", "美食", "历史", "亲子", "购物"],
            )

        self.assertIs(route.primary, external)
        self.assertIn("multi_city", route.reason)
        self.assertIn("long_itinerary", route.reason)
        self.assertIn("complex_preferences", route.reason)

    def test_disabled_fallback_never_triggers_external_route(self):
        local = FakeProvider("ollama:qwen")
        with (
            patch("services.llm_service.get_default_provider", return_value=local),
            patch("services.llm_service.get_fallback_provider", return_value=DisabledProvider()),
        ):
            route = route_model_request("itinerary", destination="杭州、上海")

        self.assertIs(route.primary, local)
        self.assertFalse(route.fallback_allowed)


if __name__ == "__main__":
    unittest.main()
