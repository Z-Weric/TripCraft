"""行程持久化 API — 保存/列表/详情/删除"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from database.models import get_db, SavedTrip
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


@router.post("/api/itineraries")
async def save_trip(req: SaveTripRequest, db: Session = Depends(get_db)):
    """保存行程"""
    trip = SavedTrip(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=",".join(req.preferences),
        summary=req.itinerary.get("summary", ""),
        total_cost=req.itinerary.get("total_cost", 0),
        itinerary_json=json.dumps(req.itinerary, ensure_ascii=False),
        verification_json=json.dumps(req.verification, ensure_ascii=False) if req.verification else None,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"行程已保存: id={trip.id}, {req.destination} {req.days}天")
    return {"status": "ok", "id": trip.id}


@router.get("/api/itineraries", response_model=List[TripSummary])
async def list_trips(db: Session = Depends(get_db)):
    """获取行程列表"""
    trips = db.query(SavedTrip).order_by(SavedTrip.created_at.desc()).all()
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
        )
        for t in trips
    ]


@router.get("/api/itineraries/{trip_id}")
async def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """获取行程详情"""
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    return {
        "id": trip.id,
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "preferences": trip.preferences.split(",") if trip.preferences else [],
        "itinerary": json.loads(trip.itinerary_json),
        "verification": json.loads(trip.verification_json) if trip.verification_json else None,
        "created_at": trip.created_at.strftime("%Y-%m-%d %H:%M") if trip.created_at else "",
    }


@router.delete("/api/itineraries/{trip_id}")
async def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    """删除行程"""
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    db.delete(trip)
    db.commit()
    logger.info(f"行程已删除: id={trip_id}")
    return {"status": "ok"}