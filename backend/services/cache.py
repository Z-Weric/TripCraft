"""内存缓存 — TTL 机制，用于 POI 查询和高德验证结果缓存"""

import time
from typing import Any, Dict, Optional, Tuple
from utils.logger import logger


class TTLCache:
    """简易 TTL 缓存，线程安全由 GIL 保证（单进程足够）"""

    def __init__(self, default_ttl: int = 3600):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expire_at = self._store[key]
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        expire_at = time.time() + (ttl or self._default_ttl)
        self._store[key] = (value, expire_at)

    def clear(self) -> None:
        self._store.clear()

    def cleanup_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(expired)


# 全局缓存实例
poi_cache = TTLCache(default_ttl=3600)          # POI 查询缓存 1h
amap_verify_cache = TTLCache(default_ttl=86400)  # 高德验证缓存 24h

logger.info("缓存服务初始化完成")