"""POST /api/generate — 生成行程（v2 异步版 + 缓存）"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
import time

from database.models import get_db, POI
from services.model_service import generate_itinerary
from services.verify_service import verify_itinerary
from services.rag_service import search_pois_by_rag, is_index_ready
from services.cache import poi_cache
from utils.logger import logger

router = APIRouter()


class GenerateRequest(BaseModel):
    destination: str
    days: int
    budget: int
    preferences: List[str] = []
    favorite_poi_ids: List[int] = []


class GenerateResponse(BaseModel):
    itinerary: dict
    verification: dict


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    start_time = time.time()

    # 缓存 POI 查询
    cache_key = f"pois:{req.destination}"
    poi_dicts = poi_cache.get(cache_key)
    if poi_dicts is None:
        all_pois = db.query(POI).filter(POI.city == req.destination).all()
        poi_dicts = [
            {
                "id": p.id, "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
                "cost": p.cost, "duration": p.duration, "note": p.note, "rating": p.rating,
            }
            for p in all_pois
        ]
        poi_cache.set(cache_key, poi_dicts)

    if not poi_dicts:
        logger.info(f"目的地无 POI: {req.destination}")
        return GenerateResponse(
            itinerary={"error": f"暂不支持目的地：{req.destination}"},
            verification={},
        )

    # RAG 检索
    if is_index_ready():
        rag_pois = search_pois_by_rag(
            destination=req.destination,
            preferences=req.preferences,
            top_k=req.days * 3,
        )
        if len(rag_pois) >= req.days * 3:
            selected_pois = rag_pois
        else:
            selected_pois = rag_pois + [
                p for p in poi_dicts
                if p["name"] not in [r["name"] for r in rag_pois]
            ]
    else:
        selected_pois = poi_dicts

    # 生成行程（异步 LLM + mock 降级）
    itinerary = await generate_itinerary(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=req.preferences,
        pois=selected_pois,
        favorite_poi_ids=req.favorite_poi_ids,
    )

    # 验证（异步）
    verification = await verify_itinerary(itinerary, req.budget, poi_dicts)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"行程生成完成: {req.destination} {req.days}天",
        extra={"method": "POST", "path": "/api/generate", "duration": duration_ms}
    )

    return GenerateResponse(itinerary=itinerary, verification=verification)