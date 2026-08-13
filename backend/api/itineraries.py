"""行程持久化 API — 保存/列表/详情/删除（v2 用户绑定）"""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import hashlib

from database.models import get_db, SavedTrip, TripEditEvent
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
    generation_source: str = "planner"
    validation_status: str = "fallback"
    fallback_reason: Optional[str] = None
    model_version: str = "none"


PLANNER_VERSION = "planner-v1"


def _poi_version(itinerary: dict) -> str:
    facts = [
        {
            "poi_id": item.get("poi_id"),
            "spot": item.get("spot"),
            "lat": item.get("lat"),
            "lng": item.get("lng"),
            "cost": item.get("cost"),
            "duration": item.get("duration"),
        }
        for day in itinerary.get("itinerary", [])
        for item in day.get("items", [])
    ]
    payload = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _itinerary_hash(itinerary: dict) -> str:
    payload = json.dumps(itinerary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _item_key(item: dict) -> str:
    poi_id = item.get("poi_id")
    return f"poi:{poi_id}" if poi_id else f"spot:{item.get('spot', '')}"


def _itinerary_diff(before: dict, after: dict) -> dict:
    before_days = {day.get("day"): day for day in before.get("itinerary", [])}
    after_days = {day.get("day"): day for day in after.get("itinerary", [])}
    events: list[dict] = []
    for day_number in sorted(set(before_days) | set(after_days), key=lambda value: value or 0):
        old_items = before_days.get(day_number, {}).get("items", [])
        new_items = after_days.get(day_number, {}).get("items", [])
        old_map = {_item_key(item): item for item in old_items}
        new_map = {_item_key(item): item for item in new_items}
        old_keys = list(old_map)
        new_keys = list(new_map)

        removed = [key for key in old_keys if key not in new_map]
        added = [key for key in new_keys if key not in old_map]
        replacement_count = min(len(removed), len(added))
        for old_key, new_key in zip(
            removed[:replacement_count],
            added[:replacement_count],
        ):
            events.append(
                {
                    "type": "replace",
                    "day": day_number,
                    "from": old_map[old_key],
                    "to": new_map[new_key],
                }
            )
        events.extend(
            {"type": "delete", "day": day_number, "item": old_map[key]}
            for key in removed[replacement_count:]
        )
        events.extend(
            {"type": "add", "day": day_number, "item": new_map[key]}
            for key in added[replacement_count:]
        )

        common_old = [key for key in old_keys if key in new_map]
        common_new = [key for key in new_keys if key in old_map]
        if common_old != common_new:
            events.append(
                {
                    "type": "reorder",
                    "day": day_number,
                    "before": common_old,
                    "after": common_new,
                }
            )
        for key in set(old_map) & set(new_map):
            old_note = old_map[key].get("note", "")
            new_note = new_map[key].get("note", "")
            if old_note != new_note:
                events.append(
                    {
                        "type": "note_update",
                        "day": day_number,
                        "poi": key,
                        "before": old_note,
                        "after": new_note,
                    }
                )
    return {
        "events": events,
        "action_types": sorted({event["type"] for event in events}),
    }


class UpdateTripRequest(BaseModel):
    itinerary: dict


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
        model_version=req.model_version[:100],
        planner_version=PLANNER_VERSION,
        poi_version=_poi_version(req.itinerary),
        generation_source=req.generation_source[:30],
        validation_status=req.validation_status[:30],
        fallback_reason=req.fallback_reason,
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
        "model_version": trip.model_version or "none",
        "planner_version": trip.planner_version or PLANNER_VERSION,
        "poi_version": trip.poi_version,
        "generation_source": trip.generation_source or "planner",
        "validation_status": trip.validation_status or "fallback",
        "fallback_reason": trip.fallback_reason,
        "version": trip.version or 1,
    }


@router.put("/api/itineraries/{trip_id}")
async def update_trip(
    trip_id: int,
    req: UpdateTripRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        return {"error": "行程不存在"}
    if trip.user_id != user["user_id"]:
        return {"error": "无权编辑"}

    before = json.loads(trip.itinerary_json)
    differences = _itinerary_diff(before, req.itinerary)
    if not differences["events"]:
        return {"status": "ok", "version": trip.version or 1, "changed": False}

    from_version = trip.version or 1
    to_version = from_version + 1
    db.add(
        TripEditEvent(
            trip_id=trip.id,
            user_id=user["user_id"],
            from_version=from_version,
            to_version=to_version,
            action_types=",".join(differences["action_types"]),
            diff_json=json.dumps(differences, ensure_ascii=False),
            before_hash=_itinerary_hash(before),
            after_hash=_itinerary_hash(req.itinerary),
        )
    )
    trip.itinerary_json = json.dumps(req.itinerary, ensure_ascii=False)
    trip.summary = req.itinerary.get("summary", trip.summary)
    trip.total_cost = req.itinerary.get("total_cost", trip.total_cost)
    trip.poi_version = _poi_version(req.itinerary)
    trip.version = to_version
    db.commit()
    logger.info(
        f"行程版本已更新: id={trip_id}, v{from_version}->v{to_version}, actions={differences['action_types']}"
    )
    return {
        "status": "ok",
        "version": to_version,
        "changed": True,
        "action_types": differences["action_types"],
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
