"""Tests for structured quality logging (low ratings & validation failures)."""

import json
import unittest
from unittest.mock import Mock, patch

from services.quality_log_service import (
    LOW_RATING_THRESHOLD,
    log_low_rating,
    log_validation_failure,
)


def _make_trip(**overrides):
    defaults = dict(
        id=42,
        user_id=7,
        destination="杭州",
        days=3,
        budget=2000,
        preferences="自然风光,美食",
        generation_source="llm",
        validation_status="valid",
        fallback_reason=None,
        model_version="ollama:qwen3.5:9b",
    )
    defaults.update(overrides)
    return Mock(**defaults)


class LowRatingLogTest(unittest.TestCase):
    def test_does_not_log_when_rating_above_threshold(self):
        db = Mock()
        trip = _make_trip()
        log_low_rating(db, trip, rating=3)
        db.add.assert_not_called()

    def test_logs_when_rating_at_or_below_threshold(self):
        for rating in range(0, LOW_RATING_THRESHOLD + 1):
            db = Mock()
            trip = _make_trip()
            log_low_rating(db, trip, rating=rating)
            self.assertEqual(db.add.call_count, 1, f"rating={rating}")
            entry = db.add.call_args.args[0]
            self.assertEqual(entry.trigger, "low_rating")
            self.assertEqual(entry.trip_id, 42)

    def test_reason_json_contains_structured_fields(self):
        db = Mock()
        trip = _make_trip(generation_source="llm_repaired", validation_status="repaired")
        verification = {
            "overall_valid": False,
            "structure_valid": True,
            "spots_valid": False,
            "budget_valid": True,
            "route_valid": True,
            "calculation_valid": True,
            "verification_source": "local",
            "errors": [
                {"code": "POI_NOT_VERIFIED", "message": "景点未通过验证"},
                {"code": "DUPLICATE_SPOT", "message": "景点重复"},
            ],
        }
        log_low_rating(db, trip, rating=1, verification=verification)

        entry = db.add.call_args.args[0]
        reason = json.loads(entry.reason_json)

        self.assertEqual(reason["trigger"], "low_rating")
        self.assertEqual(reason["user_rating"], 1)
        self.assertEqual(reason["destination"], "杭州")
        self.assertEqual(reason["generation_source"], "llm_repaired")
        self.assertEqual(reason["error_codes"], ["POI_NOT_VERIFIED", "DUPLICATE_SPOT"])
        self.assertEqual(reason["error_count"], 2)
        self.assertFalse(reason["overall_valid"])
        self.assertEqual(entry.error_codes, "POI_NOT_VERIFIED,DUPLICATE_SPOT")

    def test_reason_json_excludes_pii(self):
        db = Mock()
        trip = _make_trip()
        log_low_rating(db, trip, rating=0)

        entry = db.add.call_args.args[0]
        reason_json = entry.reason_json
        self.assertNotIn("email", reason_json)
        self.assertNotIn("password", reason_json)
        self.assertNotIn("user_id", json.loads(reason_json))


class ValidationFailureLogTest(unittest.TestCase):
    def test_does_not_log_when_verification_passes(self):
        db = Mock()
        trip = _make_trip()
        log_validation_failure(db, trip=trip, verification={"overall_valid": True})
        db.add.assert_not_called()

    def test_logs_when_verification_fails(self):
        db = Mock()
        trip = _make_trip()
        verification = {
            "overall_valid": False,
            "structure_valid": False,
            "spots_valid": False,
            "budget_valid": False,
            "route_valid": False,
            "calculation_valid": False,
            "errors": [{"code": "MISSING_FIELD", "message": "缺少 destination"}],
        }
        log_validation_failure(db, trip=trip, verification=verification)

        entry = db.add.call_args.args[0]
        self.assertEqual(entry.trigger, "validation_failed")
        self.assertEqual(entry.trip_id, 42)
        self.assertEqual(entry.error_codes, "MISSING_FIELD")

        reason = json.loads(entry.reason_json)
        self.assertEqual(reason["trigger"], "validation_failed")
        self.assertFalse(reason["overall_valid"])
        self.assertEqual(reason["error_codes"], ["MISSING_FIELD"])

    def test_logs_without_trip_for_unsaved_failures(self):
        db = Mock()
        verification = {
            "overall_valid": False,
            "errors": [{"code": "BUDGET_EXCEEDED", "message": "超预算"}],
        }
        log_validation_failure(
            db,
            trip=None,
            destination="成都",
            days=5,
            budget=1000,
            generation_source="planner",
            validation_status="fallback",
            verification=verification,
        )

        entry = db.add.call_args.args[0]
        self.assertIsNone(entry.trip_id)
        self.assertEqual(entry.trigger, "validation_failed")
        self.assertEqual(entry.destination, "成都")
        self.assertEqual(entry.error_codes, "BUDGET_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
