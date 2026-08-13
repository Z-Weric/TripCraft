"""Shared request and response schemas for itinerary generation."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator


Destination = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Preference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class GenerateRequest(BaseModel):
    destination: Destination
    days: int = Field(gt=0, le=30)
    budget: int = Field(gt=0, le=1_000_000)
    preferences: list[Preference] = Field(default_factory=list, max_length=10)
    favorite_poi_ids: list[int] = Field(default_factory=list, max_length=500)

    @field_validator("preferences")
    @classmethod
    def deduplicate_preferences(cls, preferences: list[str]) -> list[str]:
        return list(dict.fromkeys(preferences))

    @field_validator("favorite_poi_ids")
    @classmethod
    def validate_favorite_poi_ids(cls, poi_ids: list[int]) -> list[int]:
        if any(poi_id <= 0 for poi_id in poi_ids):
            raise ValueError("favorite_poi_ids must contain positive integers")
        return list(dict.fromkeys(poi_ids))


class VerificationError(BaseModel):
    code: str
    message: str
    path: str | None = None


class SpotVerificationResult(BaseModel):
    spot: str
    valid: bool
    source: Literal["external", "local", "unavailable", "failed"]


class VerificationReport(BaseModel):
    overall_valid: bool = False
    structure_valid: bool = False
    spots_valid: bool = False
    spots_total: int = 0
    spots_verified: int = 0
    verification_source: Literal["external", "local", "mixed", "unavailable"] = "unavailable"
    spot_results: list[SpotVerificationResult] = Field(default_factory=list)
    budget_valid: bool = False
    budget_total: float = 0
    budget_limit: int = 0
    budget_utilization: int = 0
    calculation_valid: bool = False
    calculated_total: float = 0
    route_valid: bool = False
    errors: list[VerificationError] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    itinerary: dict
    verification: VerificationReport | dict
    generation_source: Literal["llm", "llm_repaired", "planner"] = "planner"
    validation_status: Literal["valid", "repaired", "fallback"] = "fallback"
    fallback_reason: str | None = None
    model_version: str = "none"


class GenerationProgress(BaseModel):
    stage: str
    message: str


class GenerationResult(BaseModel):
    itinerary: dict
    verification: VerificationReport
    generation_source: Literal["llm", "llm_repaired", "planner"] = "planner"
    validation_status: Literal["valid", "repaired", "fallback"] = "fallback"
    fallback_reason: str | None = None
    model_version: str = "none"
