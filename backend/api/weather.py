"""GET /api/weather — 天气预报"""

from fastapi import APIRouter, Query
from typing import List
from services.weather_service import get_weather, get_clothing_advice
from utils.logger import logger

router = APIRouter()


@router.get("/api/weather")
async def weather(city: str = Query(..., description="城市名"), days: int = Query(3, description="天数")):
    """获取城市天气预报 + 穿衣建议"""
    forecasts = await get_weather(city, days)
    if not forecasts:
        return {"city": city, "forecasts": [], "message": "天气服务暂不可用"}

    # 为每天添加穿衣建议
    for f in forecasts:
        f["clothing"] = get_clothing_advice(f)

    logger.info(f"天气查询: {city} {len(forecasts)}天")
    return {"city": city, "forecasts": forecasts}