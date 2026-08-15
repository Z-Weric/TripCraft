"""Tests for Phase 3.2 split building and offline evaluation."""

import os
import sys
import unittest


MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "model")
if MODEL_DIR not in sys.path:
    sys.path.insert(0, MODEL_DIR)

import build_dataset
import evaluate_model


def _itinerary(poi_ids):
    items = [
        {"poi_id": poi_id, "spot": f"POI {poi_id}", "lat": 30 + poi_id / 1000, "lng": 120 + poi_id / 1000, "cost": 10}
        for poi_id in poi_ids
    ]
    return {
        "destination": "杭州",
        "days": 1,
        "summary": "测试",
        "total_cost": len(items) * 10,
        "itinerary": [{"day": 1, "items": items, "day_cost": len(items) * 10}],
    }


def _sample(sample_id, destination="杭州", poi_ids=(1, 2), label="gold"):
    return {
        "id": sample_id,
        "request": {"destination": destination, "days": 1, "budget": 100, "preferences": ["自然风光"]},
        "expected_itinerary": _itinerary(poi_ids),
        "quality_label": label,
    }


class DatasetSplitTest(unittest.TestCase):
    def test_deduplicates_shared_request_or_poi_sequence(self):
        samples = [
            _sample("gold", poi_ids=(1, 2), label="gold"),
            _sample("same-request", poi_ids=(3, 4), label="silver"),
            _sample("same-pois", destination="成都", poi_ids=(1, 2), label="silver"),
            _sample("unique", destination="成都", poi_ids=(5, 6)),
        ]
        samples[-1]["request"]["budget"] = 200
        splits, manifest = build_dataset.build_dataset(samples, (0.5, 0.25, 0.25))
        retained_ids = {sample["id"] for split in splits.values() for sample in split}

        self.assertEqual(retained_ids, {"gold", "unique"})
        self.assertEqual(manifest["retained_samples"], 2)
        self.assertEqual(set(manifest["deduplicated_sample_ids"]["gold"]), {"same-request", "same-pois"})

    def test_split_is_deterministic_and_has_no_repeated_keys(self):
        samples = [_sample(f"sample-{index}", destination=f"城市{index}", poi_ids=(index + 1, index + 2)) for index in range(10)]
        first, _ = build_dataset.build_dataset(samples, (0.8, 0.1, 0.1))
        second, _ = build_dataset.build_dataset(list(reversed(samples)), (0.8, 0.1, 0.1))

        self.assertEqual(first, second)
        self.assertEqual({name: len(values) for name, values in first.items()}, {"train": 8, "validation": 1, "test": 1})


class OfflineEvaluationTest(unittest.TestCase):
    def test_reports_metrics_for_valid_and_invalid_predictions(self):
        samples = [_sample("valid"), _sample("invalid", destination="成都", poi_ids=(3, 4))]
        predictions = [
            {"id": "valid", "itinerary": _itinerary((1, 2)), "validation_status": "valid", "latency_ms": 40},
            {"id": "invalid", "itinerary": _itinerary((99,)), "validation_status": "repaired", "latency_ms": 100},
        ]
        report = evaluate_model.evaluate_samples(samples, predictions)

        self.assertEqual(report["evaluated_predictions"], 2)
        self.assertEqual(report["schema_valid_rate"], 1)
        self.assertGreater(report["allow_listed_poi_violation_rate"], 0)
        self.assertEqual(report["business_rule_pass_rate"], 0.5)
        self.assertEqual(report["no_repair_rate"], 0.5)
        self.assertEqual(report["p95_latency_ms"], 100)


if __name__ == "__main__":
    unittest.main()
