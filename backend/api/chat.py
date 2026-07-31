"""POST /api/chat — 桌宠客服 RAG 问答（流式 SSE 输出）"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from services.rag_service import search_pois_by_rag, is_index_ready

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    destination: Optional[str] = None


def _retrieve_context(question: str, destination: str = None) -> str:
    """通过 rag_service 检索景点，返回上下文文本。"""
    if not is_index_ready():
        return ""

    # 用 search_pois_by_rag 检索（不带偏好，取 top-5）
    pois = search_pois_by_rag(
        destination=destination or "",
        preferences=None,
        top_k=5,
    )

    # 如果没有指定城市，用全局检索结果
    if not pois:
        # 退化：直接用所有景点中 TF-IDF 最匹配的
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


@router.post("/api/chat")
def chat(req: ChatRequest):
    """流式 SSE 回答：先输出思考过程，再逐字输出 LLM 回答。"""

    def event_stream():
        # 1. 输出思考过程
        context = _retrieve_context(req.message, req.destination)

        thinking_steps = []
        if context:
            import re
            spots = re.findall(r"-\s*(.+?)（", context)
            thinking_steps.append("正在检索景点知识库...")
            thinking_steps.append(f"找到 {len(spots)} 个相关景点：{'、'.join(spots[:3])}")
        else:
            thinking_steps.append("知识库未检索到直接匹配，将基于旅行经验回答...")

        thinking_steps.append("正在调用 LongCat-2.0 生成回答...")

        for step in thinking_steps:
            yield f"data: {json.dumps({'type': 'thinking', 'content': step}, ensure_ascii=False)}\n\n"

        # 2. 流式输出 LLM 回答
        from services.llm_service import has_api_key, chat_with_context_stream

        if has_api_key():
            system_prompt = (
                "你是 TripCraft 的旅行信差 Crafty，一只飞越了大江南北的信鸽。"
                '你性格活泼，说话以"咕咕~"开头，对各地景点、美食、交通了如指掌。'
                "请根据用户的问题和下方景点知识库信息，给出专业、简洁、有用的旅行建议。"
                "回答控制在 200 字以内，语气亲切但信息密度高。"
                "如果知识库信息为空，你可以根据自己的旅行经验回答。"
            )
            try:
                for chunk in chat_with_context_stream(
                    system_prompt=system_prompt,
                    user_message=req.message,
                    context=context,
                    temperature=0.7,
                    max_tokens=400,
                ):
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'content', 'content': f'[LLM 调用失败: {e}]'}, ensure_ascii=False)}\n\n"
        else:
            # 降级：模板回答
            if context:
                answer = "咕咕~ 作为你的专属旅行信差 Crafty，我帮你查到了以下信息：\n\n"
                for line in context.split("\n")[:3]:
                    answer += f"📍 {line}\n"
                answer += "\n如果你想了解更详细的行程安排，可以在上方搜索栏生成一份专属攻略明信片哦~"
            else:
                answer = '咕咕~ 我暂时没有相关信息，你可以试试换个问法！'
            yield f"data: {json.dumps({'type': 'content', 'content': answer}, ensure_ascii=False)}\n\n"

        # 3. 结束信号
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )