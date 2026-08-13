import unittest
from unittest.mock import AsyncMock, patch

from services.verify_service import verify_itinerary, verify_spot_poi


KNOWN_POIS = [
    {"id": 1, "name": "西湖", "lat": 30.25, "lng": 120.15, "cost": 0},
    {"id": 2, "name": "灵隐寺", "lat": 30.24, "lng": 120.10, "cost": 50},
]


def valid_itinerary():
    return {
        "destination": "杭州",
        "days": 1,
        "itinerary": [
            {
                "day": 1,
                "items": [
                    {"spot": "西湖", "poi_id": 1, "lat": 30.25, "lng": 120.15, "cost": 0},
                    {"spot": "灵隐寺", "poi_id": 2, "lat": 30.24, "lng": 120.10, "cost": 50},
                ],
                "day_cost": 60,
            }
        ],
        "total_cost": 60,
        "summary": "测试行程",
    }


class SpotVerificationTest(unittest.IsolatedAsyncioTestCase):
    async def test_uses_local_match_when_external_is_unavailable(self):
        with patch("services.verify_service._verify_spot_external", new=AsyncMock(return_value=None)):
            result = await verify_spot_poi("西湖", 30.25, 120.15, KNOWN_POIS, 1)
        self.assertEqual(result, {"valid": True, "source": "local"})

    async def test_rejects_local_coordinate_mismatch(self):
        with patch("services.verify_service._verify_spot_external", new=AsyncMock(return_value=None)):
            result = await verify_spot_poi("西湖", 31.25, 121.15, KNOWN_POIS, 1)
        self.assertEqual(result, {"valid": False, "source": "unavailable"})


class ItineraryVerificationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.external_patch = patch("services.verify_service._verify_spot_external", new=AsyncMock(return_value=None))
        self.external_patch.start()

    async def asyncTearDown(self):
        self.external_patch.stop()

    async def test_accepts_valid_itinerary_with_local_source(self):
        result = await verify_itinerary(valid_itinerary(), 1000, KNOWN_POIS)
        self.assertTrue(result["overall_valid"])
        self.assertTrue(result["structure_valid"])
        self.assertTrue(result["spots_valid"])
        self.assertTrue(result["calculation_valid"])
        self.assertEqual(result["verification_source"], "local")
        self.assertEqual(result["errors"], [])

    async def test_reports_missing_fields_without_raising(self):
        result = await verify_itinerary({"destination": "杭州"}, 1000, KNOWN_POIS)
        self.assertFalse(result["overall_valid"])
        self.assertFalse(result["structure_valid"])
        self.assertIn("MISSING_FIELD", {error["code"] for error in result["errors"]})

    async def test_rejects_duplicate_spot_and_cost_mismatch(self):
        itinerary = valid_itinerary()
        itinerary["itinerary"][0]["items"][1] = {
            "spot": "西湖", "poi_id": 1, "lat": 30.25, "lng": 120.15, "cost": 0
        }
        itinerary["itinerary"][0]["day_cost"] = 10
        itinerary["total_cost"] = 60

        result = await verify_itinerary(itinerary, 1000, KNOWN_POIS)
        codes = {error["code"] for error in result["errors"]}
        self.assertFalse(result["spots_valid"])
        self.assertFalse(result["calculation_valid"])
        self.assertIn("DUPLICATE_SPOT", codes)
        self.assertIn("TOTAL_COST_MISMATCH", codes)

    async def test_rejects_over_budget_itinerary(self):
        result = await verify_itinerary(valid_itinerary(), 50, KNOWN_POIS)
        self.assertFalse(result["budget_valid"])
        self.assertIn("BUDGET_EXCEEDED", {error["code"] for error in result["errors"]})

    async def test_rejects_poi_cost_tampering(self):
        itinerary = valid_itinerary()
        itinerary["itinerary"][0]["items"][1]["cost"] = 5

        result = await verify_itinerary(itinerary, 1000, KNOWN_POIS)
        self.assertFalse(result["spots_valid"])
        self.assertIn("POI_COST_MISMATCH", {error["code"] for error in result["errors"]})

    async def test_rejects_day_cost_below_item_total(self):
        itinerary = valid_itinerary()
        itinerary["itinerary"][0]["day_cost"] = 40
        itinerary["total_cost"] = 40

        result = await verify_itinerary(itinerary, 1000, KNOWN_POIS)
        self.assertFalse(result["calculation_valid"])
        self.assertIn("DAY_COST_MISMATCH", {error["code"] for error in result["errors"]})

    async def test_rejects_route_over_fifty_kilometers(self):
        itinerary = valid_itinerary()
        itinerary["itinerary"][0]["items"][1].update({"lat": 31.0, "lng": 121.0})
        far_pois = [KNOWN_POIS[0], {**KNOWN_POIS[1], "lat": 31.0, "lng": 121.0}]

        result = await verify_itinerary(itinerary, 1000, far_pois)
        self.assertFalse(result["route_valid"])
        self.assertIn("ROUTE_TOO_FAR", {error["code"] for error in result["errors"]})


if __name__ == "__main__":
    unittest.main()
