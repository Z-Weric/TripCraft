"""Restricted review workflow for building human-approved training data."""

import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from config import settings
from database.models import SavedTrip, TrainingReview, TrainingReviewDecision, get_db
from utils.auth import require_user


router = APIRouter()

DIMENSIONS = {
    "poi_accuracy",
    "route_reasonableness",
    "budget",
    "schedule",
    "readability",
    "preference_match",
}
DECISION_VALUES = {"pass", "minor_issue", "reject"}
FINAL_LABELS = {"gold", "silver", "rejected"}


class ReviewSubmission(BaseModel):
    label: Literal["gold", "silver", "rejected"]
    dimensions: dict[str, Literal["pass", "minor_issue", "reject"]]
    error_codes: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("error_codes")
    @classmethod
    def normalize_error_codes(cls, values: list[str]) -> list[str]:
        return sorted({value.strip().upper()[:80] for value in values if value.strip()})

    @model_validator(mode="after")
    def validate_label(self):
        if set(self.dimensions) != DIMENSIONS:
            raise ValueError("dimensions must contain every required review dimension")
        values = set(self.dimensions.values())
        if self.label == "gold" and values != {"pass"}:
            raise ValueError("gold requires every dimension to pass")
        if self.label == "silver" and "reject" in values:
            raise ValueError("silver cannot contain a rejected dimension")
        if self.label == "rejected" and "reject" not in values:
            raise ValueError("rejected requires at least one rejected dimension")
        return self


class ResolutionSubmission(BaseModel):
    label: Literal["gold", "silver", "rejected"]


def _reviewer_emails() -> set[str]:
    return {
        email.strip().casefold()
        for email in settings.training_reviewer_emails.split(",")
        if email.strip()
    }


def require_training_reviewer(user: dict) -> dict:
    reviewers = _reviewer_emails()
    if not reviewers or str(user.get("email", "")).casefold() not in reviewers:
        raise HTTPException(status_code=403, detail="当前账号不具备训练数据审核权限")
    return user


def _eligible_candidate(trip: SavedTrip) -> bool:
    return (
        (trip.user_rating or 0) >= 3
        and trip.validation_status in {"valid", "repaired"}
        and trip.generation_source in {"llm", "llm_repaired", "planner"}
    )


def _refresh_review_status(review: TrainingReview, decisions: list[TrainingReviewDecision]) -> None:
    if len(decisions) < 2:
        review.status = "pending"
        review.final_label = None
        return
    labels = {decision.label for decision in decisions[:2]}
    if len(labels) == 1:
        label = labels.pop()
        review.final_label = label
        review.status = "approved" if label in {"gold", "silver"} else "rejected"
        return
    review.status = "needs_adjudication"
    review.final_label = None


def _review_payload(trip: SavedTrip, review: TrainingReview | None, decisions: list[TrainingReviewDecision]) -> dict:
    return {
        "trip_id": trip.id,
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "preferences": trip.preferences.split(",") if trip.preferences else [],
        "itinerary": json.loads(trip.itinerary_json),
        "verification": json.loads(trip.verification_json) if trip.verification_json else None,
        "traceability": {
            "model_version": trip.model_version,
            "planner_version": trip.planner_version,
            "poi_version": trip.poi_version,
            "generation_source": trip.generation_source,
            "validation_status": trip.validation_status,
        },
        "review": {
            "status": review.status if review else "pending",
            "final_label": review.final_label if review else None,
            "decision_count": len(decisions),
            "decisions": [
                {
                    "label": decision.label,
                    "dimensions": json.loads(decision.dimensions_json),
                    "error_codes": decision.error_codes.split(",") if decision.error_codes else [],
                    "created_at": decision.created_at.isoformat() if decision.created_at else None,
                }
                for decision in decisions
            ],
        },
    }


@router.get("/api/training-reviews/candidates")
async def list_candidates(
    status: Literal["pending", "needs_adjudication", "approved", "rejected"] = "pending",
    limit: int = 20,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    require_training_reviewer(user)
    limit = max(1, min(limit, 100))
    reviews = {item.trip_id: item for item in db.query(TrainingReview).all()}
    candidates = []
    for trip in db.query(SavedTrip).order_by(SavedTrip.created_at.desc()).all():
        if not _eligible_candidate(trip):
            continue
        review = reviews.get(trip.id)
        decisions = (
            db.query(TrainingReviewDecision)
            .filter(TrainingReviewDecision.trip_id == trip.id)
            .order_by(TrainingReviewDecision.created_at)
            .all()
        )
        actual_status = review.status if review else "pending"
        if actual_status == status:
            candidates.append(_review_payload(trip, review, decisions))
        if len(candidates) >= limit:
            break
    return {"items": candidates, "status": status}


@router.post("/api/training-reviews/{trip_id}")
async def submit_review(
    trip_id: int,
    payload: ReviewSubmission,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    require_training_reviewer(user)
    trip = db.query(SavedTrip).filter(SavedTrip.id == trip_id).first()
    if not trip or not _eligible_candidate(trip):
        raise HTTPException(status_code=404, detail="未找到可审核的训练候选行程")

    review = db.query(TrainingReview).filter(TrainingReview.trip_id == trip_id).first()
    if review is None:
        review = TrainingReview(trip_id=trip_id)
        db.add(review)
        db.flush()
    if review.status != "pending":
        raise HTTPException(status_code=409, detail="该样本已完成审核或正在等待裁决")
    existing = (
        db.query(TrainingReviewDecision)
        .filter(TrainingReviewDecision.trip_id == trip_id, TrainingReviewDecision.reviewer_id == user["user_id"])
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="每位审核员只能提交一次结论")

    db.add(
        TrainingReviewDecision(
            trip_id=trip_id,
            reviewer_id=user["user_id"],
            label=payload.label,
            dimensions_json=json.dumps(payload.dimensions, ensure_ascii=False, sort_keys=True),
            error_codes=",".join(payload.error_codes) or None,
        )
    )
    db.flush()
    decisions = (
        db.query(TrainingReviewDecision)
        .filter(TrainingReviewDecision.trip_id == trip_id)
        .order_by(TrainingReviewDecision.created_at)
        .all()
    )
    _refresh_review_status(review, decisions)
    review.updated_at = datetime.utcnow()
    db.commit()
    return {"status": review.status, "final_label": review.final_label, "decision_count": len(decisions)}


@router.post("/api/training-reviews/{trip_id}/resolve")
async def resolve_review(
    trip_id: int,
    payload: ResolutionSubmission,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    require_training_reviewer(user)
    review = db.query(TrainingReview).filter(TrainingReview.trip_id == trip_id).first()
    if not review or review.status != "needs_adjudication":
        raise HTTPException(status_code=409, detail="该样本不需要裁决")
    decisions = db.query(TrainingReviewDecision).filter(TrainingReviewDecision.trip_id == trip_id).all()
    if any(decision.reviewer_id == user["user_id"] for decision in decisions):
        raise HTTPException(status_code=403, detail="裁决必须由第三名审核员完成")
    review.final_label = payload.label
    review.status = "approved" if payload.label in {"gold", "silver"} else "rejected"
    review.resolved_by = user["user_id"]
    review.updated_at = datetime.utcnow()
    db.commit()
    return {"status": review.status, "final_label": review.final_label}
