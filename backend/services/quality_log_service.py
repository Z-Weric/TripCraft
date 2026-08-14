"""Structured quality logging for low ratings and validation failures.

Records are written to trip_quality_logs for offline analysis only.
They must NOT be used for online training — each record is a single
observation that needs aggregation and review before entering any
training pipeline.
"""

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from database.models import SavedTrip, TripQualityLog
from utils.logger import logger

LOW_RATING_THRESHOLD = 2  # <= 2 视为低评分


def _build_reason_json(
    trigger: str,
    trip: Optional[SavedTrip],
    *,
    rating: Optional[int] = None,
    verification: Optional[dict[str, Any]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Build a structured reason payload (never includes PII)."""
    reason: dict[str, Any] = {"trigger": trigger}

    if rating is not None:
        reason["user_rating"] = rating

    if trip is not None:
        reason["destination"] = trip.destination
        reason["days"] = trip.days
        reason["budget"] = trip.budget
        reason["preferences"] = trip.preferences.split(",") if trip.preferences else []
        reason["generation_source"] = trip.generation_source
        reason["validation_status"] = trip.validation_status
        reason["fallback_reason"] = trip.fallback_reason
        reason["model_version"] = trip.model_version

    if verification is not None:
        reason["overall_valid"] = verification.get("overall_valid", False)
        reason["structure_valid"] = verification.get("structure_valid", False)
        reason["spots_valid"] = verification.get("spots_valid", False)
        reason["budget_valid"] = verification.get("budget_valid", False)
        reason["route_valid"] = verification.get("route_valid", False)
        reason["calculation_valid"] = verification.get("calculation_valid", False)
        errors = verification.get("errors", [])
        reason["error_codes"] = [e.get("code", "UNKNOWN") for e in errors] if isinstance(errors, list) else []
        reason["error_count"] = len(reason["error_codes"])
        reason["verification_source"] = verification.get("verification_source", "unavailable")

    if extra:
        reason.update(extra)

    return json.dumps(reason, ensure_ascii=False)


def _extract_error_codes(verification: dict[str, Any]) -> str:
    """Comma-joined error codes for quick SQL filtering."""
    errors = verification.get("errors", [])
    if not isinstance(errors, list):
        return ""
    return ",".join(e.get("code", "UNKNOWN") for e in errors)


def log_low_rating(
    db: Session,
    trip: SavedTrip,
    rating: int,
    verification: Optional[dict[str, Any]] = None,
) -> None:
    """Record a structured entry when a user rates a trip <= LOW_RATING_THRESHOLD."""
    if rating > LOW_RATING_THRESHOLD:
        return

    reason_json = _build_reason_json("low_rating", trip, rating=rating, verification=verification)
    error_codes = _extract_error_codes(verification) if verification else ""

    entry = TripQualityLog(
        trip_id=trip.id,
        user_id=trip.user_id,
        trigger="low_rating",
        destination=trip.destination,
        days=trip.days,
        budget=trip.budget,
        preferences=trip.preferences,
        generation_source=trip.generation_source,
        validation_status=trip.validation_status,
        fallback_reason=trip.fallback_reason,
        model_version=trip.model_version,
        error_codes=error_codes,
        reason_json=reason_json,
    )
    db.add(entry)
    logger.info(
        f"低评分质量记录: trip_id={trip.id}, rating={rating}",
        extra={"trigger": "low_rating", "validation_status": trip.validation_status},
    )


def log_validation_failure(
    db: Session,
    *,
    trip: Optional[SavedTrip] = None,
    destination: Optional[str] = None,
    days: Optional[int] = None,
    budget: Optional[int] = None,
    preferences: Optional[str] = None,
    generation_source: Optional[str] = None,
    validation_status: Optional[str] = None,
    fallback_reason: Optional[str] = None,
    model_version: Optional[str] = None,
    verification: Optional[dict[str, Any]] = None,
) -> None:
    """Record a structured entry when verification fails (overall_valid=False)."""
    if verification is not None and verification.get("overall_valid", True):
        return

    reason_json = _build_reason_json(
        "validation_failed",
        trip,
        verification=verification,
        extra={"destination": destination, "days": days, "budget": budget} if trip is None else None,
    )
    error_codes = _extract_error_codes(verification) if verification else ""

    entry = TripQualityLog(
        trip_id=trip.id if trip else None,
        user_id=trip.user_id if trip else None,
        trigger="validation_failed",
        destination=trip.destination if trip else destination,
        days=trip.days if trip else days,
        budget=trip.budget if trip else budget,
        preferences=trip.preferences if trip else preferences,
        generation_source=trip.generation_source if trip else (generation_source or ""),
        validation_status=trip.validation_status if trip else (validation_status or ""),
        fallback_reason=trip.fallback_reason if trip else fallback_reason,
        model_version=trip.model_version if trip else (model_version or "none"),
        error_codes=error_codes,
        reason_json=reason_json,
    )
    db.add(entry)
    logger.info(
        f"验证失败质量记录: trip_id={trip.id if trip else None}",
        extra={"trigger": "validation_failed"},
    )
