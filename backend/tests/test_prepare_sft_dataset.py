"""Tests for the training adapter's planner fact/narrative boundary."""

import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "model"
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from prepare_sft_dataset import build_training_record


class PrepareSftDatasetTest(unittest.TestCase):
    def test_moves_only_allow_listed_fields_to_model_output(self):
        sample = {
            "id": "trip-1",
            "quality_label": "gold",
            "instruction": json.dumps(
                {"destination": "Hangzhou", "days": 1, "budget": 500, "preferences": ["food"]}
            ),
            "output": json.dumps(
                {
                    "summary": "A relaxed day.",
                    "total_cost": 100,
                    "itinerary": [
                        {
                            "day": 1,
                            "day_cost": 100,
                            "transport_advice": "Walk between nearby stops.",
                            "items": [
                                {
                                    "poi_id": 7,
                                    "spot": "West Lake",
                                    "cost": 0,
                                    "lat": 30.2,
                                    "lng": 120.1,
                                    "duration": 120,
                                    "note": "Visit before sunset.",
                                    "reason": "Matches the scenic preference.",
                                }
                            ],
                        }
                    ],
                }
            ),
        }

        record = build_training_record(sample)

        self.assertIsNotNone(record)
        output = json.loads(record["output"])
        self.assertEqual(output["days"][0]["items"], [{"poi_id": 7, "note": "Visit before sunset.", "reason": "Matches the scenic preference."}])
        self.assertNotIn("spot", record["output"])
        self.assertNotIn("cost", record["output"])
        self.assertIn('"spot":"West Lake"', record["instruction"])

    def test_rejects_records_without_stable_poi_references(self):
        self.assertIsNone(build_training_record({"instruction": "{}", "output": "{}"}))


if __name__ == "__main__":
    unittest.main()
