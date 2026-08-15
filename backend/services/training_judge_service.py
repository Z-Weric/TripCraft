"""Offline multi-model judging for synthetic training-data candidates.

This service never selects POIs or changes planner facts. It only scores whether the
allow-listed narrative is consistent, useful, and aligned with the supplied fact pack.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from config import settings
from services.llm_provider import LLMProvider, OpenAICompatibleProvider, ProviderError


RULE_VERSION = "auto-eval-v1"
RUBRIC_FIELDS = ("fact_consistency", "preference_match", "readability", "actionability")
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [*RUBRIC_FIELDS, "unsupported_claims", "error_codes", "recommendation", "confidence"],
    "properties": {
        **{field: {"type": "integer", "minimum": 1, "maximum": 5} for field in RUBRIC_FIELDS},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "error_codes": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "recommendation": {"type": "string", "enum": ["accept", "reject"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


@dataclass(frozen=True)
class JudgeOutcome:
    provider: str
    model: str
    rubric: dict[str, Any] | None
    prompt_hash: str
    latency_ms: int | None
    error_message: str | None = None


@dataclass(frozen=True)
class AutoLabelDecision:
    label: str
    confidence: float
    rule_version: str
    hard_errors: list[str]
    judge_outcomes: list[JudgeOutcome]

    def as_record(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "rule_version": self.rule_version,
            "hard_errors": self.hard_errors,
            "judge_outcomes": [asdict(item) for item in self.judge_outcomes],
        }


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_configured_judge_providers() -> list[tuple[str, LLMProvider]]:
    """Build named judge profiles without reusing the generation model configuration."""
    from services.llm_service import build_provider

    profile_values = {
        "judge_a": (
            settings.auto_eval_judge_a_api_base,
            settings.auto_eval_judge_a_api_key,
            settings.auto_eval_judge_a_model,
        ),
        "judge_b": (
            settings.auto_eval_judge_b_api_base,
            settings.auto_eval_judge_b_api_key,
            settings.auto_eval_judge_b_model,
        ),
    }
    providers: list[tuple[str, LLMProvider]] = []
    for name in dict.fromkeys(item.strip().lower() for item in settings.auto_eval_judge_providers.split(",") if item.strip()):
        if name in profile_values:
            api_base, api_key, model = profile_values[name]
            provider: LLMProvider = OpenAICompatibleProvider(api_base, api_key, model, timeout=settings.auto_eval_timeout)
        else:
            provider = build_provider(name)
        providers.append((name, provider))
    return providers


def narrative_from_itinerary(itinerary: dict[str, Any]) -> dict[str, Any]:
    """Extract only fields a TripCraft narrative model is permitted to write."""
    return {
        "summary": str(itinerary.get("summary") or ""),
        "days": [
            {
                "day": day.get("day"),
                "transport_advice": str(day.get("transport_advice") or day.get("transport") or ""),
                "items": [
                    {
                        "poi_id": item.get("poi_id"),
                        "note": str(item.get("note") or ""),
                        "reason": str(item.get("reason") or ""),
                    }
                    for item in day.get("items", [])
                    if isinstance(item, dict)
                ],
            }
            for day in itinerary.get("itinerary", [])
            if isinstance(day, dict)
        ],
    }


def fact_pack_from_itinerary(request: dict[str, Any], itinerary: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the minimum public planner facts needed by an offline judge."""
    immutable_item_fields = (
        "poi_id", "spot", "category", "time", "lat", "lng", "cost", "duration",
        "distance_from_previous_km", "transport_cost", "recommendation_labels",
    )
    return {
        "destination": request.get("destination"),
        "days": request.get("days"),
        "budget": request.get("budget"),
        "preferences": request.get("preferences", []),
        "total_cost": itinerary.get("total_cost"),
        "itinerary": [
            {
                "day": day.get("day"),
                "day_cost": day.get("day_cost"),
                "items": [{field: item[field] for field in immutable_item_fields if field in item} for item in day.get("items", []) if isinstance(item, dict)],
            }
            for day in itinerary.get("itinerary", [])
            if isinstance(day, dict)
        ],
    }


def hard_gate(response: dict[str, Any], request: dict[str, Any]) -> list[str]:
    """Return deterministic failure codes; an LLM cannot override any of them."""
    errors: list[str] = []
    itinerary = response.get("itinerary")
    verification = response.get("verification")
    if not isinstance(itinerary, dict) or itinerary.get("error"):
        return ["GENERATION_ERROR"]
    if not isinstance(verification, dict) or not verification.get("overall_valid"):
        errors.append("BUSINESS_RULE_FAILED")
    if response.get("generation_source") not in {"llm", "llm_repaired"}:
        errors.append("NON_LLM_GENERATION")
    if response.get("validation_status") not in {"valid", "repaired"}:
        errors.append("NARRATIVE_VALIDATION_FAILED")
    if response.get("validation_status") == "repaired":
        errors.append("REPAIR_REQUIRED")
    days = itinerary.get("itinerary")
    if not isinstance(days, list) or len(days) != request.get("days"):
        errors.append("DAY_COUNT_MISMATCH")
    for day in days or []:
        if not isinstance(day, dict) or not isinstance(day.get("day"), int):
            errors.append("INVALID_DAY_REFERENCE")
            break
        for item in day.get("items", []):
            if not isinstance(item, dict) or not isinstance(item.get("poi_id"), int) or item["poi_id"] <= 0:
                errors.append("INVALID_POI_REFERENCE")
                break
    return sorted(set(errors))


def _judge_prompt(fact_pack: dict[str, Any], narrative: dict[str, Any]) -> str:
    return f"""You are an offline quality judge for TripCraft.
Evaluate only the narrative against the supplied immutable fact pack. Do not choose POIs or change route facts.
Reject factual claims not supported by the fact pack, including invented opening times, prices, transport durations, or attractions.
Score fact consistency, preference match, readability, and actionability from 1 to 5.
Return only JSON matching the provided schema.

Fact pack:
{json.dumps(fact_pack, ensure_ascii=False, separators=(',', ':'))}

Narrative:
{json.dumps(narrative, ensure_ascii=False, separators=(',', ':'))}"""


def _normalize_rubric(payload: dict[str, Any]) -> dict[str, Any]:
    for field in RUBRIC_FIELDS:
        if not isinstance(payload.get(field), int) or not 1 <= payload[field] <= 5:
            raise ValueError(f"invalid rubric field: {field}")
    if payload.get("recommendation") not in {"accept", "reject"}:
        raise ValueError("invalid recommendation")
    if not isinstance(payload.get("confidence"), (int, float)) or not 0 <= payload["confidence"] <= 1:
        raise ValueError("invalid confidence")
    for field in ("unsupported_claims", "error_codes"):
        if not isinstance(payload.get(field), list) or not all(isinstance(value, str) for value in payload[field]):
            raise ValueError(f"invalid {field}")
    return {
        **{field: payload[field] for field in RUBRIC_FIELDS},
        "unsupported_claims": payload["unsupported_claims"][:20],
        "error_codes": payload["error_codes"][:20],
        "recommendation": payload["recommendation"],
        "confidence": float(payload["confidence"]),
    }


async def judge_with_provider(provider_name: str, provider: LLMProvider, fact_pack: dict[str, Any], narrative: dict[str, Any]) -> JudgeOutcome:
    prompt = _judge_prompt(fact_pack, narrative)
    prompt_hash = _canonical_hash({"rule_version": RULE_VERSION, "prompt": prompt})
    started = time.perf_counter()
    try:
        payload = await provider.generate_json(
            [{"role": "system", "content": prompt}],
            JUDGE_SCHEMA,
            temperature=0,
            max_tokens=800,
        )
        return JudgeOutcome(provider_name, provider.model_id, _normalize_rubric(payload), prompt_hash, round((time.perf_counter() - started) * 1000))
    except (ProviderError, ValueError, TypeError) as exc:
        return JudgeOutcome(provider_name, provider.model_id, None, prompt_hash, round((time.perf_counter() - started) * 1000), str(exc))


def aggregate_judgments(hard_errors: list[str], outcomes: list[JudgeOutcome], accept_confidence: float | None = None) -> AutoLabelDecision:
    threshold = settings.auto_eval_accept_confidence if accept_confidence is None else accept_confidence
    blocking_errors = [error for error in hard_errors if error != "REPAIR_REQUIRED"]
    valid = [item.rubric for item in outcomes if item.rubric is not None]
    if blocking_errors:
        return AutoLabelDecision("negative", 0.0, RULE_VERSION, hard_errors, outcomes)
    if len(valid) < 2:
        return AutoLabelDecision("silver", 0.0, RULE_VERSION, hard_errors, outcomes)
    first, second = valid[:2]
    if any(item["recommendation"] != "accept" for item in (first, second)):
        return AutoLabelDecision("negative", 0.0, RULE_VERSION, hard_errors, outcomes)
    if first["unsupported_claims"] or second["unsupported_claims"]:
        return AutoLabelDecision("negative", 0.0, RULE_VERSION, hard_errors, outcomes)
    quality = sum((first[field] + second[field]) / 10 for field in RUBRIC_FIELDS) / len(RUBRIC_FIELDS)
    agreement = 1 - sum(abs(first[field] - second[field]) / 4 for field in RUBRIC_FIELDS) / len(RUBRIC_FIELDS)
    judge_confidence = (first["confidence"] + second["confidence"]) / 2
    confidence = round(0.45 * quality + 0.30 * agreement + 0.25 * judge_confidence, 4)
    all_core_scores_high = all(item[field] >= 4 for item in (first, second) for field in RUBRIC_FIELDS)
    if not hard_errors and all_core_scores_high and confidence >= threshold:
        label = "auto_gold_candidate"
    else:
        label = "silver"
    return AutoLabelDecision(label, confidence, RULE_VERSION, hard_errors, outcomes)


async def judge_generation(
    response: dict[str, Any],
    request: dict[str, Any],
    providers: list[tuple[str, LLMProvider]],
) -> AutoLabelDecision:
    """Run independent judges after deterministic validation; never silently accept missing judges."""
    errors = hard_gate(response, request)
    if any(error != "REPAIR_REQUIRED" for error in errors):
        return aggregate_judgments(errors, [])
    itinerary = response.get("itinerary") if isinstance(response.get("itinerary"), dict) else {}
    fact_pack = fact_pack_from_itinerary(request, itinerary)
    narrative = narrative_from_itinerary(itinerary)
    generator = str(response.get("model_version") or "")
    independent = [(name, provider) for name, provider in providers if provider.available and provider.model_id != generator]
    semaphore = asyncio.Semaphore(settings.auto_eval_max_concurrency)

    async def run_one(name: str, provider: LLMProvider) -> JudgeOutcome:
        async with semaphore:
            return await judge_with_provider(name, provider, fact_pack, narrative)

    outcomes = await asyncio.gather(*(run_one(name, provider) for name, provider in independent[:2]))
    return aggregate_judgments(errors, list(outcomes))
