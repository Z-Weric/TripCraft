"""Deterministic POI scoring, budget control, and route planning."""

import math
from collections.abc import Iterable

from schemas.planning import (
    CandidatePoi,
    PlannedDay,
    PlannedItem,
    PlannedItinerary,
    PlanningOutcome,
    PlanningReason,
    PlanningRequest,
)


PREFERENCE_CATEGORIES = {
    "自然风光": {"自然风光"},
    "美食": {"美食"},
    "历史文化": {"历史文化"},
    "亲子": {"自然风光", "历史文化", "亲子"},
    "购物": {"购物"},
}

TIME_SLOTS = (
    ("09:00-12:00", ("自然风光", "历史文化", "亲子")),
    ("12:00-13:30", ("美食",)),
    ("14:00-16:00", ("购物", "自然风光", "历史文化", "亲子")),
)
MAX_ROUTE_DISTANCE_KM = 50


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def transport_for_distance(distance_km: float) -> tuple[str, float]:
    if distance_km <= 0:
        return "步行出发", 0
    if distance_km < 3:
        return f"步行约{distance_km:.1f}km", 0
    if distance_km < 15:
        return f"公交/地铁约{distance_km:.1f}km，约10元", 10
    if distance_km < 40:
        return f"打车约{distance_km:.1f}km，约40元", 40
    return f"自驾/大巴约{distance_km:.0f}km，约80元", 80


def _preference_categories(preferences: Iterable[str]) -> set[str]:
    categories: set[str] = set()
    for preference in preferences:
        categories.update(PREFERENCE_CATEGORIES.get(preference, {preference}))
    return categories


def _score_candidate(
    poi: CandidatePoi,
    preferred_categories: set[str],
    favorite_ids: set[int],
) -> PlanningReason:
    retrieval_bonus = max(0.0, poi.retrieval_score)
    preference_bonus = 2.0 if poi.category in preferred_categories else 0.0
    favorite_bonus = 1.0 if poi.id in favorite_ids else 0.0
    labels: list[str] = []
    if preference_bonus:
        labels.append("匹配偏好")
    if favorite_bonus:
        labels.append("用户收藏")
    if poi.rating >= 4.5:
        labels.append("高评分")
    return PlanningReason(
        poi_id=poi.id,
        base_rating=poi.rating,
        retrieval_bonus=retrieval_bonus,
        preference_bonus=preference_bonus,
        favorite_bonus=favorite_bonus,
        total_score=poi.rating + retrieval_bonus + preference_bonus + favorite_bonus,
        labels=labels,
    )


def _deduplicate_candidates(candidates: list[CandidatePoi]) -> list[CandidatePoi]:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.rating,
            -candidate.retrieval_score,
            candidate.cost,
            candidate.id,
            candidate.name,
        ),
    )
    unique: list[CandidatePoi] = []
    used_ids: set[int] = set()
    used_names: set[str] = set()
    for candidate in ordered:
        normalized_name = candidate.name.strip().casefold()
        if candidate.id in used_ids or normalized_name in used_names:
            continue
        unique.append(candidate)
        used_ids.add(candidate.id)
        used_names.add(normalized_name)
    return unique


def _minimum_reserved_cost(
    candidates: list[CandidatePoi],
    used_ids: set[int],
    excluded_id: int,
    remaining_days: int,
) -> float:
    if remaining_days <= 0:
        return 0.0
    costs = sorted(
        candidate.cost
        for candidate in candidates
        if candidate.id not in used_ids and candidate.id != excluded_id
    )
    if len(costs) < remaining_days:
        return math.inf
    return sum(costs[:remaining_days])


def plan_itinerary(request: PlanningRequest) -> PlanningOutcome:
    """Produce a stable itinerary without calling an LLM or external service."""
    excluded_ids = set(request.excluded_poi_ids)
    candidates = [
        candidate
        for candidate in _deduplicate_candidates(request.candidates)
        if candidate.id not in excluded_ids
    ]
    preferred_categories = _preference_categories(request.preferences)
    favorite_ids = set(request.favorite_poi_ids)
    reason_by_id = {
        candidate.id: _score_candidate(candidate, preferred_categories, favorite_ids)
        for candidate in candidates
    }
    candidates.sort(
        key=lambda candidate: (
            -reason_by_id[candidate.id].total_score,
            candidate.cost,
            candidate.id,
            candidate.name,
        )
    )

    required_count = request.days * len(TIME_SLOTS)
    warnings: list[str] = []
    if len(candidates) < required_count:
        warnings.append(f"候选景点不足：需要{required_count}个，实际{len(candidates)}个")

    used_ids: set[int] = set()
    days: list[PlannedDay] = []
    total_cost = 0.0

    for day_index in range(request.days):
        day_items: list[PlannedItem] = []
        day_cost = 0.0
        previous: CandidatePoi | None = None

        for time_slot, slot_categories in TIME_SLOTS:
            available = [candidate for candidate in candidates if candidate.id not in used_ids]
            if not available:
                break

            ranked: list[tuple[bool, bool, bool, int, float, float, float, int, CandidatePoi, str]] = []
            for candidate in available:
                distance = (
                    haversine(previous.lat, previous.lng, candidate.lat, candidate.lng)
                    if previous is not None
                    else 0.0
                )
                transport_text, transport_cost = transport_for_distance(distance)
                incremental_cost = candidate.cost + (transport_cost if previous is not None else 0)
                remaining_days = request.days - day_index - 1
                reserved_cost = _minimum_reserved_cost(
                    candidates,
                    used_ids,
                    candidate.id,
                    remaining_days,
                )
                affordable = (
                    total_cost + day_cost + incremental_cost + reserved_cost
                    <= request.budget
                )
                route_valid = previous is None or distance <= MAX_ROUTE_DISTANCE_KM
                nearby_count = 1 + sum(
                    1
                    for other in available
                    if other.id != candidate.id
                    and haversine(candidate.lat, candidate.lng, other.lat, other.lng)
                    <= MAX_ROUTE_DISTANCE_KM
                )
                cluster_viable = nearby_count >= len(TIME_SLOTS)
                slot_bonus = 0.75 if candidate.category in slot_categories else 0.0
                route_penalty = min(distance, 100) * 0.02
                effective_score = reason_by_id[candidate.id].total_score + slot_bonus - route_penalty
                ranked.append(
                    (
                        affordable,
                        route_valid,
                        cluster_viable,
                        nearby_count,
                        effective_score,
                        -incremental_cost,
                        -distance,
                        -candidate.id,
                        candidate,
                        transport_text,
                    )
                )

            affordable_candidates = [entry for entry in ranked if entry[0] and entry[1]]
            if affordable_candidates:
                chosen = max(affordable_candidates, key=lambda entry: entry[:8])
            else:
                warning = (
                    f"第{day_index + 1}天没有距离小于{MAX_ROUTE_DISTANCE_KM}km的后续景点"
                    if day_items and not any(entry[1] for entry in ranked)
                    else (
                        f"第{day_index + 1}天因预算不足提前结束安排"
                        if day_items
                        else f"预算不足以安排第{day_index + 1}天景点"
                    )
                )
                warnings.append(warning)
                break

            candidate = chosen[8]
            transport_text = chosen[9]
            distance = (
                haversine(previous.lat, previous.lng, candidate.lat, candidate.lng)
                if previous is not None
                else 0.0
            )
            _, transport_cost = transport_for_distance(distance)
            item_increment = candidate.cost + (transport_cost if previous is not None else 0)
            day_cost += item_increment
            used_ids.add(candidate.id)
            day_items.append(
                PlannedItem(
                    time=time_slot,
                    spot=candidate.name,
                    poi_id=candidate.id,
                    category=candidate.category,
                    duration=candidate.duration or "2h",
                    cost=candidate.cost,
                    lat=candidate.lat,
                    lng=candidate.lng,
                    note=candidate.note,
                    transport_from_prev=transport_text,
                )
            )
            previous = candidate

        route = " → ".join(item.spot for item in day_items)
        days.append(
            PlannedDay(
                day=day_index + 1,
                items=day_items,
                transport=f"路线: {route}" if route else "暂无安排",
                day_cost=day_cost,
            )
        )
        total_cost += day_cost

    preference_text = "、".join(request.preferences) if request.preferences else "综合"
    selected_ids = {item.poi_id for day in days for item in day.items}
    return PlanningOutcome(
        itinerary=PlannedItinerary(
            destination=request.destination,
            days=request.days,
            itinerary=days,
            total_cost=total_cost,
            summary=f"{request.days}天{request.destination}{preference_text}之旅",
        ),
        reasons=[reason_by_id[candidate.id] for candidate in candidates if candidate.id in selected_ids],
        warnings=list(dict.fromkeys(warnings)),
        candidate_count=len(candidates),
        required_count=required_count,
    )
