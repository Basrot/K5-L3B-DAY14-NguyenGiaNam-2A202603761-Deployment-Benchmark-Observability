"""Exercise 4.4: atomic per-user, $10/month cost reservation in Redis.

The sample ``cost_guard.py`` demonstrates a daily in-memory guard. This module
implements the separate monthly Redis requirement from CODE_LAB.md.
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from functools import lru_cache

import redis


NANO_USD = Decimal("1000000000")
MONTHLY_LIMIT_USD = Decimal("10")

_RESERVE_SCRIPT = """
local spent = tonumber(redis.call('GET', KEYS[1]) or '0')
local cost = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
if spent + cost > limit then
    return 0
end
redis.call('INCRBY', KEYS[1], cost)
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
"""


@lru_cache(maxsize=8)
def _client(url: str) -> redis.Redis:
    return redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)


def _to_nano_usd(value: float | Decimal) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Cost must be a finite, non-negative number") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Cost must be a finite, non-negative number")
    return int((amount * NANO_USD).to_integral_value(rounding=ROUND_CEILING))


def check_budget(
    user_id: str,
    estimated_cost: float | Decimal,
    *,
    client: redis.Redis | None = None,
    now: datetime | None = None,
) -> bool:
    """Reserve estimated cost for this user in the current UTC month.

    Returns False if this reservation would exceed $10. Redis errors propagate,
    so the caller should reject the request rather than allow untracked spend.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string")
    cost = _to_nano_usd(estimated_cost)
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    instant = instant.astimezone(timezone.utc)
    next_month = (instant.replace(day=28) + timedelta(days=4)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    fingerprint = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    key = f"monthly_budget:{instant:%Y-%m}:{fingerprint}"
    store = client if client is not None else _client(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    return bool(store.eval(
        _RESERVE_SCRIPT,
        1,
        key,
        cost,
        _to_nano_usd(MONTHLY_LIMIT_USD),
        int(next_month.timestamp()),
    ))
