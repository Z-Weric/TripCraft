import unittest
from unittest.mock import AsyncMock

from services.training_repair_service import merge_repaired_narrative, repair_narrative


def itinerary():
    return {
        "summary": "原摘要",
        "total_cost": 20,
        "itinerary": [{
            "day": 1,
            "day_cost": 20,
            "items": [{
                "poi_id": 7,
                "spot": "测试景点",
                "lat": 30.1,
                "lng": 120.1,
                "cost": 20,
                "duration": "2h",
                "time": "09:00",
                "note": "旧文案",
                "reason": "旧理由",
            }],
        }],
    }


def narrative_payload(summary="新摘要", poi_id=7):
    return {
        "summary": summary,
        "days": [{
            "day": 1,
            "transport_advice": "按规划顺序前往",
            "items": [{"poi_id": poi_id, "note": "中性说明", "reason": "符合用户偏好"}],
        }],
    }


class TrainingRepairTest(unittest.IsolatedAsyncioTestCase):
    def test_merge_keeps_immutable_facts(self):
        repaired = merge_repaired_narrative(itinerary(), narrative_payload())
        item = repaired["itinerary"][0]["items"][0]
        self.assertEqual(repaired["summary"], "新摘要")
        self.assertEqual(item["poi_id"], 7)
        self.assertEqual(item["lat"], 30.1)
        self.assertEqual(item["cost"], 20)
        self.assertEqual(item["note"], "中性说明")

    def test_merge_rejects_changed_poi_order(self):
        with self.assertRaises(ValueError):
            merge_repaired_narrative(itinerary(), narrative_payload(poi_id=8))

    async def test_repair_provider_response_is_structurally_validated(self):
        provider = type("Provider", (), {
            "model_id": "ollama:qwen",
            "generate_json": AsyncMock(return_value=narrative_payload()),
        })()
        repaired, error, prompt_hash = await repair_narrative(provider, {"destination": "测试城"}, itinerary(), {})
        self.assertIsNone(error)
        self.assertIsNotNone(repaired)
        self.assertEqual(len(prompt_hash), 64)
        self.assertEqual(provider.generate_json.await_count, 1)


if __name__ == "__main__":
    unittest.main()
