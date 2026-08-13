"""Authenticated, persistent sharing and protected itinerary export."""

import json
import secrets
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database.models import ShareToken, SavedTrip, get_db
from services.share_service import can_read_trip, hash_share_token, is_share_token_active, is_trip_owner
from utils.auth import get_current_user, require_user
from utils.logger import logger


router = APIRouter()


class ShareResponse(BaseModel):
    url: str
    token: str
    expires_at: str


def _get_trip_or_404(db: Session, trip_id: int) -> SavedTrip:
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="行程不存在")
    return trip


def _get_token_record(db: Session, token: str) -> ShareToken | None:
    return db.query(ShareToken).filter(ShareToken.token_hash == hash_share_token(token)).first()


def _serialize_trip(trip: SavedTrip) -> dict:
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


@router.post("/api/share/{trip_id}", response_model=ShareResponse)
async def create_share_link(
    trip_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    """Create a revocable read-only share link. Only the owner may create it."""
    trip = _get_trip_or_404(db, trip_id)
    if not is_trip_owner(trip, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权分享该行程")

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.share_token_expire_hours)
    record = ShareToken(
        trip_id=trip.id,
        token_hash=hash_share_token(raw_token),
        created_by=user["user_id"],
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    logger.info(f"创建分享链接: trip_id={trip.id}, user={user['user_id']}")
    return ShareResponse(
        url=f"/detail/{raw_token}",
        token=raw_token,
        expires_at=expires_at.isoformat(timespec="seconds") + "Z",
    )


@router.get("/api/share/{token}")
async def get_shared_trip(token: str, db: Session = Depends(get_db)):
    """Read a trip through an active share token."""
    record = _get_token_record(db, token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享链接无效")
    if not is_share_token_active(record):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="分享链接已过期或被撤销")

    trip = _get_trip_or_404(db, record.trip_id)
    if not can_read_trip(trip, share_token=record):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该行程")
    return _serialize_trip(trip)


@router.delete("/api/share/{token}")
async def revoke_share_link(
    token: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    """Revoke a share link. Only the trip owner may revoke it."""
    record = _get_token_record(db, token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享链接不存在")
    trip = _get_trip_or_404(db, record.trip_id)
    if not is_trip_owner(trip, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权撤销该分享链接")

    if record.revoked_at is None:
        record.revoked_at = datetime.utcnow()
        db.commit()
    logger.info(f"撤销分享链接: trip_id={trip.id}, user={user['user_id']}")
    return {"status": "ok"}


@router.get("/api/export/{trip_id}")
async def export_trip(
    trip_id: int,
    format: Literal["json", "markdown"] = Query("json"),
    share_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Export only when the caller owns the trip, it is public, or a valid token is provided."""
    trip = _get_trip_or_404(db, trip_id)
    user = await get_current_user(authorization)
    token_record = _get_token_record(db, share_token) if share_token else None
    if token_record is not None and not is_share_token_active(token_record):
        token_record = None
    if not can_read_trip(trip, user=user, share_token=token_record):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权导出该行程")

    itinerary_data = json.loads(trip.itinerary_json)
    if format == "markdown":
        lines = [
            f"# {trip.destination} {trip.days}天行程",
            "",
            f"> {itinerary_data.get('summary', '')}",
            "",
            f"- **预算**: ¥{trip.budget}",
            f"- **总花费**: ¥{trip.total_cost}",
            f"- **偏好**: {trip.preferences}",
            "",
        ]
        for day in itinerary_data.get("itinerary", []):
            lines.append(f"## Day {day['day']} - ¥{day.get('day_cost', 0)}")
            lines.append(f"**交通**: {day.get('transport', '')}")
            lines.append("")
            for item in day.get("items", []):
                cost_str = "免费" if item.get("cost", 0) == 0 else f"¥{item['cost']}"
                lines.append(
                    f"- `{item['time']}` **{item['spot']}** ({item['category']}) - "
                    f"{item['duration']} | {cost_str}"
                )
                if item.get("note"):
                    lines.append(f"  - {item['note']}")
            lines.append("")
        lines.extend(["---", "*Generated by TripCraft*"])
        return {"format": "markdown", "content": "\n".join(lines)}

    return {
        "format": "json",
        "content": json.dumps(itinerary_data, ensure_ascii=False, indent=2),
    }
