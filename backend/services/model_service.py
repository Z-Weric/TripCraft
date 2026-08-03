"""模型服务 — LLM 行程生成 + Mock 降级 (v2)

优先使用 LLM 生成结构化行程 JSON，失败时降级到 mock 算法。
"""

import math
import random
import json
from typing import List, Dict, Any, Optional
from utils.logger import logger
from config import settings


def haversine(lat1, lng1, lat2, lng2):
    """计算两点间距离（km）"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ===== Mock 生成（降级方案） =====

def _mock_generate(destination: str, days: int, budget: int,
                    preferences: List[str], pois: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    智能行程生成算法（v2 重写版）：
    1. 评分优先：按 rating 降序排序，高评分景点优先入选
    2. 偏好加权：匹配偏好的景点加分
    3. 预算控制：累计花费不超预算
    4. 贪心就近排布：每天选起点后，每次选最近的下一个景点
    5. 时段智能分配：上午=自然/历史，中午=美食，下午=购物/休闲
    6. 交通方式匹配：根据距离选择步行/公交/打车
    """
    import itertools

    # ===== 1. 景点评分排序 + 偏好加权 =====
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

    scored_pois = []
    for poi in pois:
        score = poi.get("rating", 0)
        # 偏好匹配加分
        if poi["category"] in matched_cats:
            score += 2.0
        scored_pois.append({**poi, "_score": score})

    # 按综合分数降序排序
    scored_pois.sort(key=lambda x: x["_score"], reverse=True)

    # 按预算约束选取景点池（保留足够多的候选）
    target_count = days * 3
    selected = scored_pois[:max(target_count, min(len(scored_pois), target_count * 2))]

    # 如果不够，补充剩余景点
    if len(selected) < target_count:
        remaining = [p for p in scored_pois if p not in selected]
        selected.extend(remaining)
    selected = selected[:max(target_count, len(selected))]

    # ===== 2. 贪心就近排布 — 每天选景点 + 路线优化 =====
    # 按类别分组，方便时段分配
    by_category = {"自然风光": [], "美食": [], "历史文化": [], "购物": [], "亲子": []}
    for poi in selected:
        cat = poi.get("category", "自然风光")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(poi)

    # 时段-类别偏好映射
    time_slots = [
        ("09:00-12:00", "上午", ["自然风光", "历史文化"]),  # 上午安排自然/历史
        ("12:00-13:30", "中午", ["美食"]),                  # 中午安排美食
        ("14:00-16:00", "下午", ["购物", "自然风光", "历史文化"]),  # 下午灵活
    ]

    itinerary = []
    total_cost = 0
    used_names = set()  # 避免重复安排同一景点

    for day_idx in range(days):
        items = []
        day_cost = 0
        prev_lat, prev_lng = None, None

        for slot_idx, (time_slot, period, preferred_cats) in enumerate(time_slots):
            # 从偏好类别中选一个未用过的景点
            candidates = []
            for cat in preferred_cats:
                for poi in by_category.get(cat, []):
                    if poi["name"] not in used_names:
                        # 如果有上一个景点，计算距离优先选近的
                        if prev_lat is not None:
                            dist = haversine(prev_lat, prev_lng, poi["lat"], poi["lng"])
                        else:
                            dist = 0
                        candidates.append((poi, dist))

            if not candidates:
                # 从全部未用景点中选
                for poi in selected:
                    if poi["name"] not in used_names:
                        if prev_lat is not None:
                            dist = haversine(prev_lat, prev_lng, poi["lat"], poi["lng"])
                        else:
                            dist = 0
                        candidates.append((poi, dist))

            if not candidates:
                continue

            # 贪心：选距离最近的（如果没有 prev 就选评分最高的）
            if prev_lat is not None:
                candidates.sort(key=lambda x: x[1])  # 按距离升序
            else:
                candidates.sort(key=lambda x: x[0].get("_score", 0), reverse=True)  # 按评分降序

            poi = candidates[0][0]
            used_names.add(poi["name"])
            cost = poi.get("cost", 0)

            # 累计花费检查
            if total_cost + cost > budget and cost > 0:
                # 预算快超了，找免费景点替代
                free_candidate = next((c[0] for c in candidates if c[0].get("cost", 0) == 0), None)
                if free_candidate:
                    poi = free_candidate
                    used_names.add(poi["name"])
                    cost = 0

            # 计算交通距离和方式
            if prev_lat is not None:
                dist_km = haversine(prev_lat, prev_lng, poi["lat"], poi["lng"])
            else:
                dist_km = 0

            # 根据距离选择交通方式
            if dist_km == 0:
                transport = "步行出发"
                transport_cost = 0
            elif dist_km < 3:
                transport = f"步行约{dist_km:.1f}km"
                transport_cost = 0
            elif dist_km < 15:
                transport = f"公交/地铁约{dist_km:.1f}km，约10元"
                transport_cost = 10
            elif dist_km < 40:
                transport = f"打车约{dist_km:.1f}km，约40元"
                transport_cost = 40
            else:
                transport = f"自驾/大巴约{dist_km:.0f}km，约80元"
                transport_cost = 80

            # 使用景点自身的 duration，没有则用默认
            duration = poi.get("duration", time_slots[slot_idx][0].split("-")[0] + "h")

            items.append({
                "time": time_slot,
                "spot": poi["name"],
                "category": poi.get("category", "自然风光"),
                "duration": duration,
                "cost": cost,
                "lat": poi["lat"],
                "lng": poi["lng"],
                "note": poi.get("note", ""),
                "transport_from_prev": transport,
            })
            day_cost += cost
            day_cost += transport_cost if slot_idx > 0 else 0
            prev_lat, prev_lng = poi["lat"], poi["lng"]

        total_cost += day_cost

        # 当日交通总结
        if items:
            day_transport = " → ".join([items[0]["spot"]] + [it["spot"] for it in items[1:]])
            day_transport_str = f"路线: {day_transport}"
        else:
            day_transport_str = "暂无安排"

        itinerary.append({
            "day": day_idx + 1,
            "items": items,
            "transport": day_transport_str,
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


# ===== LLM 生成（主方案） =====

ITINERARY_SCHEMA = {
    "destination": "string",
    "days": "number",
    "itinerary": [
        {
            "day": "number (从1开始)",
            "items": [
                {
                    "time": "string (如 09:00-12:00)",
                    "spot": "string (景点名，必须来自提供的景点列表)",
                    "category": "string",
                    "duration": "string (如 2h)",
                    "cost": "number (门票费用)",
                    "lat": "number (纬度)",
                    "lng": "number (经度)",
                    "note": "string (简短备注)"
                }
            ],
            "transport": "string (当日交通建议)",
            "day_cost": "number (当日总花费)"
        }
    ],
    "total_cost": "number (总花费)",
    "summary": "string (一句话总结)"
}


def _build_llm_prompt(destination: str, days: int, budget: int,
                      preferences: List[str], pois: List[Dict[str, Any]]) -> str:
    """构建 LLM system prompt"""
    pref_str = "、".join(preferences) if preferences else "综合体验"
    pois_json = json.dumps(pois, ensure_ascii=False, indent=2)

    return f"""你是旅行规划专家。请根据以下景点数据，为用户生成一份 {days} 天的{destination}行程。

要求：
1. 总花费不超过 {budget} 元
2. 每天 3-4 个景点，时间安排合理（上午、中午、下午）
3. 路线就近排布，减少不必要的交通绕路
4. 偏好主题：{pref_str}
5. 景点名必须来自下方提供的景点列表
6. lat/lng/cost/category 必须与景点列表中的数据一致

可选景点数据：
{pois_json}

请严格返回以下 JSON 格式（不要包含 markdown 代码块标记，直接返回纯 JSON）：
{json.dumps(ITINERARY_SCHEMA, ensure_ascii=False, indent=2)}"""


async def _llm_generate(destination: str, days: int, budget: int,
                         preferences: List[str], pois: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """调用 LLM 生成行程，返回 dict 或 None（失败时）"""
    from services.llm_service import has_api_key, chat_completion

    if not has_api_key():
        logger.info("LLM API Key 未配置，使用 mock 生成")
        return None

    system_prompt = _build_llm_prompt(destination, days, budget, preferences, pois)

    try:
        result = await chat_completion(
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        # 清理可能的 markdown 代码块标记
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        parsed = json.loads(result)

        # 基本校验
        if not all(k in parsed for k in ["destination", "days", "itinerary", "total_cost"]):
            logger.warning("LLM 输出缺少必要字段")
            return None
        if len(parsed["itinerary"]) != days:
            logger.warning(f"LLM 输出天数不匹配: 期望 {days}, 实际 {len(parsed['itinerary'])}")
            return None

        logger.info(f"LLM 行程生成成功: {destination} {days}天 ¥{parsed.get('total_cost', '?')}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"LLM 输出 JSON 解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM 行程生成异常: {e}")
        return None


# ===== 对外接口 =====

async def generate_itinerary(destination: str, days: int, budget: int,
                              preferences: List[str], pois: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成行程 JSON。
    优先使用 LLM，失败时降级到 mock。
    """
    # 尝试 LLM 生成
    llm_result = await _llm_generate(destination, days, budget, preferences, pois)
    if llm_result is not None:
        return llm_result

    # 降级到 mock
    logger.info(f"降级到 mock 生成: {destination} {days}天")
    return _mock_generate(destination, days, budget, preferences, pois)