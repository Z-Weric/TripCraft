"""训练数据生成脚本 — SFT + GSPO 双格式

生成两种训练数据：
1. SFT 数据：instruction → output（高质量行程）
2. GSPO 数据：prompt → chosen/rejected（好行程 vs 差行程）

用法:
    cd TripCraft
    source .venv/bin/activate
    python model/generate_training_data.py [--city 杭州] [--limit 10]

参数:
    --city  只生成指定城市（默认全部）
    --limit 每组组合只生成 N 条（默认不限制）
    --quick 快速模式：只生成少量数据用于测试
"""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database.models import SessionLocal, POI
from services.rag_service import search_pois_by_rag, is_index_ready
from services.model_service import generate_itinerary
from services.verify_service import verify_itinerary
from utils.logger import logger

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "training_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CITIES = ["杭州", "成都", "西安", "厦门", "苏州", "南京", "重庆", "长沙", "青岛", "大理"]
DAYS_OPTIONS = [2, 3, 5]
BUDGET_OPTIONS = [1000, 2000, 3000, 5000]

PREFERENCE_COMBOS = [
    ["自然风光", "美食"],
    ["自然风光", "历史文化"],
    ["美食", "购物"],
    ["自然风光", "美食", "亲子"],
    ["历史文化", "美食"],
    ["自然风光"],
    ["美食"],
    ["购物", "美食", "自然风光"],
    ["亲子", "自然风光"],
    ["历史文化", "自然风光", "美食", "购物"],
]


def build_instruction(destination: str, days: int, budget: int, preferences: List[str]) -> str:
    """构建 SFT instruction"""
    return (
        f"你是旅行规划专家。请生成一份 {days} 天的{destination}行程。"
        f"预算 {budget} 元，偏好：{', '.join(preferences)}。"
        f"要求：每天 3-4 个景点，路线就近排布，总花费不超预算。"
        f"景点必须来自真实数据。返回 JSON 格式，包含 destination, days, itinerary(每天 items 含 time/spot/category/duration/cost/lat/lng/note), total_cost, summary。"
    )


def build_gspo_prompt(destination: str, days: int, budget: int, preferences: List[str]) -> str:
    """构建 GSPO prompt（和 SFT instruction 相同）"""
    return build_instruction(destination, days, budget, preferences)


async def generate_one(db, destination: str, days: int, budget: int, preferences: List[str]) -> Dict[str, Any]:
    """生成一条行程 + 验证"""
    all_pois = db.query(POI).filter(POI.city == destination).all()
    poi_dicts = [
        {
            "id": p.id, "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
            "cost": p.cost, "duration": p.duration, "note": p.note, "rating": p.rating,
        }
        for p in all_pois
    ]
    if not poi_dicts:
        return None

    if is_index_ready():
        rag_pois = search_pois_by_rag(destination, preferences, top_k=days * 3)
        if len(rag_pois) >= days * 3:
            selected_pois = rag_pois
        else:
            selected_pois = rag_pois + [p for p in poi_dicts if p["name"] not in [r["name"] for r in rag_pois]]
    else:
        selected_pois = poi_dicts

    itinerary = await generate_itinerary(
        destination=destination, days=days, budget=budget,
        preferences=preferences, pois=selected_pois,
    )

    verification = await verify_itinerary(itinerary, budget, poi_dicts)

    quality_ok = (
        verification.get("spots_valid", False) and
        verification.get("budget_valid", False) and
        verification.get("route_valid", False)
    )

    # 计算质量分数（用于 GSPO 排序）
    quality_score = 0
    if verification.get("spots_valid"):
        quality_score += 3
    if verification.get("budget_valid"):
        quality_score += 2
    if verification.get("route_valid"):
        quality_score += 2
    # 预算利用率越高越好（但不超支）
    utilization = verification.get("budget_utilization", 0)
    if verification.get("budget_valid") and utilization > 50:
        quality_score += 1

    return {
        "itinerary": itinerary,
        "verification": verification,
        "quality_ok": quality_ok,
        "quality_score": quality_score,
        "request": {"destination": destination, "days": days, "budget": budget, "preferences": preferences},
    }


async def generate_bad_one(db, destination: str, days: int, budget: int, preferences: List[str]) -> Dict[str, Any]:
    """故意生成差行程 — 随机选景点、不考虑路线就近、不匹配偏好"""
    import random
    from services.model_service import haversine

    all_pois = db.query(POI).filter(POI.city == destination).all()
    poi_dicts = [
        {"id": p.id, "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
         "cost": p.cost, "duration": p.duration, "note": p.note, "rating": p.rating}
        for p in all_pois
    ]
    if not poi_dicts:
        return None

    # 随机选景点（不按评分/偏好排序）
    random.shuffle(poi_dicts)
    selected = poi_dicts[:days * 3]

    # 构建行程 — 固定时段、随机交通
    itinerary_list = []
    total_cost = 0
    time_slots = [("09:00-12:00", "3h"), ("12:00-13:30", "1.5h"), ("14:00-16:00", "2h")]

    for day_idx in range(days):
        items = []
        day_cost = 0
        day_pois = selected[day_idx * 3:(day_idx + 1) * 3]
        for i, poi in enumerate(day_pois):
            cost = poi.get("cost", 0)
            items.append({
                "time": time_slots[i % 3][0],
                "spot": poi["name"],
                "poi_id": poi.get("id", 0),
                "category": poi.get("category", "自然风光"),
                "duration": poi.get("duration", time_slots[i % 3][1]),
                "cost": cost,
                "lat": poi["lat"],
                "lng": poi["lng"],
                "note": poi.get("note", ""),
            })
            day_cost += cost
        transport_cost = random.choice([10, 40, 80])
        day_cost += transport_cost
        total_cost += day_cost
        itinerary_list.append({
            "day": day_idx + 1,
            "items": items,
            "transport": random.choice(["步行", "打车", "自驾"]),
            "day_cost": day_cost,
        })

    itinerary = {
        "destination": destination,
        "days": days,
        "itinerary": itinerary_list,
        "total_cost": total_cost,
        "summary": f"{days}天{destination}之旅",
    }

    # 验证
    verification = await verify_itinerary(itinerary, budget, poi_dicts)

    quality_score = 0
    if verification.get("spots_valid"):
        quality_score += 3
    if verification.get("budget_valid"):
        quality_score += 2
    if verification.get("route_valid"):
        quality_score += 2

    return {
        "itinerary": itinerary,
        "verification": verification,
        "quality_ok": False,  # 标记为差行程
        "quality_score": quality_score,
        "request": {"destination": destination, "days": days, "budget": budget, "preferences": preferences},
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default=None, help="只生成指定城市")
    parser.add_argument("--limit", type=int, default=None, help="每组组合限制条数")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    args = parser.parse_args()

    cities = [args.city] if args.city else CITIES
    if args.quick:
        cities = cities[:1]
        DAYS_OPTIONS[:] = [2]
        BUDGET_OPTIONS[:] = [2000]
        PREFERENCE_COMBOS[:] = PREFERENCE_COMBOS[:2]

    print("=== 训练数据生成（SFT + GSPO）===")
    print(f"城市: {cities}")
    print(f"天数: {DAYS_OPTIONS}")
    print(f"预算: {BUDGET_OPTIONS}")
    print(f"偏好组合: {len(PREFERENCE_COMBOS)} 种")
    total = len(cities) * len(DAYS_OPTIONS) * len(BUDGET_OPTIONS) * len(PREFERENCE_COMBOS)
    print(f"计划生成: {total} 组，每组 2 条（用于 GSPO 对比）")
    print()

    db = SessionLocal()
    sft_data = []       # SFT 训练数据
    gspo_data = []      # GSPO 训练数据
    all_records = []    # 所有记录
    count = 0

    for city_idx, city in enumerate(cities):
        print(f"\n=== [{city_idx+1}/{len(cities)}] {city} ===")

        for days in DAYS_OPTIONS:
            for budget in BUDGET_OPTIONS:
                for prefs in PREFERENCE_COMBOS:
                    # 生成 1 条好行程 + 1 条差行程（用于 GSPO 对比）
                    good_record = None
                    bad_record = None
                    try:
                        good_record = await generate_one(db, city, days, budget, prefs)
                        count += 1
                        if good_record:
                            status = "✓" if good_record["quality_ok"] else "△"
                            print(f"  {status} [好] {city} {days}天 ¥{budget} {prefs} → ¥{good_record['itinerary'].get('total_cost', '?')} (score={good_record['quality_score']})")
                        time.sleep(1)
                    except Exception as e:
                        print(f"  ✗ [好] {city} {days}天 → {e}")
                        time.sleep(2)

                    try:
                        bad_record = await generate_bad_one(db, city, days, budget, prefs)
                        count += 1
                        if bad_record:
                            print(f"  △ [差] {city} {days}天 ¥{budget} {prefs} → ¥{bad_record['itinerary'].get('total_cost', '?')} (score={bad_record['quality_score']})")
                    except Exception as e:
                        print(f"  ✗ [差] {city} {days}天 → {e}")

                    # SFT 数据：只取高质量行程
                    if good_record and good_record["quality_ok"]:
                        sft_data.append({
                            "instruction": build_instruction(city, days, budget, prefs),
                            "input": "",
                            "output": json.dumps(good_record["itinerary"], ensure_ascii=False, indent=2),
                        })

                    # GSPO 数据：好行程 vs 差行程
                    if good_record and bad_record and good_record["quality_score"] > bad_record["quality_score"]:
                        gspo_data.append({
                            "prompt": build_gspo_prompt(city, days, budget, prefs),
                            "chosen": json.dumps(good_record["itinerary"], ensure_ascii=False, indent=2),
                            "rejected": json.dumps(bad_record["itinerary"], ensure_ascii=False, indent=2),
                        })

                    if good_record:
                        all_records.append(good_record)
                    if bad_record:
                        all_records.append(bad_record)

                    if args.limit and count >= args.limit:
                        break
                if args.limit and count >= args.limit:
                    break
            if args.limit and count >= args.limit:
                break

    db.close()

    # 保存
    print(f"\n=== 生成完成 ===")
    print(f"总行程数: {count}")
    print(f"SFT 数据: {len(sft_data)} 条")
    print(f"GSPO 数据: {len(gspo_data)} 条")

    sft_path = os.path.join(OUTPUT_DIR, "train_sft.json")
    with open(sft_path, "w", encoding="utf-8") as f:
        json.dump(sft_data, f, ensure_ascii=False, indent=2)
    print(f"SFT → {sft_path}")

    gspo_path = os.path.join(OUTPUT_DIR, "train_gspo.json")
    with open(gspo_path, "w", encoding="utf-8") as f:
        json.dump(gspo_data, f, ensure_ascii=False, indent=2)
    print(f"GSPO → {gspo_path}")

    # 统计
    raw_path = os.path.join(OUTPUT_DIR, "raw_stats.json")
    stats = {
        "total": count,
        "sft_count": len(sft_data),
        "gspo_count": len(gspo_data),
        "quality_rate": len([r for r in all_records if r["quality_ok"]]) / max(len(all_records), 1),
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"质量率: {stats['quality_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(main())