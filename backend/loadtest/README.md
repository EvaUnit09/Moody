# Moody Railway load test (Locust)

Simulates users typing mood queries against `POST /recommend`, plus lighter
`GET /popular` and `GET /health` traffic.

## Files

- `mood_queries.json` — 100 mood / scenario strings (1–200 chars, matching the API)
- `locustfile.py` — Locust user. 70% of recommend calls reuse the pool (cache hits), 30% append ` v{n}` from a pool of 20 (cache misses). 15% send a fixed `exclude_tmdb_ids` preset chosen from the base query. Locust stats are `/recommend hit` and `/recommend miss`.

## Before you run

Set `MOODY_HOST` in `backend/.env` to the target URL. The locustfile reads it through `settings.moody_host`. By default, **only localhost and 127.0.0.1 are allowed** to prevent accidental load testing of deployed services. All Railway, Vercel, and other deployed hosts are blocked unless `MOODY_ALLOW_PROD=1` is explicitly set.

`POST /recommend` on that branch is limited to **100 requests per minute per client IP** (`slowapi`, in-memory, first hop of `X-Forwarded-For`). One Locust process shares one IP. `/popular` and `/health` are not limited.

`wait_time` is `between(0.8, 2.0)`. Once cache hits are fast, that is about **15–20 recommend calls per minute per user**. Task weights are recommend 7, popular 2, health 1.

Suggested headless shape: `-u 4 -r 1 -t 2m` (about 60–80 recommend/min, near the ceiling). `-u 6` or more collects 429s. A 429 is a failure for this run.

1. Deploy a test branch with temporarily raised rate limits (production uses `10/minute`).
2. Deploy that branch to a Railway environment you can afford to hammer.
3. Point `MOODY_HOST` at that service and set `MOODY_ALLOW_PROD=1` to bypass the host guard.
4. Each cache-miss recommend calls Claude (expand + rerank) and OpenAI (embed). Cost scales with unique queries. `MOODY_MISS_POOL` (default 20) caps miss suffixes, so the distinct miss keys stop at `100 queries × pool size`. A fresh service has a cold cache, so the file pre-warms before the run (see below).

A high-VU run against the production URL mostly collects 429s and still pays for whatever misses get through.

## Run

From `backend/`, so `app.config` finds `.env`:

```bash
pip install locust
cd backend

# UI on http://localhost:8089
locust -f loadtest/locustfile.py

# Headless, requires raised limit on test branch (production is 10/minute)
locust -f loadtest/locustfile.py --headless -u 4 -r 1 -t 2m
```

`--host` overrides `settings.moody_host`. A longer miss sample is `MOODY_MISS_POOL=50` in the environment; that raises the LLM bill until the larger pool is warm.

### Warm-up

The `/recommend hit` stat is by intent, and on a cold service the first request for each cache key is a real miss. So before the run, the locustfile requests every key the hit path can use: each of the 100 moods, plus its exclude-preset variant. That is **200 real Claude/OpenAI calls**, sent below the rate limit, then a 60 second wait so the limiter's one-minute window resets. Expect roughly **3.5 minutes** before traffic starts. The `-t` timer starts after that, and warm-up requests are not in the Locust stats.

- If a 429 comes back, warm-up stops and logs an error. That means the deployed limiter is lower than the warm-up rate.
- In the web UI, wait for the `Warm-up done` log line before pressing Start. A host typed into the UI after startup is not warmed.
- `MOODY_WARMUP=0` skips it (hit p95 then includes cold misses). `MOODY_WARMUP_RATE` and `MOODY_WARMUP_SETTLE` change the pace and the wait.
- Warm-up runs only in a single-process run, not under `--master` or `--worker`.

Suggested SLO:

- `/recommend hit` p95 under 300 ms
- `/recommend miss` p95 under 3 s (LLM-bound)
- error rate under 1%, with 429 counted as a failure

Watch Datadog APM / LLM Observability during the run. The interesting split is cache hit vs miss, not raw RPS.
