"""Offline multi-model judging for synthetic training-data candidates.

This service never selects POIs or changes planner facts. It only scores whether the
allow-listed narrative is consistent, useful, and aligned with the supplied fact pack.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from config import settings
from services.llm_provider import LLMProvider, OpenAICompatibleProvider, ProviderError


RULE_VERSION = "auto-eval-v3-relaxed-unknowns"
RUBRIC_FIELDS = ("fact_consistency", "preference_match", "readability", "actionability")
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [*RUBRIC_FIELDS, "contradicted_claims", "unverified_claims", "error_codes", "recommendation", "confidence"],
    "properties": {
        **{field: {"type": "integer", "minimum": 1, "maximum": 5} for field in RUBRIC_FIELDS},
        "contradicted_claims": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "unverified_claims": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "error_codes": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "recommendation": {"type": "string", "enum": ["accept", "reject"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

EVIDENCE_DEBATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claim_verdicts"],
    "properties": {
        "claim_verdicts": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim_hash", "verdict", "evidence_urls"],
                "properties": {
                    "claim_hash": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["supported", "refuted", "unknown"]},
                    "evidence_urls": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                },
            },
        },
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
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def as_record(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "rule_version": self.rule_version,
            "hard_errors": self.hard_errors,
            "judge_outcomes": [asdict(item) for item in self.judge_outcomes],
            "evidence": self.evidence,
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
            settings.auto_eval_judge_b_api_base or settings.llm_api_base,
            settings.auto_eval_judge_b_api_key or settings.siliconflow_api_key,
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
Classify factual statements precisely:
- Put a claim in contradicted_claims only when it directly conflicts with a supplied fact, such as a wrong POI, price, duration, route order, coordinate, or transport cost.
- Put a claim in unverified_claims when it is absent from the fact pack. Absence is not evidence that the claim is false. Do not put subjective language or generic travel advice there.
- Do not reject a narrative merely because it has unverified claims. Reject only for direct contradictions or prose that is unusable because it is empty, incoherent, or materially fails the request.
For automatic training promotion, unverified_claims are allowed when they are not contradicted by the fact pack or evidence. Unknown is not false.
Score fact consistency, preference match, readability, and actionability from 1 to 5.
Return only JSON matching the provided schema.

Fact pack:
{json.dumps(fact_pack, ensure_ascii=False, separators=(',', ':'))}

Narrative:
{json.dumps(narrative, ensure_ascii=False, separators=(',', ':'))}"""


def _debate_prompt(
    fact_pack: dict[str, Any],
    narrative: dict[str, Any],
    opposing_rubric: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> str:
    return f"""You are the evidence-review round of an offline TripCraft judge debate.
Review the other judge's initial assessment, the immutable fact pack, and the citation bundles.
For each claim hash, return supported only when the cited snippets directly support it, and refuted only when they directly refute it.
Use unknown for absent, ambiguous, weak, or conflicting evidence. Do not treat fact-pack absence as refutation.
Every supported/refuted verdict must include one or more URLs from the provided citation bundles.
Return only JSON matching the provided schema.

Fact pack:
{json.dumps(fact_pack, ensure_ascii=False, separators=(',', ':'))}

Narrative:
{json.dumps(narrative, ensure_ascii=False, separators=(',', ':'))}

Other judge initial assessment:
{json.dumps(opposing_rubric, ensure_ascii=False, separators=(',', ':'))}

Citation bundles:
{json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))}"""


def _normalize_rubric(payload: dict[str, Any]) -> dict[str, Any]:
    for field in RUBRIC_FIELDS:
        if not isinstance(payload.get(field), int) or not 1 <= payload[field] <= 5:
            raise ValueError(f"invalid rubric field: {field}")
    if payload.get("recommendation") not in {"accept", "reject"}:
        raise ValueError("invalid recommendation")
    if not isinstance(payload.get("confidence"), (int, float)) or not 0 <= payload["confidence"] <= 1:
        raise ValueError("invalid confidence")
    for field in ("contradicted_claims", "unverified_claims", "error_codes"):
        if not isinstance(payload.get(field), list) or not all(isinstance(value, str) for value in payload[field]):
            raise ValueError(f"invalid {field}")
    return {
        **{field: payload[field] for field in RUBRIC_FIELDS},
        "contradicted_claims": payload["contradicted_claims"][:20],
        "unverified_claims": payload["unverified_claims"][:20],
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


async def debate_with_provider(
    provider: LLMProvider,
    fact_pack: dict[str, Any],
    narrative: dict[str, Any],
    opposing_rubric: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        payload = await provider.generate_json(
            [{"role": "system", "content": _debate_prompt(fact_pack, narrative, opposing_rubric, evidence)}],
            EVIDENCE_DEBATE_SCHEMA,
            temperature=0,
            max_tokens=800,
        )
    except (ProviderError, ValueError, TypeError):
        return None
    verdicts = payload.get("claim_verdicts")
    if not isinstance(verdicts, list):
        return None
    normalized = []
    for item in verdicts:
        if not isinstance(item, dict):
            continue
        if item.get("verdict") not in {"supported", "refuted", "unknown"}:
            continue
        if not isinstance(item.get("claim_hash"), str) or not isinstance(item.get("evidence_urls"), list):
            continue
        normalized.append({
            "claim_hash": item["claim_hash"],
            "verdict": item["verdict"],
            "evidence_urls": [url for url in item["evidence_urls"] if isinstance(url, str)][:5],
        })
    return {"claim_verdicts": normalized}


def apply_evidence_consensus(
    outcomes: list[JudgeOutcome],
    reviews: list[dict[str, Any] | None],
    evidence: list[dict[str, Any]],
) -> None:
    """Only a cited, unanimous supported/refuted verdict changes the initial label."""
    by_hash = {item["claim_hash"]: item for item in evidence}
    allowed_urls = {
        evidence_id: {source.get("url") for source in item.get("sources", []) if source.get("url")}
        for evidence_id, item in by_hash.items()
    }
    review_maps = [
        {item["claim_hash"]: item for item in review.get("claim_verdicts", [])}
        for review in reviews
        if review is not None
    ]
    if len(review_maps) != len(outcomes):
        return
    consensus: dict[str, str] = {}
    for evidence_id, item in by_hash.items():
        entries = [review.get(evidence_id) for review in review_maps]
        if any(entry is None for entry in entries):
            consensus[evidence_id] = "unknown"
            continue
        verdicts = {entry["verdict"] for entry in entries}
        citations_valid = all(
            entry["evidence_urls"] and set(entry["evidence_urls"]).issubset(allowed_urls[evidence_id])
            for entry in entries
        )
        consensus[evidence_id] = verdicts.pop() if len(verdicts) == 1 and citations_valid else "unknown"

    for outcome, review in zip(outcomes, reviews):
        if outcome.rubric is None:
            continue
        outcome.rubric["evidence_review"] = review or {"claim_verdicts": []}
        unresolved = []
        contradicted = list(outcome.rubric.get("contradicted_claims", []))
        for claim in outcome.rubric.get("unverified_claims", []):
            evidence_id = next((key for key, item in by_hash.items() if item["claim"] == claim), None)
            verdict = consensus.get(evidence_id, "unknown") if evidence_id else "unknown"
            if verdict == "refuted":
                contradicted.append(f"{claim} [external evidence refuted]")
            elif verdict != "supported":
                unresolved.append(claim)
        outcome.rubric["contradicted_claims"] = list(dict.fromkeys(contradicted))
        outcome.rubric["unverified_claims"] = list(dict.fromkeys(unresolved))


def aggregate_judgments(hard_errors: list[str], outcomes: list[JudgeOutcome], accept_confidence: float | None = None) -> AutoLabelDecision:
    threshold = settings.auto_eval_accept_confidence if accept_confidence is None else accept_confidence
    blocking_errors = [error for error in hard_errors if error != "REPAIR_REQUIRED"]
    valid = [item.rubric for item in outcomes if item.rubric is not None]
    if blocking_errors:
        return AutoLabelDecision("negative", 0.0, RULE_VERSION, hard_errors, outcomes)
    if len(valid) < 2:
        return AutoLabelDecision("silver", 0.0, RULE_VERSION, hard_errors, outcomes)
    first, second = valid[:2]
    if any(item["contradicted_claims"] for item in (first, second)):
        return AutoLabelDecision("negative", 0.0, RULE_VERSION, hard_errors, outcomes)

    # A judge recommendation is useful audit context, but it is not a factual
    # verdict. Providers can reject a plausible statement simply because its
    # source is absent from the compact fact pack. Keep that uncertainty silver
    # unless a deterministic gate or an explicit contradiction proves it wrong.
    quality = sum((first[field] + second[field]) / 10 for field in RUBRIC_FIELDS) / len(RUBRIC_FIELDS)
    agreement = 1 - sum(abs(first[field] - second[field]) / 4 for field in RUBRIC_FIELDS) / len(RUBRIC_FIELDS)
    judge_confidence = (first["confidence"] + second["confidence"]) / 2
    confidence = round(0.45 * quality + 0.30 * agreement + 0.25 * judge_confidence, 4)
    min_core_score = settings.auto_eval_min_core_score
    all_core_scores_high = all(item[field] >= min_core_score for item in (first, second) for field in RUBRIC_FIELDS)
    has_unverified_claims = any(item["unverified_claims"] for item in (first, second))
    unknowns_block = has_unverified_claims and not settings.auto_eval_allow_unverified_claims
    if not blocking_errors and not unknowns_block and all_core_scores_high and confidence >= threshold:
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

    outcomes = list(await asyncio.gather(*(run_one(name, provider) for name, provider in independent[:2])))
    decision = aggregate_judgments(errors, outcomes)
    # A generator must never evaluate itself. If removing it leaves fewer than
    # two independent judges, retain the conservative silver decision and skip
    # evidence debate, which requires an opposing rubric for each judge.
    if len(outcomes) < 2:
        return decision
    claims = [
        claim
        for outcome in outcomes
        if outcome.rubric is not None
        for claim in outcome.rubric.get("unverified_claims", [])
    ]
    if not claims or not settings.auto_eval_evidence_enabled:
        return decision

    from services.evidence_retrieval_service import retrieve_evidence_for_claims

    bundles = await retrieve_evidence_for_claims(str(request.get("destination") or ""), claims)
    evidence = [bundle.as_record() for bundle in bundles]
    if not any(item["sources"] for item in evidence):
        return AutoLabelDecision(decision.label, decision.confidence, decision.rule_version, decision.hard_errors, outcomes, evidence)

    reviews = await asyncio.gather(*(
        debate_with_provider(
            provider,
            fact_pack,
            narrative,
            outcomes[1 - index].rubric or {},
            evidence,
        )
        for index, (_, provider) in enumerate(independent[:2])
    ))
    apply_evidence_consensus(outcomes, list(reviews), evidence)
    resolved = aggregate_judgments(errors, outcomes)
    return AutoLabelDecision(resolved.label, resolved.confidence, resolved.rule_version, resolved.hard_errors, outcomes, evidence)
