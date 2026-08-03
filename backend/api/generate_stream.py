"""POST /api/generate/stream — 流式行程生成（SSE）

分阶段推送进度：
1. rag_retrieval — 正在检索景点
2. llm_generating — 正在生成行程
3. verifying — 正在验证
4. done — 完成，返回完整行程 + 验证结果
5. error — 出错
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
import json
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


@router.post("/api/generate/stream")
async def generate_stream(req: GenerateRequest, db: Session = Depends(get_db)):
    """流式 SSE 行程生成"""

    async def event_stream():
        start_time = time.time()

        def emit(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 1. 检索景点
        yield emit({"type": "progress", "stage": "rag_retrieval", "message": "正在检索景点知识库..."})

        cache_key = f"pois:{req.destination}"
        poi_dicts = poi_cache.get(cache_key)
        if poi_dicts is None:
            all_pois = db.query(POI).filter(POI.city == req.destination).all()
            poi_dicts = [
                {
                    "name": p.name, "category": p.category, "lat": p.lat, "lng": p.lng,
                    "cost": p.cost, "duration": p.duration, "note": p.note,
                }
                for p in all_pois
            ]
            poi_cache.set(cache_key, poi_dicts)

        if not poi_dicts:
            yield emit({"type": "error", "message": f"暂不支持目的地：{req.destination}"})
            return

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

        yield emit({"type": "progress", "stage": "rag_done", "message": f"已检索到 {len(selected_pois)} 个相关景点"})

        # 2. LLM 生成
        yield emit({"type": "progress", "stage": "llm_generating", "message": "AI 正在规划最优行程路线..."})

        try:
            itinerary = await generate_itinerary(
                destination=req.destination,
                days=req.days,
                budget=req.budget,
                preferences=req.preferences,
                pois=selected_pois,
            )
        except Exception as e:
            logger.error(f"行程生成失败: {e}")
            yield emit({"type": "error", "message": f"行程生成失败: {e}"})
            return

        yield emit({"type": "progress", "stage": "llm_done", "message": "行程已生成，正在验证..."})

        # 3. 验证
        yield emit({"type": "progress", "stage": "verifying", "message": "正在验证景点真实性与预算合规..."})

        try:
            verification = await verify_itinerary(itinerary, req.budget, poi_dicts)
        except Exception as e:
            logger.error(f"验证失败: {e}")
            verification = {"spots_valid": False, "budget_valid": False, "route_valid": False}

        # 4. 完成
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"流式行程生成完成: {req.destination} {req.days}天",
            extra={"method": "POST", "path": "/api/generate/stream", "duration": duration_ms}
        )

        yield emit({
            "type": "done",
            "itinerary": itinerary,
            "verification": verification,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )