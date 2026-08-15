"""Tests for the training-review permissions and two-person approval state machine."""

import unittest

from pydantic import ValidationError

from api.training_reviews import ReviewSubmission, _eligible_candidate, _refresh_review_status, require_training_reviewer


DIMENSIONS = {
    "poi_accuracy": "pass",
    "route_reasonableness": "pass",
    "budget": "pass",
    "schedule": "pass",
    "readability": "pass",
    "preference_match": "pass",
}


class Record:
    def __init__(self, **values):
        self.__dict__.update(values)


class TrainingReviewTest(unittest.TestCase):
    def test_gold_requires_all_dimensions_to_pass(self):
        self.assertEqual(ReviewSubmission(label="gold", dimensions=DIMENSIONS).label, "gold")
        with self.assertRaises(ValidationError):
            ReviewSubmission(label="gold", dimensions={**DIMENSIONS, "readability": "minor_issue"})

    def test_two_matching_decisions_approve_gold(self):
        review = Record(status="pending", final_label=None)
        _refresh_review_status(review, [Record(label="gold"), Record(label="gold")])
        self.assertEqual(review.status, "approved")
        self.assertEqual(review.final_label, "gold")

    def test_conflicting_decisions_require_third_reviewer(self):
        review = Record(status="pending", final_label=None)
        _refresh_review_status(review, [Record(label="gold"), Record(label="silver")])
        self.assertEqual(review.status, "needs_adjudication")
        self.assertIsNone(review.final_label)

    def test_only_valid_high_quality_trips_are_candidates(self):
        self.assertTrue(_eligible_candidate(Record(user_rating=4, validation_status="valid", generation_source="llm")))
        self.assertFalse(_eligible_candidate(Record(user_rating=2, validation_status="valid", generation_source="llm")))
        self.assertFalse(_eligible_candidate(Record(user_rating=5, validation_status="fallback", generation_source="planner")))

    def test_reviewer_allowlist_is_required(self):
        from api import training_reviews

        original = training_reviews.settings.training_reviewer_emails
        training_reviews.settings.training_reviewer_emails = "reviewer@example.com"
        try:
            self.assertEqual(require_training_reviewer({"email": "reviewer@example.com"})["email"], "reviewer@example.com")
            with self.assertRaises(Exception):
                require_training_reviewer({"email": "other@example.com"})
        finally:
            training_reviews.settings.training_reviewer_emails = original


if __name__ == "__main__":
    unittest.main()
