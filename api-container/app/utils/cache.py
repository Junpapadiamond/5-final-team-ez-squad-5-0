from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

try:  # pragma: no cover - optional dependency
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

logger = logging.getLogger(__name__)


class RedisCache:
    """Lightweight wrapper around redis-py with graceful degradation."""

    _client: Optional["redis.Redis[Any]"] = None

    @classmethod
    def _enabled(cls) -> bool:
        return bool(os.getenv("REDIS_URL")) and redis is not None

    @classmethod
    def _get_client(cls) -> Optional["redis.Redis[Any]"]:
        if not cls._enabled():
            return None
        if cls._client is None:
            try:
                cls._client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
            except Exception as exc:  # pragma: no cover - connection failure
                logger.warning("Redis connection failed: %s", exc)
                cls._client = None
        return cls._client

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        client = cls._get_client()
        if client is None:
            return None
        try:
            value = client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:  # pragma: no cover - runtime redis failure
            logger.warning("Redis get failed for key %s: %s", key, exc)
            return None

    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: int) -> None:
        client = cls._get_client()
        if client is None:
            return
        try:
            client.setex(key, ttl_seconds, json.dumps(value))
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis set failed for key %s: %s", key, exc)


__all__ = ["RedisCache"]
