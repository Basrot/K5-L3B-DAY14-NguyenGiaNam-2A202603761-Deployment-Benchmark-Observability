"""Part 6 production agent: authenticated, bounded and observable."""
import json
import logging
import math
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from redis.exceptions import RedisError

from app import redis_client
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("day14.agent")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    # Uvicorn owns SIGTERM and drains requests before exiting this lifespan.
    yield
    redis_client.r.close()
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank")
        return value


@app.middleware("http")
async def observe_request(request: Request, call_next):
    started = time.perf_counter()
    request_id = secrets.token_hex(12)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    route = request.scope.get("route")
    logger.info("request", extra={"fields": {
        "request_id": request_id, "method": request.method,
        "path": route.path if route else "unmatched", "status": response.status_code,
        "ms": round((time.perf_counter() - started) * 1000, 2),
    }})
    return response


@app.exception_handler(RedisError)
async def redis_error_handler(request: Request, exc: RedisError):
    logger.warning("redis_unavailable", extra={"fields": {"error_type": type(exc).__name__}})
    return JSONResponse(status_code=503, content={"detail": "State store unavailable"},
                        headers={"Retry-After": "1"})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.error("request_failed", extra={"fields": {"error_type": type(exc).__name__}})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_client.redis_healthy():
        raise HTTPException(status_code=503, detail="State store unavailable")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, key: Annotated[str, Depends(verify_api_key)]):
    check_rate_limit(key)
    check_budget()
    try:
        answer = llm_ask(body.question)
    except Exception as exc:
        logger.error("llm_error", extra={"fields": {"error_type": type(exc).__name__}})
        raise HTTPException(status_code=502, detail="LLM service unavailable") from None
    # Mock counts are estimates for the lab, not actual provider billing.
    input_tokens = max(1, math.ceil(len(body.question) / 4))
    output_tokens = max(1, math.ceil(len(answer) / 4))
    cost = record_cost(input_tokens, output_tokens)
    return {
        "question": body.question, "answer": answer,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                  "cost_usd": cost, "estimated": True},
    }
