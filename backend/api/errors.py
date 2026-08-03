"""统一异常定义"""

from fastapi import Request
from fastapi.responses import JSONResponse


class TripCraftError(Exception):
    """基础异常"""

    code: str = "TRIPCRAFT_ERROR"
    message: str = "服务异常"
    status_code: int = 500

    def __init__(self, message: str = None, code: str = None, status_code: int = None):
        if message:
            self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


class POINotFoundError(TripCraftError):
    code = "POI_NOT_FOUND"
    message = "暂不支持该目的地"
    status_code = 404


class LLMUnavailableError(TripCraftError):
    code = "LLM_UNAVAILABLE"
    message = "AI 模型暂时不可用"
    status_code = 503


class ValidationError(TripCraftError):
    code = "VALIDATION_ERROR"
    message = "行程验证失败"
    status_code = 422


async def trip_error_handler(request: Request, exc: TripCraftError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.code,
            "message": exc.message,
        },
    )