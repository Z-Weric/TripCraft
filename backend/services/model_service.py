"""Orchestrate deterministic planning and allow-listed LLM narrative."""

from dataclasses import dataclass
import json
import time
from typing import Any

from schemas.itinerary import ItineraryGenerationOutcome, ItineraryNarrative
from schemas.planning import PlanningRequest
from services.fact_pack_service import build_fact_pack
from services.planner_service import plan_itinerary
from services.response_validation_service import merge_narrative, validate_narrative
from services.llm_provider import ProviderResponseError, ProviderUnavailableError
from utils.logger import logger


@dataclass(frozen=True)
class ModelCallResult:
    payload: Any | None
    error: str | None = None
    available: bool = True
    model_id: str = "none"


def _build_prompt(
    fact_pack: dict[str, Any],
    repair_errors: list[str] | None = None,
    previous_payload: Any | None = None,
) -> str:
    repair_section = ""
    if repair_errors:
        repair_section = f"""
上一次输出未通过校验，请只修复格式和引用错误，不得改变事实包：
{repair_errors}
上一次输出：
{previous_payload}
"""
    return f"""你是 TripCraft 行程文案生成器。事实包已由系统规划器确定。

你只能填写 summary、transport_advice、note、reason，并原样引用 day 与 poi_id。
禁止输出景点名称、坐标、费用、时长、排序或任何 Schema 外字段。

事实包：
{fact_pack}
{repair_section}
只返回 JSON，不要使用 Markdown 代码块。"""


async def _llm_generate(
    fact_pack: dict[str, Any],
    repair_errors: list[str] | None = None,
    previous_payload: Any | None = None,
) -> ModelCallResult:
    from services.model_router import route_model_request

    route = route_model_request(
        "itinerary",
        destination=str(fact_pack.get("destination", "")),
        days=int(fact_pack.get("days", 0)),
        preferences=fact_pack.get("preferences", []),
        repair_errors=repair_errors,
    )
    providers = [route.primary]
    if route.fallback_allowed:
        providers.append(route.fallback)
    if not any(provider.available for provider in providers):
        return ModelCallResult(
            payload=None,
            error="LLM Provider 未配置",
            available=False,
        )

    errors: list[str] = []
    for index, provider in enumerate(providers):
        if not provider.available:
            continue
        started = time.perf_counter()
        fallback_reason = "primary_unavailable" if index else None
        try:
            payload = await provider.generate_json(
                messages=[
                    {
                        "role": "system",
                        "content": _build_prompt(fact_pack, repair_errors, previous_payload),
                    }
                ],
                schema=ItineraryNarrative.model_json_schema(),
                temperature=0.2,
                max_tokens=2000,
            )
            logger.info(
                "模型文案生成完成",
                extra={
                    "provider": provider.model_id.split(":", 1)[0],
                    "model": provider.model_id,
                    "latency": round((time.perf_counter() - started) * 1000),
                    "tokens": max(1, len(json.dumps(payload, ensure_ascii=False)) // 4),
                    "route_reason": route.reason,
                    "fallback_reason": fallback_reason,
                    "cost": 0 if provider.model_id.startswith("ollama:") else None,
                },
            )
            return ModelCallResult(payload=payload, model_id=provider.model_id)
        except ProviderUnavailableError as exc:
            errors.append(str(exc))
            logger.warning(
                "模型 Provider 不可用",
                extra={
                    "provider": provider.model_id.split(":", 1)[0],
                    "model": provider.model_id,
                    "latency": round((time.perf_counter() - started) * 1000),
                    "route_reason": route.reason,
                    "fallback_reason": str(exc),
                },
            )
        except ProviderResponseError as exc:
            logger.warning("模型文案响应不合法: %s", exc)
            return ModelCallResult(payload=None, error=str(exc))
    return ModelCallResult(payload=None, error="；".join(errors), available=False)


def _with_planning_metadata(itinerary: dict[str, Any], warnings: list[str], candidate_count: int, required_count: int) -> dict[str, Any]:
    itinerary["planning_warnings"] = warnings
    itinerary["candidate_count"] = candidate_count
    itinerary["required_candidate_count"] = required_count
    return itinerary


def _fallback(request: PlanningRequest, reason: str) -> ItineraryGenerationOutcome:
    outcome = plan_itinerary(request)
    itinerary = merge_narrative(outcome, None)
    return ItineraryGenerationOutcome(
        itinerary=_with_planning_metadata(
            itinerary,
            outcome.warnings,
            outcome.candidate_count,
            outcome.required_count,
        ),
        generation_source="planner",
        validation_status="fallback",
        fallback_reason=reason,
        model_version="none",
    )


async def generate_itinerary(
    destination: str,
    days: int,
    budget: int,
    preferences: list[str],
    pois: list[dict[str, Any]],
    favorite_poi_ids: list[int] | None = None,
) -> ItineraryGenerationOutcome:
    """Plan immutable facts first, then request and validate optional prose."""
    request = PlanningRequest(
        destination=destination,
        days=days,
        budget=budget,
        preferences=preferences,
        favorite_poi_ids=favorite_poi_ids or [],
        candidates=pois,
    )
    outcome = plan_itinerary(request)
    for warning in outcome.warnings:
        logger.warning("规划器降级: %s", warning)

    fact_pack = build_fact_pack(request, outcome)
    first_call = await _llm_generate(fact_pack)
    if not first_call.available:
        return _fallback(request, first_call.error or "LLM Provider 不可用")

    narrative, errors = validate_narrative(first_call.payload, outcome)
    if narrative is not None:
        return ItineraryGenerationOutcome(
            itinerary=_with_planning_metadata(
                merge_narrative(outcome, narrative),
                outcome.warnings,
                outcome.candidate_count,
                outcome.required_count,
            ),
            generation_source="llm",
            validation_status="valid",
            model_version=first_call.model_id,
        )

    repair_errors = errors or [first_call.error or "模型输出不可解析"]
    repair_call = await _llm_generate(fact_pack, repair_errors, first_call.payload)
    repaired_narrative, repaired_errors = validate_narrative(repair_call.payload, outcome)
    if repaired_narrative is not None:
        return ItineraryGenerationOutcome(
            itinerary=_with_planning_metadata(
                merge_narrative(outcome, repaired_narrative),
                outcome.warnings,
                outcome.candidate_count,
                outcome.required_count,
            ),
            generation_source="llm_repaired",
            validation_status="repaired",
            model_version=repair_call.model_id,
        )

    reason_parts = repair_errors + repaired_errors
    if repair_call.error:
        reason_parts.append(repair_call.error)
    reason = "；".join(dict.fromkeys(reason_parts)) or "模型修复失败"
    return _fallback(request, reason)
