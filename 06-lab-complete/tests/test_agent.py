"""Behavior tests using an isolated Redis DB, never a deployed datastore.

Run with TEST_REDIS_URL pointing to a disposable Redis instance (DB 15).
"""
import json
import logging
import os
import secrets
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import redis

os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ["AGENT_API_KEY"] = secrets.token_urlsafe(24)
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["DAILY_BUDGET_USD"] = "1000"

from app import main, redis_client
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.redis = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        if self.redis.connection_pool.connection_kwargs.get("db") != 15:
            raise RuntimeError("Tests require disposable Redis DB 15")
        self.redis.flushdb()
        settings.rate_limit_per_minute = 1000
        settings.daily_budget_usd = 1000
        self.client = TestClient(main.app, raise_server_exceptions=False)
        self.headers = {"X-API-Key": settings.agent_api_key}

    def tearDown(self):
        self.client.close()
        self.redis.flushdb()
        self.redis.close()

    def ask(self, **kwargs):
        return self.client.post("/ask", headers=self.headers,
                                json={"question": "What is deployment?"}, **kwargs)

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 200)

    def test_missing_wrong_and_empty_keys_are_rejected(self):
        for headers in ({}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}):
            response = self.client.post("/ask", headers=headers, json={"question": "Hello"})
            self.assertEqual(response.status_code, 401)

    def test_valid_request_and_estimated_usage(self):
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["answer"])
        self.assertGreater(body["usage"]["input_tokens"], 0)
        self.assertGreater(body["usage"]["cost_usd"], 0)

    def test_empty_input_is_rejected(self):
        response = self.client.post("/ask", headers=self.headers, json={"question": ""})
        self.assertEqual(response.status_code, 422)

    def test_whitespace_input_is_rejected(self):
        response = self.client.post("/ask", headers=self.headers, json={"question": "   "})
        self.assertEqual(response.status_code, 422)

    def test_sliding_window_limits_exactly_five_concurrent_calls(self):
        settings.rate_limit_per_minute = 5
        key = secrets.token_hex(12)

        def attempt(_):
            try:
                check_rate_limit(key)
                return 200
            except HTTPException as exc:
                self.assertEqual(exc.headers["Retry-After"].isdigit(), True)
                return exc.status_code

        with ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(attempt, range(30)))
        self.assertEqual(codes.count(200), 5)
        self.assertEqual(codes.count(429), 25)

    def test_rate_limit_keeps_different_keys_separate(self):
        settings.rate_limit_per_minute = 1
        check_rate_limit("first")
        check_rate_limit("second")
        with self.assertRaises(HTTPException) as error:
            check_rate_limit("first")
        self.assertEqual(error.exception.status_code, 429)

    def test_rate_window_expires(self):
        # Redis's clock: requests older than 60 seconds must not block new ones.
        settings.rate_limit_per_minute = 1
        check_rate_limit("expired")
        for key in self.redis.scan_iter(match="*:rate:*"):
            for member in self.redis.zrange(key, 0, -1):
                self.redis.zadd(key, {member: 0})
        check_rate_limit("expired")

    def test_daily_cost_accumulates_atomically(self):
        settings.daily_budget_usd = 0.014
        with ThreadPoolExecutor(max_workers=10) as pool:
            costs = list(pool.map(lambda _: record_cost(1000, 1000), range(20)))
        self.assertAlmostEqual(sum(costs), 0.015, places=9)
        with self.assertRaises(HTTPException) as error:
            check_budget()
        self.assertEqual(error.exception.status_code, 402)

    def test_tiny_budget_blocks_subsequent_request(self):
        settings.daily_budget_usd = 0.000001
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(self.ask().status_code, 402)

    def test_zero_budget_blocks_first_request(self):
        settings.daily_budget_usd = 0
        self.assertEqual(self.ask().status_code, 402)

    def test_redis_outage_keeps_liveness_but_blocks_requests(self):
        unavailable = redis.from_url("redis://127.0.0.1:1/15", socket_connect_timeout=0.1,
                                     socket_timeout=0.1)
        with patch.object(redis_client, "r", unavailable):
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.get("/ready").status_code, 503)
            self.assertEqual(self.ask().status_code, 503)
        unavailable.close()

    def test_upstream_failure_has_no_traceback(self):
        with patch.object(main, "llm_ask", side_effect=RuntimeError("private upstream data")):
            response = self.ask()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private upstream data", response.text)
        self.assertNotIn("Traceback", response.text)

    def test_request_logs_are_json_without_credentials_or_question(self):
        messages = []

        class Capture(logging.Handler):
            def emit(self, record):
                messages.append(self.format(record))

        capture = Capture()
        capture.setFormatter(main.logger.handlers[0].formatter)
        main.logger.addHandler(capture)
        try:
            self.ask()
        finally:
            main.logger.removeHandler(capture)
        self.assertTrue(messages)
        for message in messages:
            self.assertIsInstance(json.loads(message), dict)
            self.assertNotIn(settings.agent_api_key, message)
            self.assertNotIn("What is deployment?", message)


if __name__ == "__main__":
    unittest.main()
