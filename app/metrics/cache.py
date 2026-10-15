import json
from datetime import datetime

from redis.asyncio import Redis

from app.shared.config import get_settings

_KEY = "changeface:metrics"
_LIMIT = 900


class SampleCache:
    def __init__(self) -> None:
        self._memory: list[dict] = []
        self._redis: Redis | None = None
        self._use_memory = False

    async def add(self, point: dict) -> None:
        client = await self._client()
        if client is None:
            self._memory.append(point)
            del self._memory[:-_LIMIT]
            return
        score = datetime.fromisoformat(point["sampled_at"]).timestamp()
        await client.zadd(_KEY, {json.dumps(point): score})
        count = await client.zcard(_KEY)
        if count > _LIMIT:
            await client.zremrangebyrank(_KEY, 0, count - _LIMIT - 1)

    async def all(self) -> list[dict]:
        client = await self._client()
        if client is None:
            return list(self._memory)
        raw = await client.zrange(_KEY, 0, -1)
        return [json.loads(item) for item in raw]

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _client(self) -> Redis | None:
        if self._use_memory:
            return None
        if self._redis is not None:
            return self._redis
        url = get_settings().redis_url
        if not url:
            self._use_memory = True
            return None
        client = Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            self._use_memory = True
            return None
        self._redis = client
        return client


cache = SampleCache()
