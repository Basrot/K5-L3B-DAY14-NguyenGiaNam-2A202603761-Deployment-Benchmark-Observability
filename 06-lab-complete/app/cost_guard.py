"""Shared daily UTC budget. Integer nano-USD avoids accumulated float error."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app import redis_client
from app.config import settings

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006
NANO_USD = 1_000_000_000


def _daily_ledger() -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return f"day14:cost:{now:%Y-%m-%d}", int(tomorrow.timestamp())


def check_budget() -> None:
    key, _ = _daily_ledger()
    spent = int(redis_client.r.get(key) or 0)
    if spent >= round(settings.daily_budget_usd * NANO_USD):
        raise HTTPException(status_code=402, detail="Daily budget exhausted")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")
    cost_nano = round((input_tokens * PRICE_INPUT_PER_1K +
                       output_tokens * PRICE_OUTPUT_PER_1K) * NANO_USD / 1000)
    key, expires_at = _daily_ledger()
    with redis_client.r.pipeline(transaction=True) as pipeline:
        pipeline.incrby(key, cost_nano)
        pipeline.expireat(key, expires_at)
        pipeline.execute()
    return cost_nano / NANO_USD
