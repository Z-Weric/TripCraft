"""Tests for deterministic gating and multi-model judge aggregation."""

import os
import sys
import unittest


MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "model")
if MODEL_DIR not in sys.path:
    sys.path.insert(0, MODEL_DIR)

from services.training_judge_service import (
    JudgeOutcome,
    aggregate_judgments,
    apply_evidence_consensus,
    build_configured_judge_providers,
    hard_gate,
)
from generate_benchmark_cases import build_cases
from export_approved_auto_labels import build_auto_sft_sample
from auto_label_training_samples import eligible_for_auto_approval


def _response(**overrides):
    value = {
        "itinerary": {
            "days": 1,
            "itinerary": [{"day": 1, "items": [{"poi_id": 1, "spot": "西湖"}]}],
        },
        "verification": {"overall_valid": True},
        "generation_source": "llm",
        "validation_status": "valid",
        "model_version": "ollama:qwen",
    }
    value.update(overrides)
    return value


def _outcome(provider: str, **overrides):
    rubric = {
        "fact_consistency": 5,
        "preference_match": 5,
        "readability": 4,
        "actionability": 4,
        "contradicted_claims": [],
        "unverified_claims": [],
        "error_codes": [],
        "recommendation": "accept",
        "confidence": 0.95,
    }
    rubric.update(overrides)
    return JudgeOutcome(provider, provider, rubric, "hash", 1)


class TrainingJudgeTest(unittest.TestCase):
    def test_hard_gate_rejects_fallback_and_invalid_business_rules(self):
        response = _response(generation_source="planner", validation_status="fallback", verification={"overall_valid": False})
        errors = hard_gate(response, {"days": 1})
        self.assertIn("BUSINESS_RULE_FAILED", errors)
        self.assertIn("NON_LLM_GENERATION", errors)
        self.assertIn("NARRATIVE_VALIDATION_FAILED", errors)

    def test_two_high_agreement_judges_become_auto_candidate(self):
        decision = aggregate_judgments([], [_outcome("judge-a"), _outcome("judge-b")], accept_confidence=0.90)
        self.assertEqual(decision.label, "auto_gold_candidate")
        self.assertGreaterEqual(decision.confidence, 0.90)
        self.assertTrue(eligible_for_auto_approval(decision))

    def test_auto_approval_allows_unknown_claims_by_default(self):
        silver = aggregate_judgments([], [_outcome("judge-a", unverified_claims=["opening hours"]), _outcome("judge-b")])
        self.assertEqual(silver.label, "auto_gold_candidate")
        self.assertTrue(eligible_for_auto_approval(silver))

    def test_repaired_candidate_can_be_auto_candidate_when_other_gates_pass(self):
        decision = aggregate_judgments(["REPAIR_REQUIRED"], [_outcome("judge-a"), _outcome("judge-b")])
        self.assertEqual(decision.label, "auto_gold_candidate")

    def test_one_independent_judge_cannot_become_auto_candidate(self):
        decision = aggregate_judgments([], [_outcome("judge-a")])
        self.assertEqual(decision.label, "silver")
        self.assertFalse(eligible_for_auto_approval(decision))

    def test_contradicted_claim_rejects_but_unverified_claim_stays_silver(self):
        rejected = aggregate_judgments([], [_outcome("judge-a", contradicted_claims=["wrong price"]), _outcome("judge-b")])
        self.assertEqual(rejected.label, "negative")
        unverified = aggregate_judgments(
            [],
            [_outcome("judge-a", unverified_claims=["opening hours"], recommendation="reject"), _outcome("judge-b")],
        )
        self.assertEqual(unverified.label, "auto_gold_candidate")
        silver = aggregate_judgments([], [_outcome("judge-a", readability=5, recommendation="reject"), _outcome("judge-b", readability=1)])
        self.assertEqual(silver.label, "silver")

    def test_unknown_claims_can_be_strictly_blocked_by_configuration(self):
        from services import training_judge_service

        original = training_judge_service.settings.auto_eval_allow_unverified_claims
        training_judge_service.settings.auto_eval_allow_unverified_claims = False
        try:
            decision = aggregate_judgments([], [_outcome("judge-a", unverified_claims=["opening hours"]), _outcome("judge-b")])
            self.assertEqual(decision.label, "silver")
        finally:
            training_judge_service.settings.auto_eval_allow_unverified_claims = original

    def test_cited_unanimous_evidence_resolves_unverified_claim(self):
        claim = "西湖可划船"
        evidence = [{"claim": claim, "claim_hash": "claim-1", "sources": [{"url": "https://official.example/boating"}]}]
        outcomes = [_outcome("judge-a", unverified_claims=[claim]), _outcome("judge-b", unverified_claims=[claim])]
        reviews = [
            {"claim_verdicts": [{"claim_hash": "claim-1", "verdict": "supported", "evidence_urls": ["https://official.example/boating"]}]},
            {"claim_verdicts": [{"claim_hash": "claim-1", "verdict": "supported", "evidence_urls": ["https://official.example/boating"]}]},
        ]
        apply_evidence_consensus(outcomes, reviews, evidence)
        self.assertEqual(outcomes[0].rubric["unverified_claims"], [])
        self.assertEqual(outcomes[1].rubric["unverified_claims"], [])

    def test_conflicting_or_uncited_evidence_remains_unverified(self):
        claim = "西湖可划船"
        evidence = [{"claim": claim, "claim_hash": "claim-1", "sources": [{"url": "https://official.example/boating"}]}]
        outcomes = [_outcome("judge-a", unverified_claims=[claim]), _outcome("judge-b", unverified_claims=[claim])]
        reviews = [
            {"claim_verdicts": [{"claim_hash": "claim-1", "verdict": "supported", "evidence_urls": ["https://official.example/boating"]}]},
            {"claim_verdicts": [{"claim_hash": "claim-1", "verdict": "refuted", "evidence_urls": ["https://official.example/boating"]}]},
        ]
        apply_evidence_consensus(outcomes, reviews, evidence)
        self.assertEqual(outcomes[0].rubric["unverified_claims"], [claim])

    def test_matrix_generation_is_deterministic_and_challenges_are_explicit(self):
        challenge = {"id": "challenge", "request": {"destination": "杭州", "days": 1, "budget": 100, "preferences": []}, "expected_risks": ["budget_pressure"]}
        first = build_cases(["杭州", "成都"], 4, 42, True, [challenge])
        second = build_cases(["杭州", "成都"], 4, 42, True, [challenge])
        self.assertEqual(first, second)
        self.assertEqual(first[-1]["scenario_type"], "challenge")
        self.assertEqual(first[-1]["expected_risks"], ["budget_pressure"])

    def test_dedicated_judge_profiles_do_not_reuse_generator_provider_settings(self):
        from services import training_judge_service

        settings = training_judge_service.settings
        original = {
            "providers": settings.auto_eval_judge_providers,
            "a_url": settings.auto_eval_judge_a_api_base,
            "a_key": settings.auto_eval_judge_a_api_key,
            "a_model": settings.auto_eval_judge_a_model,
            "b_url": settings.auto_eval_judge_b_api_base,
            "b_key": settings.auto_eval_judge_b_api_key,
            "b_model": settings.auto_eval_judge_b_model,
        }
        settings.auto_eval_judge_providers = "judge_a,judge_b"
        settings.auto_eval_judge_a_api_base, settings.auto_eval_judge_a_api_key, settings.auto_eval_judge_a_model = "https://a.test/v1/chat/completions", "a-key", "judge-a"
        settings.auto_eval_judge_b_api_base, settings.auto_eval_judge_b_api_key, settings.auto_eval_judge_b_model = "https://b.test/v1/chat/completions", "b-key", "judge-b"
        try:
            providers = build_configured_judge_providers()
            self.assertEqual([(name, provider.model_id) for name, provider in providers], [("judge_a", "openai-compatible:judge-a"), ("judge_b", "openai-compatible:judge-b")])
        finally:
            settings.auto_eval_judge_providers = original["providers"]
            settings.auto_eval_judge_a_api_base, settings.auto_eval_judge_a_api_key, settings.auto_eval_judge_a_model = original["a_url"], original["a_key"], original["a_model"]
            settings.auto_eval_judge_b_api_base, settings.auto_eval_judge_b_api_key, settings.auto_eval_judge_b_model = original["b_url"], original["b_key"], original["b_model"]

    def test_second_judge_can_reuse_only_the_configured_provider_credentials(self):
        from services import training_judge_service

        settings = training_judge_service.settings
        original = (settings.auto_eval_judge_providers, settings.auto_eval_judge_b_api_base, settings.auto_eval_judge_b_api_key, settings.auto_eval_judge_b_model)
        settings.auto_eval_judge_providers = "judge_b"
        settings.auto_eval_judge_b_api_base = ""
        settings.auto_eval_judge_b_api_key = ""
        settings.auto_eval_judge_b_model = "judge-b"
        try:
            provider = build_configured_judge_providers()[0][1]
            self.assertTrue(provider.available)
            self.assertEqual(provider.model_id, "openai-compatible:judge-b")
        finally:
            settings.auto_eval_judge_providers, settings.auto_eval_judge_b_api_base, settings.auto_eval_judge_b_api_key, settings.auto_eval_judge_b_model = original

    def test_approved_export_uses_only_sanitized_training_fields(self):
        label = type("Label", (), {"id": 8, "label": "auto_gold_candidate", "approval_batch": "calibrated", "approval_source": "calibrated_auto", "confidence": 0.95, "rule_version": "v1"})()
        run = type("Run", (), {"id": 9, "response_json": '{"itinerary":{"summary":"ok","itinerary":[]}}', "generation_source": "llm", "validation_status": "valid", "generator_model": "teacher"})()
        scenario = type("Scenario", (), {"request_json": '{"destination":"杭州","days":1,"budget":500,"preferences":[]}', "matrix_version": "matrix-v1"})()
        sample = build_auto_sft_sample(label, run, scenario)
        self.assertEqual(sample["id"], "auto-run-9")
        self.assertEqual(sample["quality_label"], "gold")
        self.assertNotIn("user_id", str(sample))
        self.assertEqual(sample["metadata"]["approval_batch"], "calibrated")
        self.assertEqual(sample["metadata"]["approval_source"], "calibrated_auto")


if __name__ == "__main__":
    unittest.main()
