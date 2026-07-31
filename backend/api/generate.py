"""POST /api/generate — 生成行程（RAG 增强版）"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from database.models import get_db, POI
from services.model_service import generate_itinerary
from services.verify_service import verify_itinerary
from services.rag_service import search_pois_by_rag, is_index_ready

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
    # 从数据库查询该城市的 POI（用于验证）
    all_pois = db.query(POI).filter(POI.city == req.destination).all()
    poi_dicts = [
        {
            "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
            "cost": p.cost, "duration": p.duration, "note": p.note,
        }
        for p in all_pois
    ]

    if not poi_dicts:
        return GenerateResponse(
            itinerary={"error": f"暂不支持目的地：{req.destination}"},
            verification={},
        )

    # RAG 检索：根据目的地+偏好检索最相关的景点
    # 如果 RAG 索引可用，用检索结果替换随机选取；否则降级到全部 POI
    if is_index_ready():
        rag_pois = search_pois_by_rag(
            destination=req.destination,
            preferences=req.preferences,
            top_k=req.days * 3,
        )
        # 如果 RAG 检索结果足够，用检索结果；否则补充全部 POI
        if len(rag_pois) >= req.days * 3:
            selected_pois = rag_pois
        else:
            selected_pois = rag_pois + [
                p for p in poi_dicts
                if p["name"] not in [r["name"] for r in rag_pois]
            ]
    else:
        selected_pois = poi_dicts

    # 调用模型生成行程
    itinerary = generate_itinerary(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=req.preferences,
        pois=selected_pois,
    )

    # 验证（用全部 POI 做真实性校验）
    verification = verify_itinerary(itinerary, req.budget, poi_dicts)

    return GenerateResponse(itinerary=itinerary, verification=verification)