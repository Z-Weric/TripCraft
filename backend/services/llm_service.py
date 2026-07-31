"""LLM 服务 — 硅基流动 API 封装（支持流式输出）

使用硅基流动 (siliconflow.cn) 的 OpenAI 兼容接口。
模型：meituan-longcat/LongCat-2.0
"""

import os
import json
import httpx
from typing import List, Dict, Any, Optional, Generator

# 加载 API Key
API_KEY = ""
LLM_MODEL = "meituan-longcat/LongCat-2.0"

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("SILICONFLOW_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("LLM_MODEL="):
                LLM_MODEL = line.split("=", 1)[1].strip().strip('"').strip("'")

API_BASE = "https://api.siliconflow.cn/v1/chat/completions"


def has_api_key() -> bool:
    return bool(API_KEY)


def chat_completion(
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
        resp = httpx.post(API_BASE, json=payload, headers=headers, timeout=30)
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        return f"LLM 返回异常: {data}"
    except Exception as e:
        return f"LLM 调用失败: {e}"


def chat_completion_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Generator[str, None, None]:
    """
    流式调用 LLM，逐块 yield 文本内容。
    返回的每个 chunk 是一段文本片段。
    """
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
        with httpx.Client(timeout=60) as client:
            with client.stream("POST", API_BASE, json=payload, headers=headers) as resp:
                for line in resp.iter_lines():
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
        yield f"\n[LLM 调用失败: {e}]"


def chat_with_context(
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
    return chat_completion(messages, temperature, max_tokens)


def chat_with_context_stream(
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
    yield from chat_completion_stream(messages, temperature, max_tokens)