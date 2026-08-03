"""行程验证服务 — 景点真实性 + 路线合理性 + 预算合规 (v2 优化版)

优化点：
1. verify_spot_poi 只调用一次（v1 调用两次）
2. 异步化高德 API 调用
3. 缓存验证结果
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


async def verify_spot_poi(spot_name: str, lat: float, lng: float, known_pois: list = None) -> bool:
    """验证景点是否存在。优先高德 API，降级本地数据库。"""
    # 优先高德 API（异步 + 带缓存）
    result = await amap_verify_spot(spot_name, lat, lng)
    if result is not None:
        return result

    # 降级：本地数据库比对
    for poi in (known_pois or []):
        if poi["name"] == spot_name:
            if abs(poi["lat"] - lat) < 0.01 and abs(poi["lng"] - lng) < 0.01:
                return True
    return False


def check_route_distance(itinerary: Dict[str, Any]) -> bool:
    """路线合理性：相邻景点距离不超过 50km"""
    for day in itinerary["itinerary"]:
        items = day["items"]
        for i in range(len(items) - 1):
            dist = haversine(
                items[i]["lat"], items[i]["lng"],
                items[i+1]["lat"], items[i+1]["lng"]
            )
            if dist > 50:
                return False
    return True


async def verify_itinerary(itinerary: Dict[str, Any], budget: int, known_pois: list) -> Dict[str, Any]:
    """完整验证流程（v2：单次遍历，不再重复调用验证）"""
    results = {}

    # 1. 景点真实性 — 单次遍历
    all_items = []
    for day in itinerary["itinerary"]:
        all_items.extend(day["items"])

    verified_count = 0
    for item in all_items:
        if await verify_spot_poi(item["spot"], item["lat"], item["lng"], known_pois):
            verified_count += 1

    results["spots_valid"] = verified_count == len(all_items)
    results["spots_total"] = len(all_items)
    results["spots_verified"] = verified_count

    # 2. 预算合规
    results["budget_valid"] = itinerary["total_cost"] <= budget
    results["budget_total"] = itinerary["total_cost"]
    results["budget_limit"] = budget
    results["budget_utilization"] = round(itinerary["total_cost"] / budget * 100) if budget > 0 else 0

    # 3. 路线合理性
    results["route_valid"] = check_route_distance(itinerary)

    return results