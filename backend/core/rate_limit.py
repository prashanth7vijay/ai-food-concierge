"""
Rate limiting.

Trade-off (see README section 18): Redis gives correct rate limiting across
multiple backend instances/processes. The in-memory fallback below is
correct only within a single process, which is fine for local dev/demo but
NOT for a multi-instance production deployment — that's the actual reason
Redis is in the stack rather than "PostgreSQL-only" or "in-memory only".
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from backend.core.config import get_settings

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib: Any = None


class _InMemoryLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        q = self._hits[key]
        while q and q[0] < now - window_seconds:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


class _RedisLimiter:
    def __init__(self, url: str):
        self.client = redis_lib.from_url(url)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        pipe = self.client.pipeline()
        redis_key = f"ratelimit:{key}"
        pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, window_seconds)
        _, count, _, _ = pipe.execute()
        return count < limit


_limiter = None


def get_rate_limiter():
    global _limiter
    if _limiter is not None:
        return _limiter
    settings = get_settings()
    if settings.REDIS_URL and redis_lib is not None:
        try:
            _limiter = _RedisLimiter(settings.REDIS_URL)
            _limiter.client.ping()
            return _limiter
        except Exception:  # noqa: BLE001 - fall back cleanly if Redis is unreachable
            pass
    _limiter = _InMemoryLimiter()
    return _limiter
