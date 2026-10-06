# Stress test: `/recommend` latency and Railway load

Branch: `Stress-test` · Date: 2026-10-05

How to run the test is in [`backend/loadtest/README.md`](../backend/loadtest/README.md). This document records why it was run, what it found, and what changed as a result.

## Purpose

1. Check the latency SLOs under a realistic traffic mix:
   - `/recommend` cache hit p95 **< 300 ms**
   - `/recommend` cache miss p95 **< 3 s**
   - error rate **< 1%** (a 429 counts as an error)
2. Check whether the Railway service has enough CPU and memory to handle that load.
3. Measure what a cache miss costs in latency and in LLM calls.

## Test setup

| | |
|---|---|
| Tool | Locust, headless, `-u 4 -r 1 -t 2m` |
| Warm-up | 200 cache keys (100 moods × with/without exclude preset), then 60 s settle |
| Traffic mix | `/recommend` 7 : `/popular` 2 : `/health` 1 |
| `/recommend` split | 70% cache hits, 30% misses (`" v{n}"` suffix, pool of 20); 15% send `exclude_tmdb_ids` |
| Rate limit | Raised to `100/minute` on test branch (production uses `10/minute`) |
| Target | Railway test service (`MOODY_HOST`), never production |

On a cache miss, `/recommend` runs five network calls in sequence:

```
expand (Claude Haiku) → embed (OpenAI) → pgvector search (Supabase) → rerank (Claude Haiku) → TMDB watch providers
```

## Baseline (commit `e50ea64`)

Locust results:

| Path | Requests | Median | p95 | SLO |
|---|---|---|---|---|
| `/recommend` hit | 84 | 89 ms | ~170 ms | < 300 ms ✅ |
| `/recommend` miss | 39 | **5.6 s** | **~6.4 s** | < 3 s ❌ |
| `/popular` | 37 | 94 ms | ~230 ms | — |
| `/health` | 16 | 92 ms | ~170 ms | — |

- Errors: 0%, with no 429s (about 61 recommend calls/min, under the 100/min test-branch limit).
- Hits were network time plus an in-memory cache lookup. The slowest hit was 333 ms.
- Every miss took between 4.6 s and 7.7 s. A miss costs about 50× a hit.
- Railway CPU peaked under 0.15 vCPU, memory stayed flat at about 200 MB, and the error rate was 0%.

**Conclusion:** the slow misses come from waiting on Claude, OpenAI, Supabase and TMDB, not from Railway CPU or memory. More replicas or users won't fix the miss SLO and only add LLM spend. The fix has to make the miss path itself shorter or cheaper.

## Changes

### `525a355` — perf: cut cache-miss latency and add per-stage timing

| Change | Where | Why |
|---|---|---|
| Per-stage timer: one INFO log line per miss and a `Server-Timing` header | `app/services/timing.py`, `app/routers/recommend.py` | Shows where the time goes before tuning anything |
| Logging config: `app.*` at INFO, root at WARNING | `app/main.py` | Without it, the timing lines never reached Railway logs |
| Rerank candidates 40 → 25 | `app/routers/recommend.py` | Fewer input tokens |
| Overviews cut to 300 characters at a word boundary | `app/services/rerank.py` | Fewer input tokens |
| Reasons limited to one sentence of ≤ 15 words; `max_tokens` 1024 → 512 | `app/services/rerank.py` | Output tokens dominate rerank time |
| Skip query expansion for queries of ≥ 3 words (`should_expand`) | `app/services/query_intent.py` | Saves a whole Haiku call on descriptive queries; short ones like "Fall" are still expanded |
| One pooled `httpx.AsyncClient` for TMDB | `app/services/tmdb.py`, `app/main.py` | Avoids a new TLS handshake per watch-provider lookup |

### `08ae2f4` — fix: read TMDB token from `TMDB_API_READ_TOKEN`

The first rerun after `525a355` returned **1,435 / 1,435 TMDB `401 Unauthorized`** errors. The app read `API_READ_ACCESS_TOKEN`, but Railway and the GitHub ingest secret both define `TMDB_API_READ_TOKEN`. Every provider request therefore went out as `Bearer None`. `fetch_providers` returns `[]` on any failure, so `/recommend` still returned 200 and nothing in the response showed the problem. The new stage logging is what surfaced it.

## Results after changes (246 misses)

All 414 requests returned 200, and there were no TMDB failures. The logs show two Datadog LLM Observability upload tracebacks (`HttpIoError`), which ran outside the request path and did not affect any response.

Server-side per-stage timing for cache misses:

| Stage | p50 | p95 | max |
|---|---|---|---|
| expand | 0 ms | 0 ms | 1,236 ms |
| embed | 187 ms | 515 ms | 1,196 ms |
| search | 235 ms | 996 ms | 1,985 ms |
| **rerank** | **2,747 ms** | **3,313 ms** | 4,734 ms |
| providers | 75 ms | 91 ms | 200 ms |
| **total** | **3,362 ms** | **4,752 ms** | 5,502 ms |

Before vs after:

| Metric | Before | After | Change |
|---|---|---|---|
| Miss p50 | 5.6 s | 3.36 s | −40% |
| Miss p95 | ~6.4 s | 4.75 s | −26% |
| Misses under 3 s | 0% | 13% (31/246) | |
| Miss SLO (p95 < 3 s) | ❌ | ❌ | |

## Findings

1. **Rerank is now the bottleneck.** It takes about 80% of a miss, and its p95 alone (3.3 s) is over the 3 s SLO. Speeding up any other stage cannot meet the SLO.
2. **Search has a long tail.** p50 is 235 ms but p95 is about 1 s, and in an earlier run the first misses after deploy took 1.3–1.6 s in search. The likely cause is a cold HNSW index or cold database connections on Supabase.
3. **Providers are cheap now.** Six lookups take about 75 ms with the pooled client and successful results are cached.
4. **Failures were invisible.** The TMDB outage went unnoticed until per-stage logging made it visible.
5. **The server still has lots of headroom.** CPU and memory were never the constraint.

### Caveats

- **Expansion skips are higher in this test than they will be in real traffic.** Locust appends `" v{n}"` to miss queries, which adds one word. A 2-word query like "date night" becomes 3 words and skips expansion. Expansion ran on only 12 of 246 misses, and real traffic will expand more often.
- **The before and after numbers are measured differently.** The baseline comes from Locust and includes the network round trip from the client. The "after" numbers come from the server's own timing and leave out about 90 ms of network time.
- **Cache-hit latency was not re-measured.** Hits aren't logged per stage, and no new Locust report was captured. The changes don't touch the hit path.
- **Recommendation quality has not been checked yet** after the smaller rerank and the expansion skipping. See next steps.

## Next steps

- [ ] Run `backend/app/scripts/run_eval.py` against `main` and this branch to confirm quality held with 25 candidates, trimmed overviews, and fewer expansions.
- [ ] Log rerank input and output tokens next to the timing line. That shows whether generating output or the fixed per-request overhead dominates the ~2.7 s.
- [ ] Shrink the rerank output based on that measurement: ranked IDs only, shorter tag-style reasons, or reasons loaded after the results.
- [ ] Keep pgvector warm: run a query at startup and send one periodically, to cut the search p95 tail.
- [ ] Change the Locust miss suffix so it doesn't change the word count (for example, use a cache-busting field instead of a word).
- [ ] Update the 4 rate-limit tests in `backend/tests/test_rate_limit_and_cache.py`, which still expect a 10/minute limit.
- [ ] Capture a full Locust report on the next run so hit and miss numbers are measured the same way as the baseline.
