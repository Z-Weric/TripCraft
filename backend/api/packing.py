"""GET /api/packing — 打包清单"""

from fastapi import APIRouter, Query
from typing import List
from services.packing_service import generate_packing_list

router = APIRouter()


@router.get("/api/packing")
async def packing(
    city: str = Query(..., description="城市名"),
    days: int = Query(3, description="天数"),
    preferences: str = Query("", description="偏好，逗号分隔"),
):
    """生成打包清单"""
    prefs = [p.strip() for p in preferences.split(",") if p.strip()] if preferences else []
    return generate_packing_list(city, days, prefs)