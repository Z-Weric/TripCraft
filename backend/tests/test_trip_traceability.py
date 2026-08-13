import unittest
from unittest.mock import AsyncMock, Mock, patch

import json

from api.itineraries import (
    SaveTripRequest,
    UpdateTripRequest,
    _itinerary_diff,
    _poi_version,
    save_trip,
    update_trip,
)


class TripTraceabilityTest(unittest.IsolatedAsyncioTestCase):
    def test_poi_version_is_stable_for_same_facts(self):
        itinerary = {
            "itinerary": [
                {
                    "items": [
                        {
                            "poi_id": 1,
                            "spot": "景点",
                            "lat": 30.1,
                            "lng": 120.1,
                            "cost": 10,
                            "duration": "2h",
                            "note": "文案一",
                        }
                    ]
                }
            ]
        }
        changed_prose = {
            "itinerary": [
                {"items": [{**itinerary["itinerary"][0]["items"][0], "note": "文案二"}]}
            ]
        }

        self.assertEqual(_poi_version(itinerary), _poi_version(changed_prose))

    def test_itinerary_diff_records_replace_reorder_delete_and_note(self):
        before = {
            "itinerary": [
                {
                    "day": 1,
                    "items": [
                        {"poi_id": 1, "spot": "A", "note": "旧"},
                        {"poi_id": 2, "spot": "B", "note": ""},
                        {"poi_id": 3, "spot": "C", "note": ""},
                    ],
                }
            ]
        }
        after = {
            "itinerary": [
                {
                    "day": 1,
                    "items": [
                        {"poi_id": 2, "spot": "B", "note": "新"},
                        {"poi_id": 4, "spot": "D", "note": ""},
                    ],
                }
            ]
        }

        differences = _itinerary_diff(before, after)

        self.assertIn("note_update", differences["action_types"])
        self.assertIn("replace", differences["action_types"])
        self.assertTrue(any(event["type"] == "delete" for event in differences["events"]))

    def test_itinerary_diff_records_reorder(self):
        before = {
            "itinerary": [
                {
                    "day": 1,
                    "items": [
                        {"poi_id": 1, "spot": "A"},
                        {"poi_id": 2, "spot": "B"},
                    ],
                }
            ]
        }
        after = {
            "itinerary": [
                {
                    "day": 1,
                    "items": [
                        {"poi_id": 2, "spot": "B"},
                        {"poi_id": 1, "spot": "A"},
                    ],
                }
            ]
        }

        differences = _itinerary_diff(before, after)

        self.assertEqual(differences["action_types"], ["reorder"])

    async def test_save_trip_persists_generation_traceability(self):
        request = SaveTripRequest(
            destination="杭州",
            days=1,
            budget=500,
            itinerary={
                "summary": "摘要",
                "total_cost": 10,
                "itinerary": [
                    {
                        "items": [
                            {
                                "poi_id": 1,
                                "spot": "西湖",
                                "lat": 30.25,
                                "lng": 120.15,
                                "cost": 10,
                                "duration": "2h",
                            }
                        ]
                    }
                ],
            },
            generation_source="llm",
            validation_status="valid",
            model_version="ollama:qwen3.5:9b",
        )
        db = Mock()
        with patch(
            "api.itineraries.get_current_user",
            new=AsyncMock(return_value={"user_id": 7}),
        ):
            result = await save_trip(request, db, "Bearer token")

        saved = db.add.call_args.args[0]
        self.assertEqual(saved.model_version, "ollama:qwen3.5:9b")
        self.assertEqual(saved.planner_version, "planner-v1")
        self.assertEqual(saved.generation_source, "llm")
        self.assertEqual(saved.validation_status, "valid")
        self.assertEqual(len(saved.poi_version), 64)
        self.assertEqual(result["status"], "ok")

    async def test_update_trip_records_event_and_increments_version(self):
        before = {
            "summary": "旧摘要",
            "total_cost": 10,
            "itinerary": [
                {"day": 1, "items": [{"poi_id": 1, "spot": "A", "note": "旧"}]}
            ],
        }
        after = {
            "summary": "新摘要",
            "total_cost": 20,
            "itinerary": [
                {"day": 1, "items": [{"poi_id": 1, "spot": "A", "note": "新"}]}
            ],
        }
        trip = Mock(
            id=10,
            user_id=7,
            version=1,
            itinerary_json=json.dumps(before, ensure_ascii=False),
            summary="旧摘要",
            total_cost=10,
        )
        query = Mock()
        query.filter.return_value.first.return_value = trip
        db = Mock()
        db.query.return_value = query

        result = await update_trip(
            10,
            UpdateTripRequest(itinerary=after),
            db,
            {"user_id": 7},
        )

        event = db.add.call_args.args[0]
        self.assertEqual(event.action_types, "note_update")
        self.assertEqual(event.from_version, 1)
        self.assertEqual(event.to_version, 2)
        self.assertEqual(trip.version, 2)
        self.assertEqual(json.loads(trip.itinerary_json), after)
        self.assertEqual(result["version"], 2)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
