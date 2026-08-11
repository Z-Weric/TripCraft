"""美食广场 API — 从 POI 表查询美食数据"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from database.models import get_db, POI
from utils.logger import logger

router = APIRouter()


@router.get("/api/foods")
async def list_foods(
    city: str = Query(..., description="城市名"),
    db: Session = Depends(get_db),
):
    """城市美食列表"""
    pois = db.query(POI).filter(POI.city == city, POI.category == "美食").order_by(POI.rating.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "city": p.city,
            "category": p.category,
            "cost": p.cost,
            "duration": p.duration,
            "address": p.address,
            "note": p.note,
            "rating": p.rating,
            "lat": p.lat,
            "lng": p.lng,
        }
        for p in pois
    ]


@router.get("/api/foods/cities")
async def food_cities(db: Session = Depends(get_db)):
    """有美食数据的城市列表"""
    from sqlalchemy import distinct
    cities = db.query(distinct(POI.city)).filter(POI.category == "美食").all()
    return [c[0] for c in cities]