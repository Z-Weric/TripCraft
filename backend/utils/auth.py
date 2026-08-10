"""JWT 认证工具 — 含 Redis 黑名单检查"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Header
from config import settings
from utils.logger import logger

JWT_SECRET = settings.siliconflow_api_key[:32] if settings.siliconflow_api_key else "tripcraft_secret_2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7


def create_token(user_id: int, email: str) -> str:
    """生成 JWT token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"JWT token 生成: user_id={user_id}")
    return token


def verify_token(token: str) -> Optional[dict]:
    """验证 JWT token，返回 payload 或 None"""
    try:
        # 检查 Redis 黑名单
        from utils.redis_client import is_token_blacklisted, get_redis
        r = get_redis()
        if r and is_token_blacklisted(token):
            return None

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """从请求头获取当前用户，未登录返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    payload = verify_token(token)
    return payload


async def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """要求用户登录，未登录抛 401"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user