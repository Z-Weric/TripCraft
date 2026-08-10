"""行程持久化 API — 保存/列表/详情/删除（v2 用户绑定）"""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from database.models import get_db, SavedTrip
from utils.auth import get_current_user, require_user
from utils.logger import logger

router = APIRouter()


class SaveTripRequest(BaseModel):
    destination: str
    days: int
    budget: int
    preferences: List[str] = []
    itinerary: dict
    verification: Optional[dict] = None


class TripSummary(BaseModel):
    id: int
    destination: str
    days: int
    budget: int
    summary: str
    total_cost: int
    preferences: str
    created_at: str
    user_rating: int = 0
    is_public: int = 0


@router.post("/api/itineraries")
async def save_trip(req: SaveTripRequest, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """保存行程 — 已登录绑定 user_id，游客返回临时 ID 不入库"""
    user = await get_current_user(authorization)

    if not user:
        # 游客模式：不持久化，返回临时 ID
        logger.info("游客模式：行程不持久化")
        return {"status": "ok", "id": 0, "guest": True}

    trip = SavedTrip(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=",".join(req.preferences),
        summary=req.itinerary.get("summary", ""),
        total_cost=req.itinerary.get("total_cost", 0),
        itinerary_json=json.dumps(req.itinerary, ensure_ascii=False),
        verification_json=json.dumps(req.verification, ensure_ascii=False) if req.verification else None,
        user_id=user["user_id"],
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"行程已保存: id={trip.id}, user={user['user_id']}, {req.destination} {req.days}天")
    return {"status": "ok", "id": trip.id, "guest": False}


@router.get("/api/itineraries", response_model=List[TripSummary])
async def list_trips(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """获取当前用户的行程列表"""
    user = await get_current_user(authorization)
    if not user:
        return []

    trips = db.query(SavedTrip).filter(SavedTrip.user_id == user["user_id"]).order_by(SavedTrip.created_at.desc()).all()
    return [
        TripSummary(
            id=t.id,
            destination=t.destination,
            days=t.days,
            budget=t.budget,
            summary=t.summary,
            total_cost=t.total_cost,
            preferences=t.preferences,
            created_at=t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
            user_rating=t.user_rating or 0,
            is_public=t.is_public or 0,
        )
        for t in trips
    ]


@router.get("/api/itineraries/{trip_id}")
async def get_trip(trip_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """获取行程详情 — owner 可看私有，公开行程任何人可看"""
    user = await get_current_user(authorization)
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}

    # 权限：公开行程 or owner
    if trip.is_public != 1 and (not user or trip.user_id != user["user_id"]):
        return {"error": "无权查看"}

    return {
        "id": trip.id,
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "preferences": trip.preferences.split(",") if trip.preferences else [],
        "itinerary": json.loads(trip.itinerary_json),
        "verification": json.loads(trip.verification_json) if trip.verification_json else None,
        "created_at": trip.created_at.strftime("%Y-%m-%d %H:%M") if trip.created_at else "",
        "is_public": trip.is_public or 0,
        "user_rating": trip.user_rating or 0,
    }


@router.delete("/api/itineraries/{trip_id}")
async def delete_trip(trip_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """删除行程 — 仅 owner"""
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    if trip.user_id != user["user_id"]:
        return {"error": "无权删除"}

    db.delete(trip)
    db.commit()
    logger.info(f"行程已删除: id={trip_id}, user={user['user_id']}")
    return {"status": "ok"}


@router.put("/api/itineraries/{trip_id}/visibility")
async def toggle_visibility(trip_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """切换行程公开/私有"""
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    if trip.user_id != user["user_id"]:
        return {"error": "无权操作"}

    trip.is_public = 0 if trip.is_public else 1
    db.commit()
    logger.info(f"行程可见性切换: id={trip_id}, public={trip.is_public}")
    return {"status": "ok", "is_public": trip.is_public}


@router.put("/api/itineraries/{trip_id}/rate")
async def rate_trip(trip_id: int, rating: int = 0, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """给行程打分"""
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    if trip.user_id != user["user_id"]:
        return {"error": "无权操作"}

    trip.user_rating = max(0, min(5, rating))
    db.commit()
    logger.info(f"行程评分: id={trip_id}, rating={trip.user_rating}")
    return {"status": "ok", "user_rating": trip.user_rating}