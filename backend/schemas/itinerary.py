"""Schemas for the facts/narrative trust boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated


NarrativeText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class NarrativeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poi_id: int = Field(gt=0)
    note: NarrativeText = ""
    reason: NarrativeText = ""


class NarrativeDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: int = Field(gt=0)
    transport_advice: NarrativeText = ""
    items: list[NarrativeItem]


class ItineraryNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: NarrativeText
    days: list[NarrativeDay]


class ItineraryGenerationOutcome(BaseModel):
    itinerary: dict
    generation_source: Literal["llm", "llm_repaired", "planner"]
    validation_status: Literal["valid", "repaired", "fallback"]
    fallback_reason: str | None = None
    model_version: str = "none"
