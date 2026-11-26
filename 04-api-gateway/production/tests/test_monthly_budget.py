"""Integration tests for Exercise 4.4 against a disposable Redis database."""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import redis

from monthly_budget import check_budget


class MonthlyBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = os.environ.get("LAB14_TEST_REDIS_URL")
        if not url:
            raise RuntimeError("Set LAB14_TEST_REDIS_URL to a disposable Redis database")
        cls.client = redis.Redis.from_url(url, decode_responses=True)
        cls.client.ping()

    def setUp(self):
        self.client.flushdb()

    def test_monthly_limit_and_reset_key(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(check_budget("student", 6, client=self.client, now=now))
        self.assertTrue(check_budget("student", 4, client=self.client, now=now))
        self.assertFalse(check_budget("student", 0.01, client=self.client, now=now))
        keys = self.client.keys("monthly_budget:*")
        self.assertEqual(len(keys), 1)
        self.assertEqual(int(self.client.get(keys[0])), 10_000_000_000)
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        self.assertEqual(self.client.expiretime(keys[0]), int(next_month.timestamp()))

    def test_users_are_separate(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(check_budget("a", 10, client=self.client, now=now))
        self.assertFalse(check_budget("a", 0.01, client=self.client, now=now))
        self.assertTrue(check_budget("b", 0.01, client=self.client, now=now))

    def test_concurrent_reservations_do_not_exceed_limit(self):
        now = datetime.now(timezone.utc)
        with ThreadPoolExecutor(max_workers=20) as pool:
            accepted = list(pool.map(
                lambda _: check_budget("concurrent", 0.6, client=self.client, now=now),
                range(20),
            ))
        self.assertEqual(sum(accepted), 16)

    def test_invalid_cost_rejected(self):
        for cost in (-1, float("nan"), float("inf")):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                check_budget("student", cost, client=self.client)


if __name__ == "__main__":
    unittest.main()
