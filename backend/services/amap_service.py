"""高德 API 服务 — POI 查询 + 景点验证

使用高德地图 Web API 进行真实的 POI 搜索和景点真实性验证。
API Key 配置在环境变量 AMAP_API_KEY 或 backend/.env 中。
"""

import os
import httpx
from typing import List, Dict, Any, Optional

# 加载 API Key — 优先环境变量，其次 .env 文件
AMAP_API_KEY = os.environ.get("AMAP_API_KEY", "")

# 尝试从 .env 读取（不依赖 python-dotenv，简单读取）
if not AMAP_API_KEY:
    _env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(_env_path):
        with open(_env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("AMAP_API_KEY="):
                    AMAP_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

AMAP_POI_URL = "https://restapi.amap.com/v3/place/text"
AMAP_GEO_URL = "https://restapi.amap.com/v3/geocode/geo"


def has_api_key() -> bool:
    return bool(AMAP_API_KEY)


def search_pois(city: str, category: str = None, db_pois: List[Dict] = None) -> List[Dict[str, Any]]:
    """
    查询景点 POI 数据。
    优先使用高德 API，如果 API Key 不存在则降级到本地数据库。
    """
    if not has_api_key():
        # 降级到本地数据库
        results = []
        for poi in db_pois or []:
            if poi["city"] != city:
                continue
            if category and poi["category"] != category:
                continue
            results.append({
                "name": poi["name"],
                "category": poi["category"],
                "lat": poi["lat"],
                "lng": poi["lng"],
                "address": poi.get("address", ""),
                "cost": poi.get("cost", 0),
                "duration": poi.get("duration", ""),
                "note": poi.get("note", ""),
                "rating": poi.get("rating", 0),
            })
        return results

    # 高德 API 查询
    keywords = category or "景点"
    params = {
        "key": AMAP_API_KEY,
        "keywords": keywords,
        "city": city,
        "citylimit": "true",
        "offset": 20,
        "page": 1,
        "extensions": "base",
    }
    try:
        resp = httpx.get(AMAP_POI_URL, params=params, timeout=5)
        data = resp.json()
        if data.get("status") != "1":
            return []
        pois = []
        for poi in data.get("pois", []):
            location = poi.get("location", "")
            if not location or "," not in location:
                continue
            lng, lat = location.split(",")
            pois.append({
                "name": poi.get("name", ""),
                "category": category or "景点",
                "lat": float(lat),
                "lng": float(lng),
                "address": poi.get("address", ""),
                "cost": 0,
                "duration": "",
                "note": "",
                "rating": 0,
            })
        return pois
    except Exception:
        return []


def verify_spot(spot_name: str, lat: float, lng: float) -> bool:
    """
    通过高德 API 验证景点是否存在。
    使用关键词搜索 + 经纬度比对。
    """
    if not has_api_key():
        return True  # 无 API Key 时跳过验证，返回 True

    params = {
        "key": AMAP_API_KEY,
        "keywords": spot_name,
        "offset": 5,
        "page": 1,
        "extensions": "base",
    }
    try:
        resp = httpx.get(AMAP_POI_URL, params=params, timeout=5)
        data = resp.json()
        if data.get("status") != "1":
            return False
        for poi in data.get("pois", []):
            location = poi.get("location", "")
            if not location or "," not in location:
                continue
            poi_lng, poi_lat = location.split(",")
            poi_lat = float(poi_lat)
            poi_lng = float(poi_lng)
            # 经纬度偏差在 0.02 度（约 2km）以内视为匹配
            if abs(poi_lat - lat) < 0.02 and abs(poi_lng - lng) < 0.02:
                return True
        return False
    except Exception:
        return False