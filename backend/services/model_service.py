"""Mock 模型服务 — 模拟微调模型的 JSON 行程生成。

后续接入 vLLM 时，只需将 generate_itinerary 中的 mock 逻辑替换为
httpx 调用 vLLM 的 /v1/chat/completions 接口即可。
"""

import math
import random
from typing import List, Dict, Any


def haversine(lat1, lng1, lat2, lng2):
    """计算两点间距离（km）"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def generate_itinerary(destination: str, days: int, budget: int,
                       preferences: List[str], pois: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    基于 POI 数据库生成结构化行程 JSON。
    当前为 mock 实现：按偏好过滤景点，每日安排 3 个，确保预算和路线合理。

    后续替换为 vLLM 调用时：
        resp = httpx.post("http://localhost:8001/v1/chat/completions", json={...})
        return json.loads(resp.json()["choices"][0]["message"]["content"])
    """
    # 按偏好过滤 POI
    filtered = []
    for poi in pois:
        if not preferences:
            filtered.append(poi)
            continue
        # 偏好匹配：自然风光→自然，美食→美食，历史→历史文化，亲子→自然+历史，购物→购物
        pref_map = {
            "自然风光": ["自然风光"],
            "美食": ["美食"],
            "历史文化": ["历史文化"],
            "亲子": ["自然风光", "历史文化"],
            "购物": ["购物"],
        }
        matched_cats = set()
        for pref in preferences:
            matched_cats.update(pref_map.get(pref, []))
        if poi["category"] in matched_cats:
            filtered.append(poi)

    # 如果过滤后不够，补充全部 POI
    if len(filtered) < days * 3:
        remaining = [p for p in pois if p not in filtered]
        filtered.extend(remaining)

    # 随机打乱并选取
    random.shuffle(filtered)
    selected = filtered[:days * 3] if len(filtered) >= days * 3 else filtered

    # 构建行程
    itinerary = []
    total_cost = 0
    time_slots = [
        ("09:00-12:00", "3h"),
        ("12:00-13:30", "1.5h"),
        ("14:00-16:00", "2h"),
    ]
    transports = ["步行 + 公交，约15元", "地铁 + 步行，约10元", "自驾 / 大巴，约80元", "打车，约40元"]

    for day_idx in range(days):
        items = []
        day_cost = 0
        day_pois = selected[day_idx * 3 : (day_idx + 1) * 3]

        for i, poi in enumerate(day_pois):
            time_slot, duration = time_slots[i % 3]
            cost = poi.get("cost", 0)
            items.append({
                "time": time_slot,
                "spot": poi["name"],
                "category": poi["category"],
                "duration": poi.get("duration", duration),
                "cost": cost,
                "lat": poi["lat"],
                "lng": poi["lng"],
                "note": poi.get("note", ""),
            })
            day_cost += cost

        transport_cost = 15 if day_idx == 0 else random.choice([10, 15, 40, 80])
        day_cost += transport_cost
        total_cost += day_cost

        itinerary.append({
            "day": day_idx + 1,
            "items": items,
            "transport": transports[day_idx % len(transports)],
            "day_cost": day_cost,
        })

    pref_str = "、".join(preferences) if preferences else "综合"
    summary = f"{days}天{destination}{pref_str}之旅"

    return {
        "destination": destination,
        "days": days,
        "itinerary": itinerary,
        "total_cost": total_cost,
        "summary": summary,
    }