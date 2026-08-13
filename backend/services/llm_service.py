"""Provider factory and compatibility helpers for model consumers."""

from collections.abc import AsyncIterator
from functools import lru_cache

from config import settings
from services.llm_provider import (
    DisabledProvider,
    LLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
)


def _enabled_scopes() -> set[str]:
    return {
        scope.strip().lower()
        for scope in settings.llm_enabled_scopes.split(",")
        if scope.strip()
    }


@lru_cache(maxsize=8)
def build_provider(name: str) -> LLMProvider:
    normalized = name.strip().lower().replace("-", "_")
    if normalized == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
            retries=settings.ollama_retries,
            max_concurrency=settings.ollama_max_concurrency,
            queue_timeout=settings.ollama_queue_timeout,
            circuit_failure_threshold=settings.ollama_circuit_failure_threshold,
            circuit_cooldown=settings.ollama_circuit_cooldown,
        )
    if normalized in {"openai", "openai_compatible", "siliconflow"}:
        return OpenAICompatibleProvider(
            api_url=settings.llm_api_base,
            api_key=settings.siliconflow_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
        )
    return DisabledProvider()


def get_default_provider(scope: str = "itinerary") -> LLMProvider:
    if scope.lower() not in _enabled_scopes():
        return DisabledProvider()
    return build_provider(settings.llm_default_provider)


def get_fallback_provider(scope: str = "itinerary") -> LLMProvider:
    if scope.lower() not in _enabled_scopes():
        return DisabledProvider()
    return build_provider(settings.llm_fallback_provider)


def has_api_key() -> bool:
    """Backward-compatible availability check for current chat callers."""
    return get_default_provider("chat").available


async def chat_completion_stream(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> AsyncIterator[str]:
    provider = get_default_provider("chat")
    async for chunk in provider.stream_chat(messages, temperature, max_tokens):
        yield chunk


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    """Collect a provider stream for callers that require one complete response."""
    chunks = [
        chunk
        async for chunk in chat_completion_stream(messages, temperature, max_tokens)
    ]
    return "".join(chunks)


async def chat_with_context_stream(
    system_prompt: str,
    user_message: str,
    context: str = "",
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> AsyncIterator[str]:
    if context:
        system_prompt += f"\n\n以下是你可以参考的景点知识库信息：\n{context}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    async for chunk in chat_completion_stream(messages, temperature, max_tokens):
        yield chunk
