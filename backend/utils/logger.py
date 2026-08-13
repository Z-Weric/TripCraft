"""结构化日志 — JSON 格式，便于排查和监控"""

import logging
import sys
import json
from contextvars import ContextVar, Token
from datetime import datetime
from uuid import uuid4


_request_id: ContextVar[str] = ContextVar("tripcraft_request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str | None = None) -> Token:
    return _request_id.set(value or uuid4().hex)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 附加字段
        for key in (
            "method",
            "path",
            "status",
            "duration",
            "error",
            "provider",
            "model",
            "tokens",
            "latency",
            "cost",
            "route_reason",
            "fallback_reason",
            "validation_status",
        ):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """配置全局日志"""
    logger = logging.getLogger("tripcraft")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger


logger = setup_logging()
