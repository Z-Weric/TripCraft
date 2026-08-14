"""Tests for training dataset export (model/export_training_dataset.py)."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model"))

import export_training_dataset as exporter


def _make_saved_trip(**overrides):
    defaults = dict(
        id=1,
        destination="杭州",
        days=2,
        budget=2000,
        preferences="自然风光,美食",
        summary="测试摘要",
        total_cost=500,
        itinerary_json=json.dumps({
            "summary": "测试",
            "total_cost": 500,
            "itinerary": [{"day": 1, "items": [{"poi_id": 1, "spot": "西湖", "lat": 30.25, "lng": 120.15, "cost": 0, "duration": "2h"}]}],
        }, ensure_ascii=False),
        verification_json=json.dumps({"overall_valid": True, "errors": []}, ensure_ascii=False),
        user_id=7,
        is_public=0,
        user_rating=4,
        model_version="ollama:qwen3.5:9b",
        planner_version="planner-v1",
        poi_version="abc123",
        generation_source="llm",
        validation_status="valid",
        fallback_reason=None,
        version=1,
    )
    defaults.update(overrides)
    return Mock(**defaults)


def _make_quality_log(**overrides):
    defaults = dict(
        id=1,
        trip_id=1,
        user_id=7,
        trigger="low_rating",
        destination="杭州",
        days=2,
        budget=2000,
        preferences="自然风光",
        generation_source="planner",
        validation_status="fallback",
        fallback_reason="LLM 不可用",
        model_version="none",
        error_codes="BUDGET_EXCEEDED",
        reason_json=json.dumps({
            "trigger": "low_rating",
            "user_rating": 1,
            "error_codes": ["BUDGET_EXCEEDED"],
        }, ensure_ascii=False),
    )
    defaults.update(overrides)
    return Mock(**defaults)


class QualityLabelTest(unittest.TestCase):
    def test_gold_label(self):
        trip = _make_saved_trip(user_rating=5, validation_status="valid")
        self.assertEqual(exporter._quality_label(trip), "gold")

    def test_silver_label(self):
        trip = _make_saved_trip(user_rating=3, validation_status="repaired")
        self.assertEqual(exporter._quality_label(trip), "silver")

    def test_fallback_label(self):
        trip = _make_saved_trip(user_rating=0, validation_status="fallback")
        self.assertEqual(exporter._quality_label(trip), "fallback")

    def test_negative_label(self):
        trip = _make_saved_trip(user_rating=1, validation_status="valid")
        self.assertEqual(exporter._quality_label(trip), "negative")


class SftSampleTest(unittest.TestCase):
    def test_build_sft_sample_structure(self):
        trip = _make_saved_trip()
        sample = exporter._build_sft_sample(trip)

        self.assertEqual(sample["id"], "trip-1")
        self.assertIn("instruction", sample)
        self.assertIn("output", sample)
        self.assertEqual(sample["quality_label"], "gold")
        self.assertEqual(sample["metadata"]["model_version"], "ollama:qwen3.5:9b")
        self.assertIn("exported_at", sample["metadata"])

    def test_sft_sample_is_sanitized(self):
        trip = _make_saved_trip()
        sample = exporter._build_sft_sample(trip)

        output = json.loads(sample["output"])
        self.assertNotIn("planning_warnings", output)
        self.assertNotIn("user_id", sample)
        self.assertNotIn("email", sample)


class EvalSampleTest(unittest.TestCase):
    def test_build_eval_sample_structure(self):
        trip = _make_saved_trip(user_rating=4, validation_status="valid")
        sample = exporter._build_eval_sample(trip)

        self.assertEqual(sample["id"], "trip-1")
        self.assertIn("request", sample)
        self.assertIn("expected_itinerary", sample)
        self.assertIn("verification", sample)
        self.assertEqual(sample["quality_label"], "gold")


class NegativeSampleTest(unittest.TestCase):
    def test_build_negative_sample_from_log(self):
        log = _make_quality_log()
        sample = exporter._build_negative_sample(log)

        self.assertEqual(sample["id"], "quality-log-1")
        self.assertEqual(sample["trigger"], "low_rating")
        self.assertEqual(sample["error_codes"], ["BUDGET_EXCEEDED"])
        self.assertEqual(sample["quality_label"], "negative")


class ExportIntegrationTest(unittest.TestCase):
    def test_export_sft_writes_jsonl(self):
        trips = [_make_saved_trip(id=1), _make_saved_trip(id=2, user_rating=5)]
        db = Mock()
        query = Mock()
        query.filter.return_value.order_by.return_value = trips
        db.query.return_value = query

        with tempfile.TemporaryDirectory() as tmpdir:
            count = exporter.export_sft(db, tmpdir, min_rating=3)
            self.assertEqual(count, 2)

            path = os.path.join(tmpdir, "sft_samples.jsonl")
            self.assertTrue(os.path.exists(path))

            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)
            sample = json.loads(lines[0])
            self.assertIn("instruction", sample)
            self.assertIn("output", sample)

    def test_export_negatives_writes_jsonl(self):
        logs = [_make_quality_log(id=1), _make_quality_log(id=2, trigger="validation_failed")]
        db = Mock()
        query = Mock()
        query.order_by.return_value = logs
        db.query.return_value = query

        with tempfile.TemporaryDirectory() as tmpdir:
            count = exporter.export_negatives(db, tmpdir)
            self.assertEqual(count, 2)

            path = os.path.join(tmpdir, "negative_samples.jsonl")
            self.assertTrue(os.path.exists(path))

            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
