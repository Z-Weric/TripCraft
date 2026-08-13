"""Validate model narrative and merge it onto immutable planner facts."""

from typing import Any

from pydantic import ValidationError

from schemas.itinerary import ItineraryNarrative
from schemas.planning import PlanningOutcome


def validate_narrative(
    payload: Any,
    outcome: PlanningOutcome,
) -> tuple[ItineraryNarrative | None, list[str]]:
    try:
        narrative = ItineraryNarrative.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return None, errors

    planned_days = outcome.itinerary.itinerary
    if len(narrative.days) != len(planned_days):
        return None, ["days: 模型返回的天数与规划器不一致"]

    errors: list[str] = []
    for index, (narrative_day, planned_day) in enumerate(zip(narrative.days, planned_days)):
        if narrative_day.day != planned_day.day:
            errors.append(f"days.{index}.day: 必须为 {planned_day.day}")
        narrative_ids = [item.poi_id for item in narrative_day.items]
        planned_ids = [item.poi_id for item in planned_day.items]
        if narrative_ids != planned_ids:
            errors.append(
                f"days.{index}.items: poi_id 顺序必须为 {planned_ids}，实际为 {narrative_ids}"
            )
    return (narrative, []) if not errors else (None, errors)


def merge_narrative(
    outcome: PlanningOutcome,
    narrative: ItineraryNarrative | None,
) -> dict[str, Any]:
    """Only copy allow-listed prose fields; every fact remains planner-owned."""
    itinerary = outcome.itinerary.model_dump()
    if narrative is None:
        return itinerary

    itinerary["summary"] = narrative.summary
    for target_day, source_day in zip(itinerary["itinerary"], narrative.days):
        target_day["transport_advice"] = source_day.transport_advice
        narrative_by_id = {item.poi_id: item for item in source_day.items}
        for target_item in target_day["items"]:
            source_item = narrative_by_id[target_item["poi_id"]]
            target_item["note"] = source_item.note
            target_item["reason"] = source_item.reason
    return itinerary
