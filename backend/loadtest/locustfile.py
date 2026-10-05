"""Locust load test for Moody's Railway backend.

Targets:
  POST /recommend  — mood query, occasional exclude list
  GET  /popular    — cheap cached read
  GET  /health     — liveness

POST /recommend is limited to 100/minute per client IP (slowapi, in-memory,
keyed off X-Forwarded-For). A single Locust process shares one IP, and
wait_time below gives roughly 15-20 recommend calls/min per user, so
`-u 4` sits near the ceiling. 429s count as failures.

The host comes from `settings.moody_host` (MOODY_HOST in backend/.env).
Point it at the Railway test branch, never production. `--host` overrides it,
and a host containing "production" is refused unless MOODY_ALLOW_PROD=1.

Stats are split into "/recommend hit" and "/recommend miss". The split is by
intent, so before the run starts the file warms every cache key the hit path
can use (each mood, plus its exclude-preset variant) at ~80/min, then waits one
rate-limit window. That is 200 real LLM calls and about 3.5 minutes before the
run begins; the `-t` timer does not include it. Warm-up requests are not in the
stats. Set MOODY_WARMUP=0 to skip it (hit p95 then includes cold misses), or
tune MOODY_WARMUP_RATE / MOODY_WARMUP_SETTLE. With the web UI, wait for the
"Warm-up done" log line before pressing Start.

Usage (from backend/, so .env is found):
  locust -f loadtest/locustfile.py

Headless sanity check (about 4 users, 2 minutes):
  locust -f loadtest/locustfile.py --headless -u 4 -r 1 -t 2m
"""

import json
import logging
import os
import random
import sys
import zlib
from pathlib import Path

import gevent
import requests
from locust import HttpUser, between, events, task
from locust.runners import LocalRunner

# Locust only puts loadtest/ on sys.path, and Settings() reads .env from the
# working directory, so anchor both on backend/ before importing the app.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from app.config import settings  # noqa: E402

QUERIES_PATH = Path(__file__).with_name("mood_queries.json")
MOOD_QUERIES: list[str] = json.loads(QUERIES_PATH.read_text())

# Distinct " v{n}" suffixes for the miss path. Distinct miss keys top out at
# len(MOOD_QUERIES) * MISS_POOL, which caps Claude/OpenAI spend on long runs.
MISS_POOL = max(1, int(os.getenv("MOODY_MISS_POOL", "20")))
MISS_RATE = 0.30
EXCLUDE_RATE = 0.15

# The cache key includes the sorted exclude ids, so a random subset is a new
# key every call and always misses. A mood maps to one fixed preset instead,
# so repeat requests for it can still hit.
EXCLUDE_PRESETS: list[list[int]] = [[550], [680, 13], [155]]

# Pre-warm: the "hit" stat is by intent, and on a cold service the first request
# for every cache key is really a miss. Warming those keys first keeps that
# latency out of /recommend hit. Costs one Claude/OpenAI call per key
# (2 * len(MOOD_QUERIES), since each mood also has its exclude-preset variant).
WARMUP_ENABLED = os.getenv("MOODY_WARMUP", "1") != "0"
# Stay under the 100/min recommend limit while warming.
WARMUP_PER_MINUTE = max(1, int(os.getenv("MOODY_WARMUP_RATE", "80")))
# slowapi uses a fixed 1-minute window. Waiting one window after the last warm
# request means the real run starts with a fresh budget instead of 429ing.
WARMUP_SETTLE_SECONDS = max(0, int(os.getenv("MOODY_WARMUP_SETTLE", "60")))

log = logging.getLogger(__name__)


def _refuse_production(host: str | None) -> None:
    if host and "production" in host.lower() and os.getenv("MOODY_ALLOW_PROD") != "1":
        raise SystemExit(
            f"Refusing to load test {host}: it looks like production. "
            "Point MOODY_HOST at the Railway test branch (or set MOODY_ALLOW_PROD=1)."
        )


def _exclude_preset(base_query: str) -> list[int]:
    # crc32, not hash(): str hashes are salted per process, which would give
    # each Locust worker a different preset for the same mood.
    return EXCLUDE_PRESETS[zlib.crc32(base_query.encode()) % len(EXCLUDE_PRESETS)]


class MoodyUser(HttpUser):
    host = settings.moody_host
    wait_time = between(0.8, 2.0)

    def on_start(self) -> None:
        # warm session
        self.client.get("/popular", name="/popular")
        self.client.get("/health", name="/health")

    @task(7)
    def recommend(self) -> None:
        base_query = random.choice(MOOD_QUERIES)
        if random.random() < MISS_RATE:
            query = f"{base_query} v{random.randrange(MISS_POOL)}"[:200]
            stat_name = "/recommend miss"
        else:
            query = base_query
            stat_name = "/recommend hit"

        body: dict = {"query": query, "region": "US"}
        if random.random() < EXCLUDE_RATE:
            # Hash the unsuffixed mood so "x" and "x v3" share one preset.
            body["exclude_tmdb_ids"] = _exclude_preset(base_query)

        with self.client.post(
            "/recommend",
            json=body,
            name=stat_name,
            catch_response=True,
            timeout=30,
        ) as response:
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    response.failure("non-json 200")
                    return
                if "results" not in payload:
                    response.failure("missing results")
                    return
                response.success()
            elif response.status_code == 429:
                response.failure("rate limited")
            else:
                response.failure(f"status {response.status_code}: {response.text[:180]}")

    @task(2)
    def popular(self) -> None:
        self.client.get("/popular", name="/popular", timeout=15)

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="/health", timeout=10)


def _warm_cache(host: str) -> None:
    """Request every cache key the hit path can use, once, below the rate limit.

    Uses plain requests, so none of this lands in Locust's stats.
    """
    bodies: list[dict] = []
    for mood in MOOD_QUERIES:
        bodies.append({"query": mood, "region": "US"})
        bodies.append({"query": mood, "region": "US", "exclude_tmdb_ids": _exclude_preset(mood)})

    interval = 60 / WARMUP_PER_MINUTE
    log.info(
        "Warming %d cache keys at ~%d/min (about %ds), then settling %ds",
        len(bodies), WARMUP_PER_MINUTE, int(len(bodies) * interval), WARMUP_SETTLE_SECONDS,
    )

    url = f"{host.rstrip('/')}/recommend"
    session = requests.Session()
    failures = 0
    rate_limited = False

    def send(body: dict) -> None:
        nonlocal failures, rate_limited
        try:
            response = session.post(url, json=body, timeout=30)
        except requests.RequestException as exc:
            failures += 1
            log.warning("warm-up request failed: %s", exc)
            return
        if response.status_code == 429:
            rate_limited = True
        elif response.status_code != 200:
            failures += 1
            log.warning("warm-up got %s for %r", response.status_code, body["query"])

    jobs = []
    for body in bodies:
        if rate_limited:
            break
        jobs.append(gevent.spawn(send, body))
        gevent.sleep(interval)
    gevent.joinall(jobs)

    if rate_limited:
        log.error(
            "Warm-up hit a 429 and stopped early. The deployed limiter is lower than the "
            "100/min this test assumes, so hit latency will still include cold misses."
        )
    log.info("Warm-up sent %d/%d keys (%d failed)", len(jobs), len(bodies), failures)
    if jobs and WARMUP_SETTLE_SECONDS:
        log.info("Settling %ds so the rate-limit window resets", WARMUP_SETTLE_SECONDS)
        gevent.sleep(WARMUP_SETTLE_SECONDS)
    log.info("Warm-up done. If you are using the web UI, you can start the test now.")


@events.init.add_listener
def _on_init(environment, **_kwargs) -> None:
    # environment.host is the --host value; fall back to the .env value.
    host = environment.host or MoodyUser.host
    # Guard first, so a production host exits before any warm-up traffic.
    _refuse_production(host)

    if not WARMUP_ENABLED:
        return
    # Warm once, from the process that generates load. Master/worker setups
    # would otherwise warm once per process.
    if not isinstance(environment.runner, LocalRunner):
        return
    if not host:
        log.info("No host yet (it will come from the web UI), so skipping warm-up")
        return
    _warm_cache(host)


@events.test_start.add_listener
def _check_host_on_start(environment, **_kwargs) -> None:
    # Covers a host typed into the web UI after startup.
    try:
        _refuse_production(environment.host or MoodyUser.host)
    except SystemExit as exc:
        log.error("%s", exc)
        environment.process_exit_code = 1
        environment.runner.quit()
