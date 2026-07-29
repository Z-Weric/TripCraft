"""GET /api/pois — 查询景点信息"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.models import get_db, POI

router = APIRouter()


@router.get("/api/pois")
def get_pois(
    city: str = Query(..., description="城市名"),
    category: Optional[str] = Query(None, description="分类"),
    db: Session = Depends(get_db),
):
    query = db.query(POI).filter(POI.city == city)
    if category:
        query = query.filter(POI.category == category)
    pois = query.all()
    return [
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