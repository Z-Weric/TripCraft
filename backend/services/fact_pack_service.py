"""Build the minimal set of immutable planning facts sent to an LLM."""

from typing import Any

from schemas.planning import PlanningOutcome, PlanningRequest
from services.planner_service import haversine, transport_for_distance


def build_fact_pack(request: PlanningRequest, outcome: PlanningOutcome) -> dict[str, Any]:
    reason_by_id = {reason.poi_id: reason for reason in outcome.reasons}
    days: list[dict[str, Any]] = []
    for day in outcome.itinerary.itinerary:
        items: list[dict[str, Any]] = []
        previous = None
        for order, item in enumerate(day.items, start=1):
            distance_km = 0.0
            transport_cost = 0.0
            if previous is not None:
                distance_km = haversine(previous.lat, previous.lng, item.lat, item.lng)
                _, transport_cost = transport_for_distance(distance_km)
            reason = reason_by_id.get(item.poi_id)
            items.append(
                {
                    "order": order,
                    "time": item.time,
                    "poi_id": item.poi_id,
                    "name": item.spot,
                    "category": item.category,
                    "lat": item.lat,
                    "lng": item.lng,
                    "cost": item.cost,
                    "duration": item.duration,
                    "distance_from_previous_km": round(distance_km, 2),
                    "transport_cost": transport_cost,
                    "recommendation_labels": reason.labels if reason else [],
                }
            )
            previous = item
        days.append({"day": day.day, "day_cost": day.day_cost, "items": items})

    return {
        "destination": request.destination,
        "days": request.days,
        "budget": request.budget,
        "preferences": request.preferences,
        "total_cost": outcome.itinerary.total_cost,
        "itinerary": days,
    }
