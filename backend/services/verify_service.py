"""行程验证服务 — 景点真实性 + 路线合理性 + 预算合规

景点真实性验证使用高德 API（amap_service.verify_spot）。
路线合理性使用 haversine 距离计算。
预算合规使用总花费与用户预算比对。
"""

import math
from typing import Dict, Any
from services.amap_service import verify_spot as amap_verify_spot


def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def verify_spot_poi(spot_name: str, lat: float, lng: float, known_pois: list = None) -> bool:
    """
    验证景点是否存在。
    优先使用高德 API 验证；如果 API 不可用，降级到本地 POI 数据库比对。
    """
    # 优先高德 API
    result = amap_verify_spot(spot_name, lat, lng)
    if result is not None:
        return result

    # 降级：本地数据库比对
    for poi in (known_pois or []):
        if poi["name"] == spot_name:
            if abs(poi["lat"] - lat) < 0.01 and abs(poi["lng"] - lng) < 0.01:
                return True
    return False


def check_route_distance(itinerary: Dict[str, Any]) -> bool:
    """
    路线合理性：相邻景点距离按交通方式分档
    步行 < 5km，公交 < 20km，驾车 < 50km
    """
    for day in itinerary["itinerary"]:
        items = day["items"]
        for i in range(len(items) - 1):
            dist = haversine(
                items[i]["lat"], items[i]["lng"],
                items[i+1]["lat"], items[i+1]["lng"]
            )
            # 简化：统一用 50km 上限
            if dist > 50:
                return False
    return True


def verify_itinerary(itinerary: Dict[str, Any], budget: int, known_pois: list) -> Dict[str, Any]:
    """完整验证流程"""
    results = {}

    # 1. 景点真实性
    all_items = []
    for day in itinerary["itinerary"]:
        all_items.extend(day["items"])

    results["spots_valid"] = all(
        verify_spot_poi(item["spot"], item["lat"], item["lng"], known_pois)
        for item in all_items
    )
    results["spots_total"] = len(all_items)
    results["spots_verified"] = sum(
        1 for item in all_items
        if verify_spot_poi(item["spot"], item["lat"], item["lng"], known_pois)
    )

    # 2. 预算合规
    results["budget_valid"] = itinerary["total_cost"] <= budget
    results["budget_total"] = itinerary["total_cost"]
    results["budget_limit"] = budget
    results["budget_utilization"] = round(itinerary["total_cost"] / budget * 100) if budget > 0 else 0

    # 3. 路线合理性
    results["route_valid"] = check_route_distance(itinerary)

    return results