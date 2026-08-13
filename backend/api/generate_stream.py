"""POST /api/generate/stream — 流式行程生成（SSE）

分阶段推送进度：
1. rag_retrieval — 正在检索景点
2. llm_generating — 正在生成行程
3. verifying — 正在验证
4. done — 完成，返回完整行程 + 验证结果
5. error — 出错
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import time

from database.models import get_db
from schemas.generate import GenerateRequest
from services.generation_service import generate_events
from utils.logger import logger

router = APIRouter()


@router.post("/api/generate/stream")
async def generate_stream(req: GenerateRequest, db: Session = Depends(get_db)):
    """流式 SSE 行程生成"""

    async def event_stream():
        start_time = time.time()

        def emit(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            async for event in generate_events(req, db):
                payload = event.payload.model_dump()
                if event.kind == "progress":
                    yield emit({"type": "progress", **payload})
                    continue

                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"流式行程生成完成: {req.destination} {req.days}天",
                    extra={"method": "POST", "path": "/api/generate/stream", "duration": duration_ms}
                )
                yield emit({"type": "done", **payload})
        except LookupError as exc:
            logger.info(f"目的地无 POI: {req.destination}")
            yield emit({"type": "error", "message": str(exc)})
        except Exception as e:
            logger.error(f"行程生成失败: {e}")
            yield emit({"type": "error", "message": f"行程生成失败: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
