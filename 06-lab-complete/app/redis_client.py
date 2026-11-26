"""Lazy, bounded Redis connections shared by this worker's threads."""
import redis

from app.config import settings

# Client creation does not connect: /health works even while Redis is down.
r = redis.from_url(
    settings.redis_url, decode_responses=True,
    socket_connect_timeout=1, socket_timeout=1,
    retry_on_timeout=False, max_connections=32,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
