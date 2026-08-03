"""天气服务 — 高德天气 API

获取指定城市未来几天的天气预报。
高德免费 API 支持当日/未来 3 天天气预报。
"""

import httpx
from typing import List, Dict, Any
from config import settings
from utils.logger import logger

AMAP_API_KEY = settings.amap_api_key
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


async def get_weather(city: str, days: int = 3) -> List[Dict[str, Any]]:
    """获取城市天气预报"""
    if not AMAP_API_KEY:
        logger.warning("高德 API Key 未配置，天气服务不可用")
        return []

    # extensions=all 获取未来预报，city 用城市名
    params = {
        "key": AMAP_API_KEY,
        "city": city,
        "extensions": "all",  # all=未来预报
    }
    try:
        async with httpx.AsyncClient(timeout=settings.amap_timeout) as client:
            resp = await client.get(AMAP_WEATHER_URL, params=params)
            data = resp.json()

        if data.get("status") != "1":
            logger.warning(f"天气 API 返回非 1: {data.get('info', '')}")
            return []

        # 高德返回 forecasts 列表
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return []

        # 取第一个 forecast 中的 casts 列表（每日天气）
        casts = forecasts[0].get("casts", [])
        result = []
        for cast in casts[:days]:
            result.append({
                "date": cast.get("date", ""),
                "week": cast.get("week", ""),
                "dayweather": cast.get("dayweather", "未知"),
                "nightweather": cast.get("nightweather", "未知"),
                "daytemp": cast.get("daytemp", ""),
                "nighttemp": cast.get("nighttemp", ""),
                "daywind": cast.get("daywind", ""),
                "daypower": cast.get("daypower", ""),
                "temp_diff": abs(int(cast.get("daytemp", 0)) - int(cast.get("nighttemp", 0))),
            })
        return result
    except Exception as e:
        logger.error(f"天气查询失败: {e}")
        return []


def get_clothing_advice(weather: Dict[str, Any]) -> str:
    """根据天气给出穿衣建议"""
    if not weather:
        return ""
    daytemp = int(weather.get("daytemp", 20))
    nighttemp = int(weather.get("nighttemp", 15))
    avg = (daytemp + nighttemp) / 2

    if avg >= 30:
        return "炎热，建议穿短袖、短裤，注意防晒"
    elif avg >= 25:
        return "温暖，短袖为主，备一件薄外套"
    elif avg >= 15:
        return "凉爽，建议长袖 + 外套"
    elif avg >= 5:
        return "偏冷，建议穿厚外套或薄羽绒服"
    else:
        return "寒冷，建议穿羽绒服、围巾、手套"

    if "雨" in weather.get("dayweather", ""):
        return "有雨，记得带伞"
    return ""