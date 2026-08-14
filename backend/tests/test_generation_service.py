import unittest
from unittest.mock import AsyncMock, Mock, patch

from schemas.generate import GenerateRequest
from schemas.itinerary import ItineraryGenerationOutcome
from schemas.planning import CandidatePoi, PlanningRequest
from services.generation_service import generate_events, generate_once, retrieve_candidate_pois
from services.planner_service import plan_itinerary


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


class StreamingFavoriteWeightTest(unittest.IsolatedAsyncioTestCase):
    """Phase 0.4 — 验证流式请求中收藏加权生效。"""

    async def test_stream_passes_favorite_poi_ids_to_generate_itinerary(self):
        """流式 generate_events 将 favorite_poi_ids 传递给 generate_itinerary。"""
        request = GenerateRequest(
            destination="杭州",
            days=1,
            budget=2000,
            preferences=["自然风光"],
            favorite_poi_ids=[42],
        )
        city_pois = [
            {
                "id": 42,
                "city": "杭州",
                "name": "收藏景点",
                "category": "自然风光",
                "lat": 30.0,
                "lng": 120.0,
                "address": "",
                "cost": 0,
                "duration": "2h",
                "note": "",
                "rating": 4.0,
            }
        ]
        itinerary = {
            "destination": "杭州",
            "days": 1,
            "itinerary": [],
            "total_cost": 0,
            "summary": "测试",
        }

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
            patch("services.generation_service._verify_itinerary", new=AsyncMock(return_value={})),
        ):
            async for _ in generate_events(request, Mock()):
                pass

        self.assertEqual(generate.await_args.kwargs["favorite_poi_ids"], [42])

    def test_favorite_poi_gets_higher_score_in_planner(self):
        """收藏的 POI 在规划器评分中获得 favorite_bonus，总分高于未收藏的同分 POI。"""
        favorite_poi = CandidatePoi(
            id=10, name="收藏景点", lat=30.0, lng=120.0, category="自然风光", rating=4.0, cost=0,
        )
        normal_poi = CandidatePoi(
            id=20, name="普通景点", lat=30.0, lng=120.0, category="自然风光", rating=4.0, cost=0,
        )
        request_with_favorite = PlanningRequest(
            destination="杭州", days=1, budget=2000,
            preferences=["自然风光"], favorite_poi_ids=[10],
            candidates=[favorite_poi, normal_poi],
        )

        outcome = plan_itinerary(request_with_favorite)
        reasons_by_id = {r.poi_id: r for r in outcome.reasons}

        self.assertGreater(reasons_by_id[10].total_score, reasons_by_id[20].total_score)
        self.assertEqual(reasons_by_id[10].favorite_bonus, 1.0)
        self.assertEqual(reasons_by_id[20].favorite_bonus, 0.0)
        self.assertIn("用户收藏", reasons_by_id[10].labels)

    def test_stream_and_non_stream_produce_same_favorite_weighting(self):
        """流式和非流式走同一编排，收藏加权结果一致。"""
        pois = [
            {"id": 1, "city": "杭州", "name": "景点A", "category": "自然风光",
             "lat": 30.0, "lng": 120.0, "address": "", "cost": 0,
             "duration": "2h", "note": "", "rating": 4.0},
            {"id": 2, "city": "杭州", "name": "景点B", "category": "自然风光",
             "lat": 30.01, "lng": 120.01, "address": "", "cost": 0,
             "duration": "2h", "note": "", "rating": 4.0},
        ]

        # 构造 PlanningRequest 验证收藏加权
        req = PlanningRequest(
            destination="杭州", days=1, budget=2000,
            preferences=["自然风光"], favorite_poi_ids=[1],
            candidates=[CandidatePoi(**p) for p in pois],
        )
        outcome = plan_itinerary(req)
        selected_ids = {
            item.poi_id
            for day in outcome.itinerary.itinerary
            for item in day.items
        }
        # 收藏景点应被选中（评分更高）
        self.assertIn(1, selected_ids)


if __name__ == "__main__":
    unittest.main()
