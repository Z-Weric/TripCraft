import unittest

from pydantic import ValidationError

from schemas.generate import GenerateRequest


class GenerateRequestTest(unittest.TestCase):
    def test_normalizes_and_deduplicates_lists(self):
        request = GenerateRequest(
            destination="  杭州  ",
            days=3,
            budget=2000,
            preferences=[" 美食 ", "美食", "自然风光"],
            favorite_poi_ids=[2, 2, 5],
        )

        self.assertEqual(request.destination, "杭州")
        self.assertEqual(request.preferences, ["美食", "自然风光"])
        self.assertEqual(request.favorite_poi_ids, [2, 5])

    def test_rejects_invalid_boundaries(self):
        invalid_payloads = [
            {"destination": "", "days": 3, "budget": 2000},
            {"destination": "杭州", "days": 0, "budget": 2000},
            {"destination": "杭州", "days": 3, "budget": 0},
            {"destination": "杭州", "days": 3, "budget": 2000, "favorite_poi_ids": [0]},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                GenerateRequest(**payload)


if __name__ == "__main__":
    unittest.main()

