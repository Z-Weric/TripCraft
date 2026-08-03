"""LLM 服务 — 硅基流动 API 封装（v2 异步版 + 流式输出）

使用硅基流动 (siliconflow.cn) 的 OpenAI 兼容接口。
"""

import json
from typing import List, Dict, Any, Generator, Optional
import httpx

from config import settings
from utils.logger import logger

API_KEY = settings.siliconflow_api_key
LLM_MODEL = settings.llm_model
API_BASE = settings.llm_api_base
TIMEOUT = settings.llm_timeout

# 全局复用 async client
_async_client: Optional[httpx.AsyncClient] = None


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(timeout=TIMEOUT)
    return _async_client


def has_api_key() -> bool:
    return bool(API_KEY)


async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """非流式调用，返回完整文本。"""
    if not has_api_key():
        return "LLM API Key 未配置"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        client = _get_async_client()
        resp = await client.post(API_BASE, json=payload, headers=headers)
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        logger.error("LLM 返回异常", extra={"error": str(data)})
        return f"LLM 返回异常: {data}"
    except Exception as e:
        logger.error("LLM 调用失败", extra={"error": str(e)})
        return f"LLM 调用失败: {e}"


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Generator[str, None, None]:
    """流式调用 LLM，逐块 yield 文本内容。"""
    if not has_api_key():
        yield "LLM API Key 未配置"
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream("POST", API_BASE, json=payload, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error("LLM 流式调用失败", extra={"error": str(e)})
        yield f"\n[LLM 调用失败: {e}]"


async def chat_with_context(
    system_prompt: str,
    user_message: str,
    context: str = "",
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    """带 RAG 上下文的 LLM 对话（非流式）。"""
    full_system = system_prompt
    if context:
        full_system += f"\n\n以下是你可以参考的景点知识库信息：\n{context}"

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_message},
    ]
    return await chat_completion(messages, temperature, max_tokens)


async def chat_with_context_stream(
    system_prompt: str,
    user_message: str,
    context: str = "",
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Generator[str, None, None]:
    """带 RAG 上下文的 LLM 对话（流式）。"""
    full_system = system_prompt
    if context:
        full_system += f"\n\n以下是你可以参考的景点知识库信息：\n{context}"

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_message},
    ]
    async for chunk in chat_completion_stream(messages, temperature, max_tokens):
        yield chunk