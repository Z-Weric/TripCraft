"""Redis 客户端 — 验证码 / Token 黑名单 / 数据缓存 / 热点数据"""

import json
import redis
from typing import Any, Optional
from datetime import timedelta
from config import settings
from utils.logger import logger

# 连接 Redis
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=getattr(settings, "redis_host", "localhost"),
            port=getattr(settings, "redis_port", 6379),
            db=getattr(settings, "redis_db", 0),
            password=getattr(settings, "redis_password", None),
            decode_responses=True,
        )
        try:
            _redis_client.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            _redis_client = None
    return _redis_client


# ===== 验证码 =====

def set_verification_code(email: str, code: str, expire: int = 300) -> bool:
    """存储验证码，5 分钟过期"""
    r = get_redis()
    if not r:
        return False
    r.setex(f"verify:{email}", expire, code)
    return True


def get_verification_code(email: str) -> Optional[str]:
    r = get_redis()
    if not r:
        return None
    return r.get(f"verify:{email}")


def delete_verification_code(email: str) -> None:
    r = get_redis()
    if r:
        r.delete(f"verify:{email}")


# ===== Token 黑名单 =====

def blacklist_token(token: str, expire: int = 604800) -> bool:
    """将 token 加入黑名单（7 天过期，和 JWT 有效期一致）"""
    r = get_redis()
    if not r:
        return False
    r.setex(f"blacklist:{token}", expire, "1")
    return True


def is_token_blacklisted(token: str) -> bool:
    r = get_redis()
    if not r:
        return False
    return r.exists(f"blacklist:{token}") > 0


# ===== 数据缓存 =====

def cache_get(key: str) -> Optional[Any]:
    """获取缓存数据（自动 JSON 反序列化）"""
    r = get_redis()
    if not r:
        return None
    val = r.get(f"cache:{key}")
    if val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """设置缓存数据（自动 JSON 序列化）"""
    r = get_redis()
    if not r:
        return False
    r.setex(f"cache:{key}", ttl, json.dumps(value, ensure_ascii=False, default=str))
    return True


def cache_delete(key: str) -> None:
    r = get_redis()
    if r:
        r.delete(f"cache:{key}")


def cache_delete_pattern(pattern: str) -> None:
    """按模式删除缓存"""
    r = get_redis()
    if r:
        for key in r.scan_iter(f"cache:{pattern}"):
            r.delete(key)