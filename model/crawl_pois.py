"""高德 API 景点爬取脚本

从高德地图 POI 搜索 API 爬取 10 个城市的真实景点数据，
写入 SQLite 数据库，替代手工种子数据。

用法:
    cd TripCraft
    source .venv/bin/activate
    python model/crawl_pois.py
"""

import os
import sys
import time
import httpx
from typing import List, Dict, Any

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database.models import engine, SessionLocal, POI, Base

# 加载 API Key
AMAP_API_KEY = ""
_env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_API_KEY="):
                AMAP_API_KEY = line.split("=", 1)[1].strip()

AMAP_POI_URL = "https://restapi.amap.com/v3/place/text"

# 10 个目标城市
CITIES = ["杭州", "成都", "西安", "厦门", "苏州", "南京", "重庆", "长沙", "青岛", "大理"]

# 搜索关键词分类（对应项目的 category 字段）
SEARCH_CATEGORIES = [
    {"keywords": "风景名胜", "category": "自然风光"},
    {"keywords": "公园", "category": "自然风光"},
    {"keywords": "餐厅", "category": "美食"},
    {"keywords": "特色美食", "category": "美食"},
    {"keywords": "博物馆", "category": "历史文化"},
    {"keywords": "古迹", "category": "历史文化"},
    {"keywords": "寺庙", "category": "历史文化"},
    {"keywords": "购物", "category": "购物"},
    {"keywords": "步行街", "category": "购物"},
]

# 估算花费的简单规则（高德免费 API 不返回门票价格）
COST_ESTIMATE = {
    "自然风光": 50,
    "美食": 80,
    "历史文化": 60,
    "购物": 100,
}

DURATION_ESTIMATE = {
    "自然风光": "2-3h",
    "美食": "1-1.5h",
    "历史文化": "1.5-2h",
    "购物": "1-2h",
}


def crawl_pois(city: str, keywords: str, category: str, page: int = 1) -> List[Dict[str, Any]]:
    """调用高德 POI 搜索 API（含评分数据）"""
    params = {
        "key": AMAP_API_KEY,
        "keywords": keywords,
        "city": city,
        "citylimit": "true",
        "offset": 20,
        "page": page,
        "extensions": "all",  # all 返回详细信息含 biz_ext.rating
    }
    try:
        resp = httpx.get(AMAP_POI_URL, params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "1":
            print(f"  [警告] API 返回非 1: {data.get('info', '')}")
            return []

        pois = []
        for poi in data.get("pois", []):
            location = poi.get("location", "")
            if not location or "," not in location:
                continue
            lng, lat = location.split(",")

            name = poi.get("name", "").strip()
            if not name:
                continue

            # 提取高德评分
            biz_ext = poi.get("biz_ext", {}) or {}
            rating_str = biz_ext.get("rating", "")
            try:
                rating = float(rating_str) if rating_str else 0
            except (ValueError, TypeError):
                rating = 0

            # 提取门票价格（高德 deepinfo 中可能有）
            deepinfo = poi.get("deepinfo", {}) or {}
            cost = COST_ESTIMATE.get(category, 50)
            # 尝试从 deepinfo 中获取门票价格
            if deepinfo:
                ticket = deepinfo.get("ticket", "")
                if ticket and ticket != "无":
                    # 尝试提取数字
                    import re
                    price_match = re.search(r'(\d+)', ticket)
                    if price_match:
                        cost = int(price_match.group(1))

            # 提取营业时间作为 duration 参考
            opentime = (deepinfo or {}).get("opentime", "") or poi.get("opentime", "")

            pois.append({
                "city": city,
                "name": name,
                "category": category,
                "lat": float(lat),
                "lng": float(lng),
                "address": poi.get("address", "") or "",
                "cost": cost,
                "duration": DURATION_ESTIMATE.get(category, "2h"),
                "note": f"高德类型: {poi.get('type', '未知')}" + (f" | 评分: {rating}" if rating > 0 else ""),
                "rating": rating,
            })
        return pois
    except Exception as e:
        print(f"  [错误] 爬取失败: {e}")
        return []


def crawl_all_cities():
    """爬取所有城市的所有分类景点"""
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # 清空旧数据
    old_count = db.query(POI).count()
    if old_count > 0:
        print(f"清空旧数据: {old_count} 条")
        db.query(POI).delete()
        db.commit()

    total = 0
    seen_names = set()  # 去重

    for city in CITIES:
        print(f"\n=== 爬取 {city} ===")
        city_count = 0

        for cat_config in SEARCH_CATEGORIES:
            keywords = cat_config["keywords"]
            category = cat_config["category"]

            # 爬取 2 页（每页 20 条，每分类最多 40 条）
            for page in range(1, 3):
                pois = crawl_pois(city, keywords, category, page)
                if not pois:
                    break

                for poi in pois:
                    # 去重：同城市同名景点只保留一条
                    key = f"{poi['city']}_{poi['name']}"
                    if key in seen_names:
                        continue
                    seen_names.add(key)

                    db.add(POI(**poi))
                    city_count += 1

                # 避免触发 API 频率限制
                time.sleep(0.15)

        db.commit()
        # 统计有评分的景点
        rated = db.query(POI).filter(POI.city == city, POI.rating > 0).count()
        print(f"  {city}: {city_count} 个景点 (其中 {rated} 个有评分)")
        total += city_count

    db.close()
    print(f"\n=== 完成: 共 {total} 个景点 ===")
    return total


if __name__ == "__main__":
    if not AMAP_API_KEY:
        print("错误: 未找到 AMAP_API_KEY，请检查 backend/.env")
        sys.exit(1)

    print(f"高德 API Key: {AMAP_API_KEY[:8]}...")
    print(f"目标城市: {', '.join(CITIES)}")
    print(f"搜索分类: {len(SEARCH_CATEGORIES)} 类")
    print()

    crawl_all_cities()

    # 验证
    db = SessionLocal()
    total_rated = 0
    for city in CITIES:
        count = db.query(POI).filter(POI.city == city).count()
        rated = db.query(POI).filter(POI.city == city, POI.rating > 0).count()
        total_rated += rated
        print(f"  {city}: {count} 个景点, {rated} 个有评分")
    print(f"\n有评分景点总计: {total_rated} / {db.query(POI).count()}")
    db.close()