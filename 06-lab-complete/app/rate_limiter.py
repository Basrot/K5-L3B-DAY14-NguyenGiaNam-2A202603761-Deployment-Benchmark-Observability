"""Atomic 60-second sliding window, shared across workers and restarts."""
import hashlib
import secrets

from fastapi import HTTPException

from app import redis_client
from app.config import settings

# Redis TIME avoids disagreement between clocks on different app instances.
# The whole read/check/write is atomic, including simultaneous first requests.
SLIDING_WINDOW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60000)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return {0, math.max(1, math.ceil((tonumber(oldest[2]) + 60000 - now) / 1000))}
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], 60000)
return {1, 0}
"""


def check_rate_limit(key: str) -> None:
    fingerprint = hashlib.sha256(key.encode("utf-8")).hexdigest()
    allowed, retry_after = redis_client.r.eval(
        SLIDING_WINDOW, 1, f"day14:rate:{fingerprint}",
        settings.rate_limit_per_minute, secrets.token_hex(16),
    )
    if not allowed:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
