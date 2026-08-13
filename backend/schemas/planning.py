"""Typed domain models for deterministic itinerary planning."""

from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CandidatePoi(BaseModel):
    id: int = Field(gt=0)
    city: str = ""
    name: NonEmptyText
    category: str = "自然风光"
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str = ""
    cost: float = Field(default=0, ge=0)
    duration: str = "2h"
    note: str = ""
    rating: float = Field(default=0, ge=0)
    retrieval_score: float = Field(
        default=0,
        validation_alias=AliasChoices("retrieval_score", "_score"),
    )


class PlanningRequest(BaseModel):
    destination: NonEmptyText
    days: int = Field(gt=0, le=30)
    budget: float = Field(gt=0)
    preferences: list[str] = Field(default_factory=list)
    favorite_poi_ids: list[int] = Field(default_factory=list)
    excluded_poi_ids: list[int] = Field(default_factory=list)
    candidates: list[CandidatePoi] = Field(default_factory=list)


class PlanningReason(BaseModel):
    poi_id: int
    base_rating: float
    retrieval_bonus: float
    preference_bonus: float
    favorite_bonus: float
    total_score: float
    labels: list[str] = Field(default_factory=list)


class PlannedItem(BaseModel):
    time: str
    spot: str
    poi_id: int
    category: str
    duration: str
    cost: float
    lat: float
    lng: float
    note: str
    reason: str = ""
    transport_from_prev: str


class PlannedDay(BaseModel):
    day: int
    items: list[PlannedItem]
    transport: str
    transport_advice: str = ""
    day_cost: float


class PlannedItinerary(BaseModel):
    destination: str
    days: int
    itinerary: list[PlannedDay]
    total_cost: float
    summary: str


class PlanningOutcome(BaseModel):
    itinerary: PlannedItinerary
    reasons: list[PlanningReason]
    warnings: list[str] = Field(default_factory=list)
    candidate_count: int
    required_count: int
