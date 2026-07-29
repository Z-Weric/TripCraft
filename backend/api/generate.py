"""POST /api/generate — 生成行程"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from database.models import get_db, POI
from services.model_service import generate_itinerary
from services.verify_service import verify_itinerary

router = APIRouter()


class GenerateRequest(BaseModel):
    destination: str
    days: int
    budget: int
    preferences: List[str] = []


class GenerateResponse(BaseModel):
    itinerary: dict
    verification: dict


@router.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    # 从数据库查询该城市的 POI
    pois = db.query(POI).filter(POI.city == req.destination).all()
    poi_dicts = [
        {
            "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
            "cost": p.cost, "duration": p.duration, "note": p.note,
        }
        for p in pois
    ]

    # 如果数据库没有该城市，返回错误
    if not poi_dicts:
        return GenerateResponse(
            itinerary={"error": f"暂不支持目的地：{req.destination}"},
            verification={},
        )

    # 调用模型生成行程（当前为 mock）
    itinerary = generate_itinerary(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=req.preferences,
        pois=poi_dicts,
    )

    # 验证
    verification = verify_itinerary(itinerary, req.budget, poi_dicts)

    return GenerateResponse(itinerary=itinerary, verification=verification)