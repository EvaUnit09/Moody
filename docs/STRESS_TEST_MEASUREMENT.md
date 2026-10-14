# About the three open stress-test questions

Branch: `cursor/measure-stress-open-questions-9b14`. Date: 2026-10-14. Measurement code: `9dd96c9`.

This is a measurement report, not a fix. It answers the three unchecked items in [STRESS_TEST.md](STRESS_TEST.md). Noah reviews this PR before any follow-up change lands. Do not merge it as a product change.

This rerun had live-looking secrets injected (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_DB_URL`, `TMDB_API_READ_TOKEN`, `DD_API_KEY`) and `MOODY_HOST` pointing at the Railway test service. OpenAI embeddings, Supabase pgvector, and TMDB all succeeded. Anthropic rejected the injected key (`invalid x-api-key`, HTTP 401) on every Messages API call. `/recommend` on the test host and on the local uvicorn therefore 500s before `Server-Timing` is written. Quality scores, rerank-stage p50/p95, token correlation, and a baseline-shaped Locust hit/miss report are **INCONCLUSIVE**. The limiter is Anthropic authentication, not missing env names.

## Verdict

| Question | Verdict | Sample size | What we have |
| --- | --- | --- | --- |
| 1. Quality on main vs pre-#22 | INCONCLUSIVE | 0 scored queries. 5 interleaved process-pairs attempted (10 `run_eval` processes, 9 queries queued each). | Every process died on the first Anthropic call with 401. No pass/fail per query. No dropped-query list. |
| 2. Rerank ~2.7 s, generation vs overhead | INCONCLUSIVE | 0 successful misses with `Server-Timing` or `rerank_in`/`rerank_out`. Probe N=15 POST `/recommend` to the test host, all 500. Local POST N=1, 500 with Anthropic 401 in the uvicorn traceback. | Cannot say whether the ~2.7 s is output generation or fixed overhead. Datadog API key validates; span/log search returns 401 without an application key. |
| 3. Locust hit p95 and miss p95 | INCONCLUSIVE for latency. Failures are the result. | Abortive Locust: 1 user, 30 s, `MOODY_WARMUP=0`. `/recommend hit` 6/6 failed, `/recommend miss` 2/2 failed, `/popular` 6/6 200, `/health` 2/2 200. | Full `-u 4 -r 1 -t 2m` warmup (200 real LLM keys) was not run. `/recommend` 500s; warmup would have spent the ceiling on errors. |

Do not read Locust p95 1600 ms (hit-intent) / 2800 ms (miss-intent) as SLO numbers. Those are 500-response times.

## Preflight

Checked in this Cloud Agent VM with `printenv` name listing only (no values), `backend/.env` (absent), and live HTTP probes. `MOODY_ALLOW_PROD=1` was set only after confirming the host is not production.

| Name | This environment |
| --- | --- |
| `ANTHROPIC_API_KEY` | set (len 108, `sk-ant` prefix). Anthropic HTTP 401 `invalid x-api-key` |
| `OPENAI_API_KEY` | set. Live `embed_text` succeeded (dim 1536, 906 ms) |
| `SUPABASE_DB_URL` | set. Live `search_similar` succeeded (3 rows, 1453 ms) |
| `TMDB_API_READ_TOKEN` | set. `GET /3/authentication` 200 `success=true`; watch providers 200 |
| `DD_API_KEY` | set. `GET /api/v1/validate` 200 `{"valid": ...}`. Span/log search 401 (no application key) |
| `DD_SITE` | set (value omitted; US1-style Datadog site) |
| `MOODY_HOST` | set. Railway `*.up.railway.app` test hostname, not production |
| `MOODY_ALLOW_PROD` | set to `1` after the production check |

Production URL `https://moody-production-87c7.up.railway.app` was **not** used as `MOODY_HOST` and was not POSTed.

```
$ python3 -c "import os; h=os.environ['MOODY_HOST'].rstrip('/'); print('is_prod', h=='https://moody-production-87c7.up.railway.app'); print('test_railway', h.endswith('.up.railway.app') and 'production' not in h)"
is_prod False
test_railway True

$ curl -sS -o /tmp/health.json -w "%{http_code}\n" "$MOODY_HOST/health"
200
{"status":"ok"}

$ curl -sS -o /tmp/popular.json -w "%{http_code} %{size_download}\n" "$MOODY_HOST/popular"
200 2756
```

Machine at measurement time: 4 cores, `load average: 0.25, 0.15, 0.09`, idle. The limiter of the failed runs is the Anthropic 401, not CPU.

Live OpenAI + Supabase smoke (from `backend/`, venv Python):

```
pool_ok 0.71
embed_ok dim 1536 ms 906.0
search_ok n 3 titles ['Autumn Almanac', 'Love the Coopers', 'An Autumn Romance'] ms 1453.2
```

Anthropic auth check (models list and a 8-token message; key passed via env, not printed):

```
models_status 401
models_error_type authentication_error
messages_status 401
messages_error_type authentication_error
messages_error_message_kind invalid x-api-key
```

Request ids from Anthropic (not secrets): `req_011Cg2Ko3a15NGM49zJCYPAs` (eval main_1 rerank), `req_011Cg2KoKt32YJVoHnL9Vrfk` (eval pre22_1 expand), `req_011Cg2L1Qg6uuJPdYfTxGCwn` (local `/recommend` expand).

## 1. Quality

Claim we wanted: pass rate and per-query pass/fail for the 9-query harness on main (25 candidates, gated expansion, 300-character overviews, `max_tokens` 512, 15-word reason cap) versus pre-#22 settings from `eb32d87` (limit=40 passed explicitly, always expand, full overviews, `max_tokens` 1024, no reason cap), same eval set, with every dropped query named.

How pre-#22 was applied: measurement-only env `MOODY_EVAL_PRE_22=1` in `app/services/eval.py`. It patches `should_expand` to always true, passes `search_similar(..., limit=40)`, restores the `eb32d87` rerank tool/prompt (full overviews, 1024 tokens, uncapped reason). `/recommend` does not read this env. Confirmed by unit tests (`tests/test_eval.py`).

Command (correct module name, no `.py`):

```
$ cd backend
$ python -m app.scripts.run_eval --json --verbose
$ MOODY_EVAL_PRE_22=1 python -m app.scripts.run_eval --json --verbose
```

Benchmark checklist asked for a choice, not a ballpark, so the two sides were alternated 5 times (main, pre-22, main, pre-22, …). `DD_TRACE_ENABLED=false` for these processes so a missing Datadog agent did not add noise.

| Side | Processes | Elapsed (s) | JSON summary | Queries scored | Pass rate |
| --- | --- | --- | --- | --- | --- |
| main | 5 | 5.0, 3.9, 3.8, 3.7, 4.0 | none | 0 | n/a |
| pre-#22 | 5 | 3.3, 3.2, 3.2, 3.2, 3.3 | none | 0 | n/a |

Main dies on `rerank` for the first query (`something slow and melancholic...`, ≥3 words, so `should_expand` is false). Pre-#22 dies on `expand_query` for that same first query because the toggle always calls Haiku.

```
$ python -m app.scripts.run_eval --json --verbose
[Eval] Starting evaluation harness...
anthropic.AuthenticationError: Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011Cg2Ko3a15NGM49zJCYPAs'}
```

**Queries that dropped:** none can be named. A drop needs a query that fails on one side and passes on the other. Both sides scored 0 queries.

**Benchmark checklist.** Sample size 0 live evals that completed the 9-query set. Cold vs warm n/a. Errors: 10/10 processes, 0 queries. Limiter: Anthropic 401, reproduced on models list, Messages, eval rerank, eval expand, and local `/recommend`. The eval harness and the pre-#22 toggle did run; the model call did not succeed. `TMDB_API_READ_TOKEN` is not required for `run_eval`.

## 2. Miss latency and rerank tokens

Claim we wanted: p50/p95/max per stage from `Server-Timing` and `StageTimer`, plus rerank input and output tokens, optional time to first token, and latency versus output length, so we can say whether the ~2.7 s rerank p50 is output generation or fixed overhead.

The Railway test service accepts GET `/health` and GET `/popular`. POST `/recommend` returns 500 with no `Server-Timing`. The header is only attached after a successful miss path in `recommend.py`, so a crash inside expand/rerank never emits stage timings or `rerank_in`/`rerank_out`.

Probe, unique-enough miss body then 14 repeats of the same body (would have been cache hits if the first had 200'd). `MOODY_ALLOW_PROD=1` set. Host is not production.

```
MISS1 {"status": 500, "elapsed_ms": 4699.0, "server_timing": null, "body": "Internal Server Error"}
BURST_STATUSES {500: 14}
BURST_ELAPSED [1632.1, 1273.5, 1070.9, 627.2, 946.3, 555.4, 619.6, 633.6, 705.7, 540.2, 930.4, 536.3, 562.3, 557.8]
BURST_TIMING_PRESENT 0
```

Further payloads, including `"Fall"` (286.7 ms) and a long descriptive query (2213.3 ms), also 500 with no `Server-Timing`. The long-query delay is in the same band as local embed+search (906+1453 ms), which matches “OpenAI and Supabase work, Anthropic fails at rerank.”

Local uvicorn already running in this VM (`127.0.0.1:8000`, session `api`) on this branch. POST `/recommend` with sentinel exclude:

```
status 500 ms 173.8 timing None
```

Uvicorn traceback (expand on `"Fall"`):

```
File "/workspace/backend/app/services/query_intent.py", line 92, in expand_query
    message = await client.messages.create(
...
anthropic.AuthenticationError: Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011Cg2L1Qg6uuJPdYfTxGCwn'}
```

So: the test service is almost certainly not serving a healthy miss path with `rerank_in`/`rerank_out` log fields. The local backend is this branch, and it also cannot complete a miss. Time to first token was not probed; a streaming `messages.stream` would hit the same 401.

Datadog: `DD_API_KEY` validates. `POST /api/v2/spans/events/search` and `POST /api/v2/logs/events/search` return 401 Unauthorized (no `DD_APP_KEY` / application key in the environment). Historical 246-miss LLM Observability tokens were not exported.

The ~2.7 s / 3.3 s p95 figures in STRESS_TEST.md remain the last live numbers (246 misses, server-side, after `525a355`). This run did not reproduce them.

**Benchmark checklist.** Sample size 0 successful rerank timings. Errors: 15/15 test-host POSTs, 1/1 local POST, all 500. Work that happened: HTTP reached `/recommend`; expand or rerank called Anthropic; Anthropic rejected the key; no stage header, no token fields. Cannot name generation vs overhead.

## 3. Clean load test

Claim we wanted: Locust `-u 4 -r 1 -t 2m` with the same warm-up as the baseline, sentinel-exclude misses (no extra word), then hit p95 and miss p95 from the client, inside the spend ceiling in [backend/loadtest/README.md](../backend/loadtest/README.md).

The ceiling is 200 warmup keys plus a 2-minute mix at 4 users. Warmup is 200 real Claude/OpenAI calls. POST `/recommend` on this host is 500, so that warmup would spend the ceiling on failures. It was skipped (`MOODY_WARMUP=0`).

Abortive run, still against `MOODY_HOST` (test host), `MOODY_ALLOW_PROD=1`:

```
$ cd backend
$ MOODY_WARMUP=0 MOODY_ALLOW_PROD=1 \
    locust -f loadtest/locustfile.py \
    --host "$MOODY_HOST" \
    --headless -u 1 -r 1 -t 30s \
    --csv ../docs/loadtest/moody-testing-2026-10-14 \
    --html ../docs/loadtest/moody-testing-2026-10-14.html
```

Locust 2.46.7, exit code 1. Full CSV and HTML: [docs/loadtest/](loadtest/).

| Path | Requests | Failures | Median | p95 (Locust approx) | Notes |
| --- | --- | --- | --- | --- | --- |
| `/recommend hit` | 6 | 6 (100%) | 1100 ms | 1600 ms | Intent-hit, but 500 so not a cache hit |
| `/recommend miss` | 2 | 2 (100%) | 2800 ms | 2800 ms | N=2; p95 is not meaningful |
| `/popular` | 6 | 0 | 47 ms | 170 ms | 200 |
| `/health` | 2 | 0 | 49 ms | 49 ms | 200 |
| Aggregated | 16 | 8 (50%) | 550 ms | 2800 ms | Failures are all `/recommend` 500s |

```
Error report
2  POST /recommend miss: status 500: Internal Server Error
6  POST /recommend hit: status 500: Internal Server Error
```

This branch still ships `@limiter.limit` default `10/minute`. The baseline Locust shape needs 100/minute on the test process. `MOODY_RECOMMEND_RATE_LIMIT` (default `10/minute`) exists so a local measurement process can raise it without changing production. It was not needed here: 500s arrived well under 10/minute.

Word-count bias of the old Locust `" v{n}"` suffix is unchanged from the previous revision of this PR. Rerun: `pytest tests/test_locust_expand_bias.py` (part of 123 passed).

**Benchmark checklist.** Locust success sample size 0 for hit and miss. Errors 8/8 recommend, 0/8 health+popular. Work that happened: Locust POSTed `/recommend`; the service returned 500. Limiter of recommend failures is Anthropic 401 (shown locally), not Railway CPU. This is not the STRESS_TEST.md mix and must not be compared to the 84-hit / 39-miss baseline.

## Code in this PR (measurement only)

- `app/services/rerank.py`, `app/services/timing.py`, `app/routers/recommend.py`: token fields on the miss log line
- `app/services/eval.py`, `app/scripts/run_eval.py`: `MOODY_EVAL_PRE_22=1` replays pre-#22 knobs inside the eval process
- `app/routers/recommend.py`: `MOODY_RECOMMEND_RATE_LIMIT` defaults to `10/minute`
- Locust sentinel exclude bust (no extra word)
- This file and `docs/loadtest/*`

No change to candidate count, overview truncation, expansion gating, reason length, or the 10/minute production default.

## How to finish the three questions

1. Put a Messages-API-valid `ANTHROPIC_API_KEY` in the Cloud Agent environment and on the Railway test service. The key currently injected is set and looks like `sk-ant`, but Anthropic returns 401.
2. Confirm `MOODY_HOST` is a test service on this branch (so miss logs include `rerank_in`/`rerank_out`) with `/recommend` 200 and a raised limiter for Locust (`100/minute` on that process only).
3. From `backend/`, run `python -m app.scripts.run_eval --json --verbose` at least 5 times, interleaved with `MOODY_EVAL_PRE_22=1 python -m app.scripts.run_eval --json --verbose`. Parse JSON from the first `{`. A drop is a query that fails on one side in every run and passes on the other in every run.
4. Drive misses, collect `Server-Timing` plus `rerank_in`/`rerank_out`. If `rerank_out` does not move, report ms per output token, not a scatter slope. Add a streaming TTFT probe only as a side measurement.
5. If Datadog still has the 246-miss LLM Observability spans, export them with an application key (`DD_APP_KEY`). The API key alone cannot search spans.
6. Locust: `MOODY_ALLOW_PROD=1 locust -f loadtest/locustfile.py --headless -u 4 -r 1 -t 2m` from `backend/` against the test host, warmup on. Save CSV/HTML under `docs/loadtest/`.

## Unit tests that did run

From `backend/`, `DD_TRACE_ENABLED=false`:

```
$ pytest -q --tb=line
123 passed in 4.70s
Required test coverage of 75% reached. Total coverage: 79.79%
```

Those tests mock Anthropic. They do not replace a live eval or a successful Locust report.
