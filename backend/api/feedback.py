"""POST /api/feedback — 用户反馈 (v2 异步版)"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import get_db, Feedback
from utils.logger import logger

router = APIRouter()


class FeedbackRequest(BaseModel):
    destination: str
    days: int
    budget: int
    preferences: List[str] = []
    feedback_type: str  # useful / improve
    comment: Optional[str] = None


@router.post("/api/feedback")
async def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    fb = Feedback(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=",".join(req.preferences),
        feedback_type=req.feedback_type,
        comment=req.comment,
    )
    db.add(fb)
    db.commit()
    logger.info(f"用户反馈: {req.feedback_type} for {req.destination}")
    return {"status": "ok", "id": fb.id}