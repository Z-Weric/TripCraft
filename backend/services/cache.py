"""缓存服务 — Redis 优先，内存降级

用于 POI 查询、景点详情、天气结果、排行榜等数据缓存。
"""

from typing import Any, Optional
from utils.redis_client import cache_get, cache_set, cache_delete, cache_delete_pattern, get_redis
from utils.logger import logger


class TTLCache:
    """内存降级缓存（Redis 不可用时使用）"""

    def __init__(self, default_ttl: int = 3600):
        self._store = {}
        self._default_ttl = default_ttl
        self._redis_available = False
        try:
            r = get_redis()
            self._redis_available = r is not None
        except Exception:
            self._redis_available = False

    def get(self, key: str) -> Optional[Any]:
        # 优先 Redis
        if self._redis_available:
            val = cache_get(key)
            if val is not None:
                return val

        # 降级内存
        import time
        if key not in self._store:
            return None
        value, expire_at = self._store[key]
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        # 优先 Redis
        if self._redis_available:
            cache_set(key, value, ttl or self._default_ttl)
            return

        # 降级内存
        import time
        expire_at = time.time() + (ttl or self._default_ttl)
        self._store[key] = (value, expire_at)

    def clear(self) -> None:
        if self._redis_available:
            cache_delete_pattern("*")
        self._store.clear()


# 全局缓存实例
poi_cache = TTLCache(default_ttl=3600)
amap_verify_cache = TTLCache(default_ttl=86400)

logger.info(f"缓存服务初始化 (Redis={'启用' if poi_cache._redis_available else '降级内存'})")