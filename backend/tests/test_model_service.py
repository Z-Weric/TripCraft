import unittest
from unittest.mock import AsyncMock, patch

from services.model_service import ModelCallResult, _build_prompt, generate_itinerary


def sample_pois():
    return [
        {
            "id": index,
            "city": "测试城",
            "name": f"景点{index}",
            "category": "自然风光",
            "lat": 30 + index * 0.001,
            "lng": 120 + index * 0.001,
            "cost": index * 10,
            "duration": "2h",
            "note": "数据库备注",
            "rating": 5 - index * 0.1,
        }
        for index in range(1, 4)
    ]


def valid_narrative(summary="模型摘要"):
    return {
        "summary": summary,
        "days": [
            {
                "day": 1,
                "transport_advice": "建议步行",
                "items": [
                    {"poi_id": index, "note": f"文案{index}", "reason": f"理由{index}"}
                    for index in (1, 2, 3)
                ],
            }
        ],
    }


class ModelServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_forbids_unsupported_travel_claims(self):
        prompt = _build_prompt({"destination": "测试城", "itinerary": []})
        self.assertIn("事实包直接推出", prompt)
        self.assertIn("可划船", prompt)
        self.assertIn("天气或季节", prompt)

    async def test_returns_complete_deterministic_plan_when_llm_is_unavailable(self):
        with patch(
            "services.model_service._llm_generate",
            new=AsyncMock(
                return_value=ModelCallResult(
                    payload=None,
                    error="provider unavailable",
                    available=False,
                )
            ),
        ) as llm_generate:
            result = await generate_itinerary("测试城", 1, 100, [], sample_pois(), [3])

        self.assertEqual(result.generation_source, "planner")
        self.assertEqual(result.validation_status, "fallback")
        self.assertEqual(result.fallback_reason, "provider unavailable")
        self.assertEqual(len(result.itinerary["itinerary"][0]["items"]), 3)
        self.assertEqual(result.itinerary["itinerary"][0]["items"][0]["poi_id"], 3)
        self.assertEqual(llm_generate.await_count, 1)

    async def test_model_can_only_change_allow_listed_text(self):
        narrative = valid_narrative()
        with patch(
            "services.model_service._llm_generate",
            new=AsyncMock(return_value=ModelCallResult(payload=narrative)),
        ):
            result = await generate_itinerary("测试城", 1, 200, [], sample_pois())

        first_item = result.itinerary["itinerary"][0]["items"][0]
        self.assertEqual(result.generation_source, "llm")
        self.assertEqual(result.itinerary["summary"], "模型摘要")
        self.assertEqual(first_item["note"], "文案1")
        self.assertEqual(first_item["spot"], "景点1")
        self.assertEqual(first_item["lat"], 30.001)
        self.assertEqual(first_item["cost"], 10)

    async def test_rejects_fact_tampering_then_accepts_one_repair(self):
        tampered = valid_narrative()
        tampered["days"][0]["items"][0]["cost"] = 0
        generate = AsyncMock(
            side_effect=[
                ModelCallResult(payload=tampered),
                ModelCallResult(payload=valid_narrative("修复后摘要")),
            ]
        )
        with patch("services.model_service._llm_generate", new=generate):
            result = await generate_itinerary("测试城", 1, 200, [], sample_pois())

        self.assertEqual(generate.await_count, 2)
        self.assertEqual(result.generation_source, "llm_repaired")
        self.assertEqual(result.validation_status, "repaired")
        self.assertEqual(result.itinerary["summary"], "修复后摘要")
        self.assertEqual(result.itinerary["itinerary"][0]["items"][0]["cost"], 10)

    async def test_falls_back_after_one_failed_repair(self):
        invalid = {"summary": "非法输出", "days": []}
        generate = AsyncMock(return_value=ModelCallResult(payload=invalid))
        with patch("services.model_service._llm_generate", new=generate):
            result = await generate_itinerary("测试城", 1, 200, [], sample_pois())

        self.assertEqual(generate.await_count, 2)
        self.assertEqual(result.generation_source, "planner")
        self.assertEqual(result.validation_status, "fallback")
        self.assertIn("天数", result.fallback_reason)


if __name__ == "__main__":
    unittest.main()
