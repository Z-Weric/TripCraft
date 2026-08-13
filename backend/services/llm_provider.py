"""Provider-neutral interfaces for local and external language models."""

import json
import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

import httpx


class ProviderError(RuntimeError):
    """Base error for model provider failures."""


class ProviderUnavailableError(ProviderError):
    """Raised when a configured provider cannot serve requests."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an invalid response."""


def _parse_json_content(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError as exc:
        raise ProviderResponseError(f"模型未返回合法 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderResponseError("模型 JSON 顶层必须是对象")
    return payload


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def available(self) -> bool: ...

    async def health_check(self) -> bool: ...

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict[str, Any]: ...

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]: ...


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 60,
        retries: int = 1,
        max_concurrency: int = 2,
        queue_timeout: float = 5,
        circuit_failure_threshold: int = 3,
        circuit_cooldown: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized_base_url = base_url.rstrip("/")
        for suffix in ("/v1/chat/completions", "/api/chat"):
            if normalized_base_url.endswith(suffix):
                normalized_base_url = normalized_base_url[: -len(suffix)]
                break
        self.base_url = normalized_base_url
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.queue_timeout = queue_timeout
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_cooldown = circuit_cooldown
        self._transport = transport
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._consecutive_failures = 0
        self._circuit_opened_at = 0.0

    @property
    def model_id(self) -> str:
        return f"ollama:{self.model}"

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.model)

    async def health_check(self) -> bool:
        if not self.available:
            return False
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5), transport=self._transport) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                return any(
                    model.get("name") == self.model or model.get("model") == self.model
                    for model in models
                )
        except (httpx.HTTPError, ValueError, TypeError):
            return False

    def _ensure_circuit_closed(self) -> None:
        if not self._circuit_opened_at:
            return
        if time.monotonic() - self._circuit_opened_at >= self.circuit_cooldown:
            self._circuit_opened_at = 0.0
            self._consecutive_failures = 0
            return
        raise ProviderUnavailableError("Ollama 熔断器已开启")

    async def _acquire_slot(self) -> None:
        self._ensure_circuit_closed()
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.queue_timeout)
        except TimeoutError as exc:
            raise ProviderUnavailableError("Ollama 请求队列已满") from exc

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._circuit_opened_at = 0.0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_failure_threshold:
            self._circuit_opened_at = time.monotonic()

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        await self._acquire_slot()
        last_error: Exception | None = None
        try:
            for attempt in range(self.retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                        response = await client.post(f"{self.base_url}/api/chat", json=payload)
                        response.raise_for_status()
                        self._record_success()
                        return response
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt >= self.retries:
                        break
            self._record_failure()
            raise ProviderUnavailableError(f"Ollama 调用失败: {last_error}") from last_error
        finally:
            self._semaphore.release()

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        if not self.available:
            raise ProviderUnavailableError("Ollama Provider 未配置")
        response = await self._post(
            {
                "model": self.model,
                "messages": messages,
                "format": schema,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
        )
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderResponseError("Ollama 响应缺少 message.content") from exc
        return _parse_json_content(content)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        if not self.available:
            raise ProviderUnavailableError("Ollama Provider 未配置")
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            await self._acquire_slot()
            try:
                async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                    async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                self._record_success()
            finally:
                self._semaphore.release()
        except httpx.HTTPError as exc:
            self._record_failure()
            raise ProviderUnavailableError(f"Ollama 流式调用失败: {exc}") from exc


class OpenAICompatibleProvider:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        timeout: float = 60,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._transport = transport

    @property
    def model_id(self) -> str:
        return f"openai-compatible:{self.model}"

    @property
    def available(self) -> bool:
        return bool(self.api_url and self.api_key and self.model)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def health_check(self) -> bool:
        if not self.available:
            return False
        models_url = self.api_url.rsplit("/chat/completions", 1)[0] + "/models"
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5), transport=self._transport) as client:
                response = await client.get(models_url, headers=self._headers)
                return response.is_success
        except httpx.HTTPError:
            return False

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        if not self.available:
            raise ProviderUnavailableError("OpenAI 兼容 Provider 未配置")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "tripcraft_response", "strict": True, "schema": schema},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                response = await client.post(self.api_url, json=payload, headers=self._headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"外部模型调用失败: {exc}") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("外部模型响应缺少 choices[0].message.content") from exc
        return _parse_json_content(content)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        if not self.available:
            raise ProviderUnavailableError("OpenAI 兼容 Provider 未配置")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=self._headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"外部模型流式调用失败: {exc}") from exc


class DisabledProvider:
    @property
    def model_id(self) -> str:
        return "disabled:none"

    @property
    def available(self) -> bool:
        return False

    async def health_check(self) -> bool:
        return False

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        raise ProviderUnavailableError("LLM Provider 已禁用")

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        raise ProviderUnavailableError("LLM Provider 已禁用")
        yield ""  # pragma: no cover
