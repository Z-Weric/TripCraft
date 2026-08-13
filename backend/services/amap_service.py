"""高德 API 服务 — POI 查询 + 景点验证 (v2 异步版 + 缓存)

API Key 配置在环境变量 AMAP_API_KEY 或 backend/.env 中。
"""

import httpx
from typing import List, Dict, Any
from config import settings
from services.cache import amap_verify_cache
from utils.logger import logger

AMAP_API_KEY = settings.amap_api_key
AMAP_POI_URL = settings.amap_poi_url
AMAP_GEO_URL = settings.amap_geo_url
AMAP_TIMEOUT = settings.amap_timeout


def has_api_key() -> bool:
    return bool(AMAP_API_KEY)


async def search_pois(city: str, category: str = None, db_pois: List[Dict] = None) -> List[Dict[str, Any]]:
    """查询景点 POI 数据。优先高德 API，降级本地数据库。"""
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
        async with httpx.AsyncClient(timeout=AMAP_TIMEOUT) as client:
            resp = await client.get(AMAP_POI_URL, params=params)
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
    except Exception as e:
        logger.error("高德 POI 查询失败", extra={"error": str(e), "city": city})
        return []


async def verify_spot(spot_name: str, lat: float, lng: float) -> bool | None:
    """验证景点；未配置或请求异常时返回 None，由调用方进行本地验证。"""
    if not has_api_key():
        return None

    cache_key = f"verify:{spot_name}:{lat:.4f}:{lng:.4f}"
    cached = amap_verify_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "key": AMAP_API_KEY,
        "keywords": spot_name,
        "offset": 5,
        "page": 1,
        "extensions": "base",
    }
    try:
        async with httpx.AsyncClient(timeout=AMAP_TIMEOUT) as client:
            resp = await client.get(AMAP_POI_URL, params=params)
            data = resp.json()
        if data.get("status") != "1":
            amap_verify_cache.set(cache_key, False)
            return False
        for poi in data.get("pois", []):
            location = poi.get("location", "")
            if not location or "," not in location:
                continue
            poi_lng, poi_lat = location.split(",")
            poi_lat = float(poi_lat)
            poi_lng = float(poi_lng)
            if abs(poi_lat - lat) < 0.02 and abs(poi_lng - lng) < 0.02:
                amap_verify_cache.set(cache_key, True)
                return True
        amap_verify_cache.set(cache_key, False)
        return False
    except Exception as e:
        logger.error("高德景点验证失败", extra={"error": str(e), "spot": spot_name})
        return None
