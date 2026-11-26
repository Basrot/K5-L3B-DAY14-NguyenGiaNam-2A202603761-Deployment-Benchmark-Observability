# Part 6 and Render

Implement the existing Part 6 lab contract in `06-lab-complete/`, retaining FastAPI,
the supplied mock LLM, and the unmodified grading script. The user authorized
implementation and deployment on Render on 2026-11-26.

## Approach

Use the existing Python modules, a Redis sliding window shared by all workers,
and a daily UTC cost ledger in Redis. Redis failures return 503 from protected
requests and readiness; liveness remains 200. API keys come only from environment
variables, and logs never include keys or questions. Uvicorn drains requests on
SIGTERM and the FastAPI lifespan closes Redis afterward.

Docker uses a slim multi-stage build, non-root user, health check, and a dynamic
PORT. Compose supplies Redis with persistence. Render supplies a Docker web
service and a private Key Value service in the same region, both on Free plans.
Render Free datastore restarts can lose data; this lab deployment is a demo.

Manual Render setup is a fallback to the reproducible Blueprint. Railway and a
native Python Render runtime are unnecessary because the user selected Render
and the lab requires Docker. Do not add conversation history or Part 7 changes.

## Verification and delivery

Use real Redis for integration tests, including simultaneous rate-limit calls,
budget accumulation and outages. Run the unchanged full grader in Linux with
Docker access. Publish only verified code and test the four required HTTP cases
on Render. Record actual outputs, deployment status, and AI assistance; never
invent missing results. Credentials and login remain outside version control.
