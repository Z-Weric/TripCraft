"""Shared orchestration for regular and SSE itinerary generation."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from config import settings
from schemas.generate import GenerateRequest, GenerationProgress, GenerationResult
from utils.logger import logger


@dataclass(frozen=True)
class GenerationEvent:
    kind: Literal["progress", "result"]
    payload: GenerationProgress | GenerationResult


def _serialize_poi(poi: Any) -> dict[str, Any]:
    return {
        "id": poi.id,
        "city": poi.city,
        "name": poi.name,
        "category": poi.category,
        "lat": poi.lat,
        "lng": poi.lng,
        "address": poi.address,
        "cost": poi.cost,
        "duration": poi.duration,
        "note": poi.note,
        "rating": poi.rating,
    }


def load_city_pois(db: Session, destination: str) -> list[dict[str, Any]]:
    from database.models import POI
    from services.cache import poi_cache

    cache_key = f"pois:{destination}"
    cached = poi_cache.get(cache_key)
    if cached is not None:
        return cached

    pois = db.query(POI).filter(POI.city == destination).all()
    serialized = [_serialize_poi(poi) for poi in pois]
    poi_cache.set(cache_key, serialized)
    return serialized


def retrieve_candidate_pois(req: GenerateRequest, city_pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from services.rag_service import is_index_ready, search_pois_by_rag

    if not is_index_ready():
        return city_pois

    target_count = req.days * settings.candidate_pool_multiplier
    rag_pois = search_pois_by_rag(
        destination=req.destination,
        preferences=req.preferences,
        top_k=target_count,
    )
    if len(rag_pois) >= target_count:
        return rag_pois

    rag_names = {poi["name"] for poi in rag_pois}
    return rag_pois + [poi for poi in city_pois if poi["name"] not in rag_names]


async def _generate_itinerary(**kwargs: Any):
    from services.model_service import generate_itinerary

    return await generate_itinerary(**kwargs)


async def _verify_itinerary(itinerary: dict[str, Any], budget: int, city_pois: list[dict[str, Any]]) -> dict[str, Any]:
    from services.verify_service import verify_itinerary

    return await verify_itinerary(itinerary, budget, city_pois)


async def generate_events(req: GenerateRequest, db: Session) -> AsyncIterator[GenerationEvent]:
    yield GenerationEvent(
        kind="progress",
        payload=GenerationProgress(stage="rag_retrieval", message="正在检索景点知识库..."),
    )

    city_pois = load_city_pois(db, req.destination)
    if not city_pois:
        raise LookupError(f"暂不支持目的地：{req.destination}")

    candidate_pois = retrieve_candidate_pois(req, city_pois)
    yield GenerationEvent(
        kind="progress",
        payload=GenerationProgress(stage="rag_done", message=f"已检索到 {len(candidate_pois)} 个相关景点"),
    )
    yield GenerationEvent(
        kind="progress",
        payload=GenerationProgress(stage="llm_generating", message="AI 正在规划最优行程路线..."),
    )

    generation = await _generate_itinerary(
        destination=req.destination,
        days=req.days,
        budget=req.budget,
        preferences=req.preferences,
        pois=candidate_pois,
        favorite_poi_ids=req.favorite_poi_ids,
    )

    yield GenerationEvent(
        kind="progress",
        payload=GenerationProgress(stage="llm_done", message="行程已生成，正在验证..."),
    )
    yield GenerationEvent(
        kind="progress",
        payload=GenerationProgress(stage="verifying", message="正在验证景点真实性与预算合规..."),
    )

    verification = await _verify_itinerary(generation.itinerary, req.budget, city_pois)
    logger.info(
        "行程生成链路完成",
        extra={
            "validation_status": generation.validation_status,
            "fallback_reason": generation.fallback_reason,
            "status": "valid" if verification.get("overall_valid") else "invalid",
        },
    )
    yield GenerationEvent(
        kind="result",
        payload=GenerationResult(
            itinerary=generation.itinerary,
            verification=verification,
            generation_source=generation.generation_source,
            validation_status=generation.validation_status,
            fallback_reason=generation.fallback_reason,
            model_version=generation.model_version,
        ),
    )


async def generate_once(req: GenerateRequest, db: Session) -> GenerationResult:
    async for event in generate_events(req, db):
        if event.kind == "result":
            return event.payload
    raise RuntimeError("generation completed without a result")
