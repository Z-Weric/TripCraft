import unittest

from schemas.planning import PlanningRequest
from services.fact_pack_service import build_fact_pack
from services.planner_service import plan_itinerary


class FactPackServiceTest(unittest.TestCase):
    def test_contains_only_selected_facts_and_no_unselected_city_pool(self):
        request = PlanningRequest(
            destination="测试城",
            days=1,
            budget=100,
            preferences=["自然风光"],
            candidates=[
                {
                    "id": index,
                    "name": f"景点{index}",
                    "category": "自然风光",
                    "lat": 30 + index * 0.001,
                    "lng": 120,
                    "cost": 0,
                    "rating": 6 - index,
                }
                for index in range(1, 6)
            ],
        )
        outcome = plan_itinerary(request)
        fact_pack = build_fact_pack(request, outcome)
        packed_ids = [item["poi_id"] for day in fact_pack["itinerary"] for item in day["items"]]

        self.assertEqual(len(packed_ids), 3)
        self.assertNotIn(5, packed_ids)
        self.assertNotIn("candidates", fact_pack)
        self.assertIn("distance_from_previous_km", fact_pack["itinerary"][0]["items"][1])


if __name__ == "__main__":
    unittest.main()
