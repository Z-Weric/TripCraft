"""POST /api/generate - generate an itinerary in one response."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time

from database.models import get_db
from schemas.generate import GenerateRequest, GenerateResponse
from services.generation_service import generate_once
from utils.logger import logger

router = APIRouter()


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    try:
        result = await generate_once(req, db)
    except LookupError:
        logger.info(f"目的地无 POI: {req.destination}")
        return GenerateResponse(
            itinerary={"error": f"暂不支持目的地：{req.destination}"},
            verification={},
        )

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"行程生成完成: {req.destination} {req.days}天",
        extra={"method": "POST", "path": "/api/generate", "duration": duration_ms}
    )

    return GenerateResponse(**result.model_dump())
