import unittest
from unittest.mock import AsyncMock, Mock, patch

from schemas.generate import GenerateRequest
from schemas.itinerary import ItineraryGenerationOutcome
from services.generation_service import generate_once, retrieve_candidate_pois


class GenerationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_passes_favorite_poi_ids_to_model(self):
        request = GenerateRequest(
            destination="杭州",
            days=2,
            budget=2000,
            preferences=["自然风光"],
            favorite_poi_ids=[7, 9],
        )
        city_pois = [
            {
                "id": 7,
                "city": "杭州",
                "name": "测试景点",
                "category": "自然风光",
                "lat": 30.0,
                "lng": 120.0,
                "address": "",
                "cost": 0,
                "duration": "2h",
                "note": "",
                "rating": 5.0,
            }
        ]
        itinerary = {
            "destination": "杭州",
            "days": 2,
            "itinerary": [],
            "total_cost": 0,
            "summary": "测试",
        }
        verification = {"spots_valid": True, "budget_valid": True, "route_valid": True}

        with (
            patch("services.generation_service.load_city_pois", return_value=city_pois),
            patch("services.generation_service.retrieve_candidate_pois", return_value=city_pois),
            patch(
                "services.generation_service._generate_itinerary",
                new=AsyncMock(
                    return_value=ItineraryGenerationOutcome(
                        itinerary=itinerary,
                        generation_source="planner",
                        validation_status="fallback",
                        fallback_reason="test",
                    )
                ),
            ) as generate,
            patch("services.generation_service._verify_itinerary", new=AsyncMock(return_value=verification)),
        ):
            result = await generate_once(request, Mock())

        self.assertEqual(result.itinerary, itinerary)
        self.assertEqual(generate.await_args.kwargs["favorite_poi_ids"], [7, 9])
        self.assertEqual(generate.await_args.kwargs["pois"], city_pois)
        self.assertEqual(result.generation_source, "planner")
        self.assertEqual(result.fallback_reason, "test")

    def test_rag_candidate_pool_uses_configured_multiplier(self):
        request = GenerateRequest(destination="杭州", days=2, budget=2000)
        city_pois = [{"id": index, "name": f"景点{index}"} for index in range(20)]

        with (
            patch("services.rag_service.is_index_ready", return_value=True),
            patch("services.rag_service.search_pois_by_rag", return_value=city_pois[:16]) as search,
            patch("services.generation_service.settings.candidate_pool_multiplier", 8),
        ):
            result = retrieve_candidate_pois(request, city_pois)

        self.assertEqual(len(result), 16)
        self.assertEqual(search.call_args.kwargs["top_k"], 16)


if __name__ == "__main__":
    unittest.main()
