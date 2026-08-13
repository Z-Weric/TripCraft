"""Deterministic model routing rules and explicit fallback reasons."""

from dataclasses import dataclass

from services.llm_provider import LLMProvider


@dataclass(frozen=True)
class ModelRoute:
    primary: LLMProvider
    fallback: LLMProvider
    reason: str
    fallback_allowed: bool


def _is_multi_city(destination: str) -> bool:
    separators = (",", "，", "/", "、", "+", "→", "-")
    return any(separator in destination for separator in separators)


def route_model_request(
    scope: str,
    *,
    destination: str = "",
    days: int = 0,
    preferences: list[str] | None = None,
    repair_errors: list[str] | None = None,
) -> ModelRoute:
    from services.llm_service import get_default_provider, get_fallback_provider

    primary = get_default_provider(scope)
    fallback = get_fallback_provider(scope)
    reasons: list[str] = []
    if _is_multi_city(destination):
        reasons.append("multi_city")
    if days > 7:
        reasons.append("long_itinerary")
    if len(preferences or []) >= 5:
        reasons.append("complex_preferences")
    if repair_errors:
        reasons.append("schema_repair")
    if not reasons:
        reasons.append("standard_local_request")

    fallback_allowed = (
        fallback.available
        and fallback.model_id != primary.model_id
    )
    complex_request = reasons != ["standard_local_request"]
    if complex_request and fallback_allowed:
        primary, fallback = fallback, primary
    return ModelRoute(
        primary=primary,
        fallback=fallback,
        reason=",".join(reasons),
        fallback_allowed=(
            fallback.available
            and fallback.model_id != primary.model_id
        ),
    )
