"""Bounded narrative-only repair for silver training candidates."""

import hashlib
import json
from typing import Any

from config import settings
from schemas.itinerary import ItineraryNarrative
from services.llm_provider import LLMProvider, ProviderError
from services.training_judge_service import fact_pack_from_itinerary, narrative_from_itinerary


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_repair_prompt(
    request: dict[str, Any],
    itinerary: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    fact_pack = fact_pack_from_itinerary(request, itinerary)
    narrative = narrative_from_itinerary(itinerary)
    return f"""你是 TripCraft 的文案修复器。只修复已有行程的允许文案字段，不得重新规划。

事实包是不可变事实。你只能输出 summary、transport_advice、note、reason，并原样保留 day、poi_id 及其顺序。
不得新增事实包没有直接支持的活动、开放时间、排队、天气季节、评分、热门程度、安全等级、历史细节、价格或服务承诺。
删除无法由事实包或给定证据直接支持的声明；需要保留但无法确认时，改成中性的行程衔接表达。
不要修改 POI、坐标、费用、时长、时间、路线或任何 Schema 外字段。

用户请求：
{json.dumps(request, ensure_ascii=False, separators=(',', ':'))}

不可变事实包：
{json.dumps(fact_pack, ensure_ascii=False, separators=(',', ':'))}

原始文案：
{json.dumps(narrative, ensure_ascii=False, separators=(',', ':'))}

裁判反馈（只用于定位要删除或改写的声明）：
{json.dumps(decision, ensure_ascii=False, separators=(',', ':'))}

只返回符合 schema 的 JSON，不要 Markdown。"""


def _validate_structure(payload: Any, original: dict[str, Any]) -> ItineraryNarrative:
    narrative = ItineraryNarrative.model_validate(payload)
    original_days = original.get("days", [])
    if len(narrative.days) != len(original_days):
        raise ValueError("修复后的天数不能改变")
    for repaired_day, original_day in zip(narrative.days, original_days):
        if repaired_day.day != original_day.get("day"):
            raise ValueError("修复后的 day 不能改变")
        expected_ids = [item.get("poi_id") for item in original_day.get("items", [])]
        actual_ids = [item.poi_id for item in repaired_day.items]
        if actual_ids != expected_ids:
            raise ValueError("修复后的 poi_id 顺序不能改变")
    return narrative


def merge_repaired_narrative(itinerary: dict[str, Any], payload: Any) -> dict[str, Any]:
    original = narrative_from_itinerary(itinerary)
    narrative = _validate_structure(payload, original)
    repaired = json.loads(json.dumps(itinerary, ensure_ascii=False))
    repaired["summary"] = narrative.summary
    for target_day, source_day in zip(repaired.get("itinerary", []), narrative.days):
        target_day["transport_advice"] = source_day.transport_advice
        by_id = {item.poi_id: item for item in source_day.items}
        for target_item in target_day.get("items", []):
            source_item = by_id[target_item["poi_id"]]
            target_item["note"] = source_item.note
            target_item["reason"] = source_item.reason
    return repaired


async def repair_narrative(
    provider: LLMProvider,
    request: dict[str, Any],
    itinerary: dict[str, Any],
    decision: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str]:
    prompt = build_repair_prompt(request, itinerary, decision)
    prompt_hash = _hash(prompt)
    try:
        payload = await provider.generate_json(
            [{"role": "system", "content": prompt}],
            ItineraryNarrative.model_json_schema(),
            temperature=0.1,
            max_tokens=2000,
        )
        return merge_repaired_narrative(itinerary, payload), None, prompt_hash
    except (ProviderError, ValueError, TypeError) as exc:
        return None, str(exc), prompt_hash


def build_repair_provider() -> LLMProvider:
    from services.llm_service import build_provider

    return build_provider(settings.auto_eval_repair_provider)
