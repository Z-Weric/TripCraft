"""Itinerary validation for structure, POI facts, budget, and route quality."""

import math
from numbers import Real
from typing import Any, Literal, TypedDict


REQUIRED_ITINERARY_FIELDS = ("destination", "days", "itinerary", "total_cost")
REQUIRED_DAY_FIELDS = ("day", "items", "day_cost")
REQUIRED_ITEM_FIELDS = ("spot", "lat", "lng", "cost")
MAX_ROUTE_DISTANCE_KM = 50
COORDINATE_TOLERANCE = 0.01
COST_TOLERANCE = 0.01


class SpotVerification(TypedDict):
    valid: bool
    source: Literal["external", "local", "unavailable", "failed"]


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


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _append_error(errors: list[dict[str, Any]], code: str, message: str, path: str = "") -> None:
    error = {"code": code, "message": message}
    if path:
        error["path"] = path
    errors.append(error)


def _matches_local_poi(
    spot_name: str,
    lat: float,
    lng: float,
    known_pois: list[dict[str, Any]],
    poi_id: int | None = None,
) -> bool:
    for poi in known_pois:
        if poi_id and poi.get("id") and poi["id"] != poi_id:
            continue
        if poi.get("name") != spot_name:
            continue
        poi_lat = poi.get("lat")
        poi_lng = poi.get("lng")
        if not _is_number(poi_lat) or not _is_number(poi_lng):
            continue
        if abs(float(poi_lat) - lat) < COORDINATE_TOLERANCE and abs(float(poi_lng) - lng) < COORDINATE_TOLERANCE:
            return True
    return False


def _find_local_poi(
    spot_name: str,
    known_pois: list[dict[str, Any]],
    poi_id: int | None = None,
) -> dict[str, Any] | None:
    for poi in known_pois:
        if poi_id and poi.get("id") and poi["id"] != poi_id:
            continue
        if poi.get("name") == spot_name:
            return poi
    return None


async def _verify_spot_external(spot_name: str, lat: float, lng: float) -> bool | None:
    from services.amap_service import verify_spot

    return await verify_spot(spot_name, lat, lng)


async def verify_spot_poi(
    spot_name: str,
    lat: float,
    lng: float,
    known_pois: list[dict[str, Any]] | None = None,
    poi_id: int | None = None,
    verify_external: bool = True,
) -> SpotVerification:
    """Use AMap when available, otherwise require a local POI match."""
    # Planner-selected POIs carry an immutable local id, name, and coordinates.
    # Treat that exact match as authoritative before an external search, whose
    # coverage or name normalization can otherwise reject known-good facts.
    local_pois = known_pois or []
    if _matches_local_poi(spot_name, lat, lng, local_pois, poi_id):
        return {"valid": True, "source": "local"}

    external_result = await _verify_spot_external(spot_name, lat, lng) if verify_external else None
    if external_result is True:
        return {"valid": True, "source": "external"}
    if external_result is False:
        return {"valid": False, "source": "failed"}
    return {"valid": False, "source": "unavailable"}


def _structure_items(itinerary: Any, errors: list[dict[str, Any]]) -> list[tuple[int, int, dict[str, Any]]]:
    if not isinstance(itinerary, dict):
        _append_error(errors, "INVALID_ITINERARY_TYPE", "行程必须是 JSON 对象")
        return []

    for field in REQUIRED_ITINERARY_FIELDS:
        if field not in itinerary:
            _append_error(errors, "MISSING_FIELD", f"行程缺少字段：{field}", field)

    days = itinerary.get("days")
    if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
        _append_error(errors, "INVALID_DAYS", "days 必须是正整数", "days")

    plans = itinerary.get("itinerary")
    if not isinstance(plans, list):
        _append_error(errors, "INVALID_ITINERARY_DAYS", "itinerary 必须是数组", "itinerary")
        return []
    if isinstance(days, int) and not isinstance(days, bool) and days > 0 and len(plans) != days:
        _append_error(errors, "DAY_COUNT_MISMATCH", "行程天数与 days 不一致", "itinerary")

    all_items: list[tuple[int, int, dict[str, Any]]] = []
    seen_days: set[int] = set()
    for day_index, day in enumerate(plans):
        day_path = f"itinerary[{day_index}]"
        if not isinstance(day, dict):
            _append_error(errors, "INVALID_DAY_TYPE", "每日行程必须是 JSON 对象", day_path)
            continue
        for field in REQUIRED_DAY_FIELDS:
            if field not in day:
                _append_error(errors, "MISSING_FIELD", f"每日行程缺少字段：{field}", f"{day_path}.{field}")

        day_number = day.get("day")
        if not isinstance(day_number, int) or isinstance(day_number, bool) or day_number <= 0:
            _append_error(errors, "INVALID_DAY_NUMBER", "day 必须是正整数", f"{day_path}.day")
        elif day_number in seen_days:
            _append_error(errors, "DUPLICATE_DAY", "行程中出现重复 day", f"{day_path}.day")
        else:
            seen_days.add(day_number)

        items = day.get("items")
        if not isinstance(items, list):
            _append_error(errors, "INVALID_ITEMS", "items 必须是数组", f"{day_path}.items")
            continue
        if not items:
            _append_error(errors, "EMPTY_DAY", "每天至少需要一个景点", f"{day_path}.items")

        for item_index, item in enumerate(items):
            item_path = f"{day_path}.items[{item_index}]"
            if not isinstance(item, dict):
                _append_error(errors, "INVALID_ITEM_TYPE", "景点项目必须是 JSON 对象", item_path)
                continue
            missing = False
            for field in REQUIRED_ITEM_FIELDS:
                if field not in item:
                    missing = True
                    _append_error(errors, "MISSING_FIELD", f"景点缺少字段：{field}", f"{item_path}.{field}")
            if missing:
                continue

            if not isinstance(item.get("spot"), str) or not item["spot"].strip():
                _append_error(errors, "INVALID_SPOT_NAME", "spot 必须是非空字符串", f"{item_path}.spot")
                continue
            if not _is_number(item.get("lat")) or not _is_number(item.get("lng")):
                _append_error(errors, "INVALID_COORDINATES", "lat/lng 必须是有限数值", item_path)
                continue
            if not _is_number(item.get("cost")) or float(item["cost"]) < 0:
                _append_error(errors, "INVALID_COST", "cost 必须是非负数值", f"{item_path}.cost")
                continue
            all_items.append((day_index, item_index, item))
    return all_items


def _check_route(plans: list[dict[str, Any]], errors: list[dict[str, Any]]) -> bool:
    route_valid = True
    for day_index, day in enumerate(plans):
        if not isinstance(day, dict) or not isinstance(day.get("items"), list):
            continue
        valid_items = [
            item
            for item in day["items"]
            if isinstance(item, dict) and _is_number(item.get("lat")) and _is_number(item.get("lng"))
        ]
        for item_index in range(len(valid_items) - 1):
            current = valid_items[item_index]
            following = valid_items[item_index + 1]
            distance = haversine(
                float(current["lat"]),
                float(current["lng"]),
                float(following["lat"]),
                float(following["lng"]),
            )
            if distance > MAX_ROUTE_DISTANCE_KM:
                route_valid = False
                _append_error(
                    errors,
                    "ROUTE_TOO_FAR",
                    f"相邻景点距离 {distance:.1f}km，超过 {MAX_ROUTE_DISTANCE_KM}km",
                    f"itinerary[{day_index}].items[{item_index}]",
                )
    return route_valid


async def verify_itinerary(
    itinerary: Any,
    budget: int,
    known_pois: list[dict[str, Any]],
    verify_external: bool = True,
) -> dict[str, Any]:
    """Return a complete validation report without raising on malformed model output."""
    errors: list[dict[str, Any]] = []
    items = _structure_items(itinerary, errors)
    structure_valid = not any(
        error["code"]
        in {
            "INVALID_ITINERARY_TYPE",
            "MISSING_FIELD",
            "INVALID_DAYS",
            "INVALID_ITINERARY_DAYS",
            "DAY_COUNT_MISMATCH",
            "INVALID_DAY_TYPE",
            "INVALID_DAY_NUMBER",
            "DUPLICATE_DAY",
            "INVALID_ITEMS",
            "EMPTY_DAY",
            "INVALID_ITEM_TYPE",
            "INVALID_SPOT_NAME",
            "INVALID_COORDINATES",
            "INVALID_COST",
        }
        for error in errors
    )

    spot_results: list[dict[str, Any]] = []
    seen_spots: set[str] = set()
    verified_count = 0
    for day_index, item_index, item in items:
        spot_name = item["spot"].strip()
        path = f"itinerary[{day_index}].items[{item_index}]"
        if spot_name in seen_spots:
            _append_error(errors, "DUPLICATE_SPOT", f"景点重复：{spot_name}", f"{path}.spot")
        else:
            seen_spots.add(spot_name)

        result = await verify_spot_poi(
            spot_name,
            float(item["lat"]),
            float(item["lng"]),
            known_pois,
            item.get("poi_id"),
            verify_external,
        )
        if result["valid"]:
            verified_count += 1
        else:
            _append_error(errors, "POI_NOT_VERIFIED", f"景点未通过验证：{spot_name}", path)
        spot_results.append({"spot": spot_name, **result})

        local_poi = _find_local_poi(spot_name, known_pois, item.get("poi_id"))
        if local_poi is None:
            _append_error(errors, "POI_REFERENCE_MISMATCH", f"景点不在当前候选数据中：{spot_name}", path)
        elif _is_number(local_poi.get("cost")) and abs(float(local_poi["cost"]) - float(item["cost"])) > COST_TOLERANCE:
            _append_error(errors, "POI_COST_MISMATCH", f"景点费用与数据源不一致：{spot_name}", f"{path}.cost")

    spot_sources = {result["source"] for result in spot_results if result["valid"]}
    if not spot_results:
        verification_source = "unavailable"
    elif spot_sources == {"external"}:
        verification_source = "external"
    elif spot_sources == {"local"}:
        verification_source = "local"
    else:
        verification_source = "mixed"

    duplicate_spots = any(error["code"] == "DUPLICATE_SPOT" for error in errors)
    fact_mismatch = any(
        error["code"] in {"POI_REFERENCE_MISMATCH", "POI_COST_MISMATCH"}
        for error in errors
    )
    spots_valid = bool(items) and verified_count == len(items) and not duplicate_spots and not fact_mismatch and structure_valid

    declared_total = itinerary.get("total_cost") if isinstance(itinerary, dict) else None
    calculated_total = 0.0
    calculation_valid = True
    plans = itinerary.get("itinerary", []) if isinstance(itinerary, dict) else []
    if not _is_number(declared_total) or float(declared_total) < 0:
        calculation_valid = False
        _append_error(errors, "INVALID_TOTAL_COST", "total_cost 必须是非负数值", "total_cost")
    if isinstance(plans, list):
        for day_index, day in enumerate(plans):
            if not isinstance(day, dict) or not isinstance(day.get("items"), list):
                calculation_valid = False
                continue
            item_total = sum(
                float(item["cost"])
                for item in day["items"]
                if isinstance(item, dict) and _is_number(item.get("cost")) and float(item["cost"]) >= 0
            )
            day_cost = day.get("day_cost")
            if not _is_number(day_cost) or float(day_cost) < item_total - COST_TOLERANCE:
                calculation_valid = False
                _append_error(
                    errors,
                    "DAY_COST_MISMATCH",
                    "day_cost 不能小于当日景点费用之和",
                    f"itinerary[{day_index}].day_cost",
                )
                continue
            calculated_total += float(day_cost)

    if _is_number(declared_total) and abs(float(declared_total) - calculated_total) > COST_TOLERANCE:
        calculation_valid = False
        _append_error(errors, "TOTAL_COST_MISMATCH", "total_cost 与每日费用之和不一致", "total_cost")

    safe_total = float(declared_total) if _is_number(declared_total) else calculated_total
    budget_valid = budget > 0 and calculation_valid and safe_total <= budget
    if calculation_valid and safe_total > budget:
        _append_error(errors, "BUDGET_EXCEEDED", "行程总费用超过预算", "total_cost")

    route_valid = structure_valid and _check_route(plans if isinstance(plans, list) else [], errors)
    overall_valid = structure_valid and spots_valid and calculation_valid and budget_valid and route_valid

    return {
        "overall_valid": overall_valid,
        "structure_valid": structure_valid,
        "spots_valid": spots_valid,
        "spots_total": len(items),
        "spots_verified": verified_count,
        "verification_source": verification_source,
        "spot_results": spot_results,
        "budget_valid": budget_valid,
        "budget_total": safe_total,
        "budget_limit": budget,
        "budget_utilization": round(safe_total / budget * 100) if budget > 0 else 0,
        "calculation_valid": calculation_valid,
        "calculated_total": calculated_total,
        "route_valid": route_valid,
        "errors": errors,
    }
