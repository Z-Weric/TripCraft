"""GET /api/pois — 查询景点信息 (v2 异步版 + 缓存)"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.models import get_db, POI
from services.cache import poi_cache

router = APIRouter()


@router.get("/api/pois")
async def get_pois(
    city: str = Query(..., description="城市名"),
    category: Optional[str] = Query(None, description="分类"),
    db: Session = Depends(get_db),
):
    cache_key = f"pois:{city}:{category or 'all'}"
    cached = poi_cache.get(cache_key)
    if cached is not None:
        return cached

    query = db.query(POI).filter(POI.city == city)
    if category:
        query = query.filter(POI.category == category)
    pois = query.all()
    result = [
        {
            "name": p.name,
            "category": p.category,
            "lat": p.lat,
            "lng": p.lng,
            "address": p.address,
            "cost": p.cost,
            "duration": p.duration,
            "note": p.note,
            "rating": p.rating,
        }
        for p in pois
    ]
    poi_cache.set(cache_key, result)
    return result