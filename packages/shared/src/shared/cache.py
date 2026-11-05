import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisJsonCache:
    def __init__(self, redis: Redis, namespace: str, ttl_seconds: int = 60) -> None:
        self.redis = redis
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds

    def key(self, suffix: str) -> str:
        return f"cache:{self.namespace}:{suffix}"

    async def get_or_load(
        self,
        suffix: str,
        loader: Callable[[], Awaitable[Any]],
    ) -> Any:
        key = self.key(suffix)
        try:
            cached = await self.redis.get(key)
        except RedisError:
            logger.warning("cache_read_unavailable", extra={"cache_key": key})
            return await loader()
        if cached is not None:
            return json.loads(cached)
        value = await loader()
        try:
            await self.redis.set(key, json.dumps(value, default=str), ex=self.ttl_seconds)
        except RedisError:
            logger.warning("cache_write_unavailable", extra={"cache_key": key})
        return value

    async def invalidate(self, *suffixes: str) -> None:
        if not suffixes:
            return
        try:
            await self.redis.delete(*(self.key(suffix) for suffix in suffixes))
        except RedisError:
            logger.warning("cache_invalidation_unavailable", extra={"namespace": self.namespace})

    async def bump_version(self, name: str = "version") -> int:
        try:
            return await self.redis.incr(self.key(name))
        except RedisError:
            logger.warning("cache_version_unavailable", extra={"namespace": self.namespace})
            return 0

    async def version(self, name: str = "version") -> int:
        try:
            return int(await self.redis.get(self.key(name)) or 0)
        except RedisError:
            return 0
