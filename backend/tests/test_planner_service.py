import json
import unittest
from pathlib import Path

from schemas.planning import CandidatePoi, PlanningRequest
from services.planner_service import haversine, plan_itinerary


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "planner_pois.json"


def load_candidates() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def selected_items(outcome):
    return [item for day in outcome.itinerary.itinerary for item in day.items]


class PlannerServiceTest(unittest.TestCase):
    def make_request(self, **overrides) -> PlanningRequest:
        payload = {
            "destination": "测试城",
            "days": 2,
            "budget": 500,
            "preferences": [],
            "favorite_poi_ids": [],
            "candidates": load_candidates(),
        }
        payload.update(overrides)
        return PlanningRequest(**payload)

    def test_same_input_produces_stable_result(self):
        request = self.make_request(preferences=["自然风光"])

        first = plan_itinerary(request)
        second = plan_itinerary(request)

        self.assertEqual(first.model_dump(), second.model_dump())

    def test_preference_and_favorite_increase_score(self):
        candidates = [
            CandidatePoi(id=101, name="普通景点", category="购物", lat=30, lng=120, rating=5),
            CandidatePoi(id=102, name="偏好景点", category="自然风光", lat=30, lng=120, rating=4),
            CandidatePoi(id=103, name="收藏景点", category="美食", lat=30, lng=120, rating=4),
        ]
        outcome = plan_itinerary(
            self.make_request(
                days=1,
                preferences=["自然风光"],
                favorite_poi_ids=[103],
                candidates=candidates,
            )
        )
        reasons = {reason.poi_id: reason for reason in outcome.reasons}

        self.assertGreater(reasons[102].preference_bonus, 0)
        self.assertGreater(reasons[103].favorite_bonus, 0)
        self.assertEqual(outcome.itinerary.itinerary[0].items[0].poi_id, 102)

    def test_budget_is_never_exceeded_and_each_day_is_reserved(self):
        candidates = [
            CandidatePoi(
                id=index,
                name=f"景点{index}",
                category="自然风光",
                lat=30 + index * 0.001,
                lng=120 + index * 0.001,
                cost=10,
                rating=5 - index * 0.01,
            )
            for index in range(1, 7)
        ]
        outcome = plan_itinerary(self.make_request(days=2, budget=20, candidates=candidates))

        self.assertLessEqual(outcome.itinerary.total_cost, 20)
        self.assertTrue(all(day.items for day in outcome.itinerary.itinerary))

    def test_route_prefers_nearby_candidate_after_first_stop(self):
        candidates = [
            CandidatePoi(id=201, name="起点", category="自然风光", lat=30, lng=120, rating=5),
            CandidatePoi(id=202, name="近点", category="美食", lat=30.005, lng=120.005, rating=4),
            CandidatePoi(id=203, name="远点", category="美食", lat=30.2, lng=120.2, rating=4),
        ]
        outcome = plan_itinerary(self.make_request(days=1, candidates=candidates))
        items = outcome.itinerary.itinerary[0].items

        self.assertEqual([item.poi_id for item in items[:2]], [201, 202])
        self.assertLess(
            haversine(items[0].lat, items[0].lng, items[1].lat, items[1].lng),
            3,
        )

    def test_route_never_crosses_distant_geographic_clusters(self):
        candidates = load_candidates()[:5]
        candidates.extend(
            [
                {
                    **load_candidates()[5],
                    "id": 301,
                    "name": "远郊一号",
                    "lat": 31.2,
                    "lng": 121.2,
                    "rating": 4.9,
                },
                {
                    **load_candidates()[6],
                    "id": 302,
                    "name": "远郊二号",
                    "lat": 31.205,
                    "lng": 121.205,
                    "rating": 4.8,
                },
            ]
        )
        outcome = plan_itinerary(self.make_request(days=1, candidates=candidates))
        items = outcome.itinerary.itinerary[0].items

        for current, following in zip(items, items[1:]):
            self.assertLessEqual(
                haversine(current.lat, current.lng, following.lat, following.lng),
                50,
            )

    def test_duplicate_ids_and_names_are_removed(self):
        candidates = load_candidates()[:3]
        duplicate_id = {**candidates[0], "name": "相同编号的副本", "rating": 1}
        duplicate_name = {**candidates[1], "id": 999, "rating": 1}
        outcome = plan_itinerary(
            self.make_request(days=1, candidates=candidates + [duplicate_id, duplicate_name])
        )
        items = selected_items(outcome)

        self.assertEqual(len({item.poi_id for item in items}), len(items))
        self.assertEqual(len({item.spot for item in items}), len(items))
        self.assertEqual(outcome.candidate_count, 3)

    def test_exclusions_and_insufficient_candidates_are_observable(self):
        candidates = load_candidates()[:2]
        outcome = plan_itinerary(
            self.make_request(days=1, candidates=candidates, excluded_poi_ids=[1])
        )

        self.assertNotIn(1, [item.poi_id for item in selected_items(outcome)])
        self.assertTrue(any("候选景点不足" in warning for warning in outcome.warnings))


if __name__ == "__main__":
    unittest.main()
