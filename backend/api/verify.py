"""POST /api/verify — 验证行程"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import get_db, POI
from services.verify_service import verify_itinerary

router = APIRouter()


class VerifyRequest(BaseModel):
    itinerary: dict
    budget: int


@router.post("/api/verify")
def verify(req: VerifyRequest, db: Session = Depends(get_db)):
    pois = db.query(POI).all()
    poi_dicts = [
        {"name": p.name, "lat": p.lat, "lng": p.lng}
        for p in pois
    ]
    return verify_itinerary(req.itinerary, req.budget, poi_dicts)