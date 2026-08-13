"""POST /api/chat — 桌宠客服 RAG 问答（v2 异步流式 SSE）"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import time

from services.llm_provider import ProviderUnavailableError
from services.model_router import route_model_request
from services.rag_service import search_pois_by_rag, is_index_ready
from utils.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    destination: Optional[str] = None


def _retrieve_context(question: str, destination: str = None) -> str:
    """通过 rag_service 检索景点，返回上下文文本。"""
    if not is_index_ready():
        return ""

    pois = search_pois_by_rag(
        destination=destination or "",
        preferences=None,
        top_k=5,
    )

    if not pois:
        from services.rag_service import _pois_db
        if not _pois_db:
            return ""
        pois = _pois_db[:5]

    if not pois:
        return ""

    parts = []
    for poi in pois[:5]:
        cost_str = "免费" if poi.get("cost", 0) == 0 else f"门票{poi['cost']}元"
        name = poi.get("name", "")
        city = poi.get("city", "")
        cat = poi.get("category", "")
        dur = poi.get("duration", "")
        note = poi.get("note", "")
        parts.append(f"- {name}（{city}，{cat}）：{cost_str}，建议游玩{dur}。{note}")
    return "\n".join(parts)


def _fallback_answer(context: str) -> str:
    if not context:
        return "咕咕~ 我暂时没有相关信息，你可以试试换个问法！"
    answer = "咕咕~ 作为你的专属旅行信差 Crafty，我帮你查到了以下信息：\n\n"
    for line in context.split("\n")[:3]:
        answer += f"📍 {line}\n"
    return answer + "\n如果你想了解更详细的行程安排，可以在上方生成一份专属攻略。"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """流式 SSE 回答：先输出思考过程，再逐字输出 LLM 回答。"""
    start_time = time.time()

    async def event_stream():
        context = _retrieve_context(req.message, req.destination)

        thinking_steps = []
        if context:
            import re
            spots = re.findall(r"-\s*(.+?)（", context)
            thinking_steps.append("正在检索景点知识库...")
            thinking_steps.append(f"找到 {len(spots)} 个相关景点：{'、'.join(spots[:3])}")
        else:
            thinking_steps.append("知识库未检索到直接匹配，将基于旅行经验回答...")

        route = route_model_request("chat", destination=req.destination or "")
        thinking_steps.append(f"正在调用 {route.primary.model_id} 生成回答...")

        for step in thinking_steps:
            yield f"data: {json.dumps({'type': 'thinking', 'content': step}, ensure_ascii=False)}\n\n"

        if route.primary.available or route.fallback_allowed:
            system_prompt = (
                "你是 TripCraft 的旅行信差 Crafty，一只飞越了大江南北的信鸽。"
                '你性格活泼，说话以"咕咕~"开头，对各地景点、美食、交通了如指掌。'
                "请根据用户的问题和下方景点知识库信息，给出专业、简洁、有用的旅行建议。"
                "回答控制在 200 字以内，语气亲切但信息密度高。"
                "如果知识库信息为空，你可以根据自己的旅行经验回答。"
            )
            messages = [
                {"role": "system", "content": system_prompt + (f"\n\n景点知识库：\n{context}" if context else "")},
                {"role": "user", "content": req.message},
            ]
            providers = [route.primary] + ([route.fallback] if route.fallback_allowed else [])
            delivered = False
            for index, provider in enumerate(providers):
                if not provider.available:
                    continue
                provider_started = time.perf_counter()
                output_characters = 0
                try:
                    async for chunk in provider.stream_chat(messages, temperature=0.7, max_tokens=400):
                        delivered = True
                        output_characters += len(chunk)
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    logger.info(
                        "Chat Provider 完成",
                        extra={
                            "provider": provider.model_id.split(":", 1)[0],
                            "model": provider.model_id,
                            "latency": round((time.perf_counter() - provider_started) * 1000),
                            "tokens": max(1, output_characters // 4),
                            "cost": 0 if provider.model_id.startswith("ollama:") else None,
                            "route_reason": route.reason,
                            "fallback_reason": "primary_unavailable" if index else None,
                        },
                    )
                    break
                except ProviderUnavailableError as exc:
                    logger.warning(
                        "Chat Provider 不可用",
                        extra={
                            "provider": provider.model_id.split(":", 1)[0],
                            "model": provider.model_id,
                            "route_reason": route.reason,
                            "fallback_reason": str(exc),
                        },
                    )
                    if delivered:
                        break
            if not delivered:
                answer = _fallback_answer(context)
                yield f"data: {json.dumps({'type': 'content', 'content': answer}, ensure_ascii=False)}\n\n"
        else:
            answer = _fallback_answer(context)
            yield f"data: {json.dumps({'type': 'content', 'content': answer}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Chat 完成: {req.message[:30]}",
            extra={"method": "POST", "path": "/api/chat", "duration": duration_ms}
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
