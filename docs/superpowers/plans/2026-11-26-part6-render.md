# Part 6 Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Part 6, prove PASS 12/12, and deploy it with Redis on Render.
**Architecture:** FastAPI with shared Redis state; non-root Docker; Render web + Key Value.
**Tech Stack:** Python 3.11, FastAPI, redis-py, Docker, Render.
**Spec:** `docs/superpowers/specs/2026-11-26-part6-render-design.md`

## Global Constraints

- Keep code in `06-lab-complete/`; do not modify the grader or golden dataset.
- Image < 500 MB; SIGTERM drains requests; Docker stop < 10 seconds.
- Missing/wrong key 401, rate exceeded 429, exhausted budget 402, Redis outage 503.
- Run the full checker on Linux; no secrets or fabricated evidence in Git.

## Review Focus

- Simultaneous requests cannot bypass the per-key sliding window (Task 1).
- Two clients accumulate cost without lost updates (Task 1).
- Redis outage preserves liveness and blocks protected requests safely (Task 1).
- Empty input, missing key and LLM failure produce clear errors without traces (Task 1).
- Container respects custom PORT and drains SIGTERM (Task 2).

### Task 1: Agent behavior

**Files:** `06-lab-complete/app/{main,config,auth,redis_client,rate_limiter,cost_guard}.py`, `tests/test_agent.py`, `requirements-dev.txt`.
**Interfaces:** `verify_api_key() -> str`, `check_rate_limit(key: str) -> None`, `check_budget() -> None`, `record_cost(input_tokens: int, output_tokens: int) -> float`, `redis_healthy() -> bool`.

- [ ] Run unchanged grader baseline; expect missing production features.
- [ ] Add integration tests against a dedicated Redis DB; run and observe failures.
- [ ] Implement env configuration, safe auth, atomic Redis rate limit, daily ledger, JSON logs, endpoints and lifespan.
- [ ] Run integration tests; expect all passing.

### Task 2: Containers and deployment configuration

**Files:** Part 6 `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`, `render.yaml`, testing runner configuration.
**Interfaces:** `uvicorn app.main:app`, Docker PORT env; Render REDIS_URL from private datastore.

- [ ] Implement multi-stage runtime, non-root, health check and exec CMD; persistent Redis Compose.
- [ ] Define Render Free web + Key Value Blueprint, generated API key, Singapore region.
- [ ] Run static checks, build image and full Linux grader; expect PASS 12/12.
- [ ] Test custom PORT and Compose readiness; record actual output and image size.

### Task 3: Review and Render delivery

**Files:** `DEPLOYMENT.md`, `MISSION_ANSWERS.md` (Part 6 evidence and AI log only), verification reports.
**Interfaces:** public Render URL; expected status sequence 200, 200, 401, 200.

- [ ] Review diff and tests for concurrency, secrets, lifecycle and Render path correctness.
- [ ] Record verified results and commit/push the feature branch to the user's origin.
- [ ] Deploy Free services on Render through the available authenticated interface.
- [ ] Verify four public cases and update evidence, or state the precise login/account blocker.
