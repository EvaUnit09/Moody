# About the three open stress-test questions

Branch: `cursor/measure-stress-open-questions-9b14`. Date: 2026-10-14.

This is a measurement report, not a fix. It answers the three unchecked items in [STRESS_TEST.md](STRESS_TEST.md). Noah reviews this PR before any follow-up change lands. Do not merge it as a product change.

A later follow-up in this Cloud Agent VM received a Messages-API-valid `ANTHROPIC_API_KEY` (Anthropic `GET /v1/models` 200, tiny Haiku `messages.create` 200). OpenAI, Supabase, and TMDB still worked. `MOODY_HOST` is a Railway test hostname, not production; that service was 502 / timed out, so miss timings and Locust ran against a local uvicorn on this branch (`127.0.0.1:8001`) with live keys and `MOODY_RECOMMEND_RATE_LIMIT=100/minute` in that process only. Production default remains `10/minute`.

## Verdict

| Question | Verdict | Sample size | What we have |
| --- | --- | --- | --- |
| 1. Quality on main vs pre-#22 | **No drop.** Median pass rate 100% on both sides. | 5 interleaved runs per side, 9 queries each (90 scored queries). Errors 0. | Every query passed every run on both sides. **Dropped queries: none.** |
| 2. Rerank ~2.7 s, generation vs overhead | **Mostly output generation**, not fixed overhead. | 30 cache-miss POSTs with `Server-Timing` + `rerank_in`/`rerank_out`. 5 streaming TTFT probes (not the product `messages.create` path). | Rerank p50 **3076 ms**, p95 **3328 ms**. `rerank_out` 252–306 (median 270). TTFT p50 **608 ms** (~18–22% of stream total); remaining tokens ~2.5 s. |
| 3. Locust hit p95 and miss p95 | Hit SLO holds on localhost. Miss SLO still fails. | One Locust run: warmup 200/200 (0 failed), then `-u 4 -r 1 -t 2m`. CSV: hit **122**, miss **43**, popular 45, health 24. Failures **0**. | Hit p95 **3 ms** (loopback cache). Miss p95 **4000 ms**. Not Railway client RTT. |

## Preflight

`MOODY_ALLOW_PROD=1` was set only after confirming `MOODY_HOST` is not `https://moody-production-87c7.up.railway.app`. Production was not POSTed.

| Name | This environment |
| --- | --- |
| `ANTHROPIC_API_KEY` | set. After the follow-up inject: models 200, tiny Haiku 200 (`usage.output_tokens=8`) |
| `OPENAI_API_KEY` | set. Live embeddings succeed |
| `SUPABASE_DB_URL` | set. Live pgvector search succeeds |
| `TMDB_API_READ_TOKEN` | set. Watch providers succeed on local misses |
| `DD_API_KEY` | set. Validate 200. Span/log search 401 without an application key |
| `MOODY_HOST` | set. Railway test host, not production. GET `/health` timed out; POST `/recommend` 502 |
| `MOODY_ALLOW_PROD` | `1` for the test-host probes only |

```
$ python3 -c "import os; h=os.environ['MOODY_HOST'].rstrip('/'); print('is_prod', h=='https://moody-production-87c7.up.railway.app')"
is_prod False

# Anthropic after the follow-up key inject
models_status 200
models_count 14 has_haiku True
messages_status 200
messages_ok_usage output_tokens=8
messages_stop max_tokens

# Railway test host, same session
GET /health TimeoutError
POST /recommend 502 Application failed to respond (~15 s)
```

Machine: 4 cores, `load average: 0.11, 0.05, 0.01` at the start of the live runs, idle. The miss limiter is Anthropic output generation, not this VM's CPU.

Local measurement server: `MOODY_RECOMMEND_RATE_LIMIT=100/minute DD_TRACE_ENABLED=false uvicorn app.main:app --host 127.0.0.1 --port 8001`. Smoke miss:

```
local8001_status 200
ms 7643.0
server_timing cache;dur=0.0, expand;dur=1060.9, embed;dur=1101.5, search;dur=2030.3, rerank;dur=3266.7, providers;dur=163.3, total;dur=7623.3
n_results 6
titles ['Dark Harvest', 'Little Forest: Summer/Autumn', 'Harvest Moon']
log: recommend miss timings ... rerank=3267ms ... rerank_in=2530 rerank_out=267 total=7623ms
```

That first miss is cold search (2030 ms) and is **not** in the n=30 stage table below.

## 1. Quality

Claim: pass rate and per-query pass/fail on main (25 candidates, gated expansion, 300-character overviews, `max_tokens` 512, 15-word reason cap) versus pre-#22 from `eb32d87` (limit=40, always expand, full overviews, `max_tokens` 1024, no reason cap), same 9 queries, every dropped query named.

Pre-#22 was `MOODY_EVAL_PRE_22=1` in the eval process only. `/recommend` does not read it.

```
$ python -m app.scripts.run_eval --json --verbose
$ MOODY_EVAL_PRE_22=1 python -m app.scripts.run_eval --json --verbose
```

Alternated 5 times (main, pre-22, …). `DD_TRACE_ENABLED=false`. JSON parsed from the first `{`.

| Side | Pass rates (5 runs) | Median | Range | Candidate limit | Errors |
| --- | --- | --- | --- | --- | --- |
| main | 1.0, 1.0, 1.0, 1.0, 1.0 | 100% | 100–100% | 25 | 0 |
| pre-#22 | 1.0, 1.0, 1.0, 1.0, 1.0 | 100% | 100–100% | 40 | 0 |

All nine queries passed on every run of both sides, including `Fall`.

**Queries that dropped: none.**

Main reasons are shorter (run 1 mean 84 chars) than pre-#22 (mean 141 chars), as expected from the 15-word cap. The harness `min_reason_length` is 20 characters; both sides cleared it. Pre-#22 avg rating on run 1 was 7.18 vs main 6.89; that is not a pass/fail drop.

**Benchmark checklist.** Limiter of a pass is the harness (result count, genre match, rating ≥ 6, reason length). Errors 0. Work happened: 6 titles per query, `Fall` recommended autumn-themed titles on both sides. Five interleaved runs, gap 0. End-to-end path is this eval harness, not `/recommend` HTTP (eval skips TMDB providers).

## 2. Miss latency and rerank tokens

Claim: p50/p95 per stage plus rerank tokens, so we can say whether the ~2.7 s rerank p50 is output generation or fixed overhead.

Railway test host could not serve `/recommend` (502). Local uvicorn on this branch emits `Server-Timing` and `rerank_in`/`rerank_out` on the miss log line.

Thirty unique misses: first 30 Locust moods, sentinel `exclude_tmdb_ids` `2001000000+i`. All 200, 6 results each.

| Stage | p50 | p95 | max | n |
| --- | --- | --- | --- | --- |
| expand | 0 ms | 1078 ms | 1121 ms | 30 |
| embed | 211 ms | 364 ms | 374 ms | 30 |
| search | 484 ms | 1228 ms | 1715 ms | 30 |
| **rerank** | **3076 ms** | **3328 ms** | 3416 ms | 30 |
| providers | 96 ms | 140 ms | 142 ms | 30 |
| **total** | **3998 ms** | **5160 ms** | 5423 ms | 30 |

Expand p50 is 0 because `should_expand` skips 3-or-more-word moods. Three one-word moods in this 30 (`uplifting`, `thriller`, `feel-good`) still call Haiku (~1.0–1.1 s).

Token fields on those 30 log lines:

| | min | median | max |
| --- | --- | --- | --- |
| `rerank_in` | 2275 | 2502 | 2817 |
| `rerank_out` | 252 | 270 | 306 |
| rerank ms / `rerank_out` | 9.85 | 11.39 | 12.20 |

`rerank_out` barely moves (range 54). Do not trust a scatter slope as the main evidence. Pearson corr(`rerank_out`, rerank ms) = 0.65; corr(`rerank_in`, rerank ms) = 0.12. Ten-token buckets still rise with output length (250s mean 2970 ms, 290s mean 3306 ms).

Streaming probe, same rerank tool/prompt, `messages.stream` (not the product `messages.create` path), n=5:

| query | TTFT ms | stream total ms | after TTFT ms | out tokens |
| --- | --- | --- | --- | --- |
| slow and melancholic | 610 | 3182 | 2572 | 287 |
| funny but not dumb | 490 | 2943 | 2453 | 269 |
| uplifting | 481 | 2934 | 2453 | 272 |
| small town mystery | 608 | 3236 | 2629 | 289 |
| movies that feel like autumn | 728 | 3305 | 2577 | 282 |

TTFT p50 **608 ms** (~17–22% of stream total). The remaining ~2.5 s is token generation. 270 output tokens × ~11 ms/token ≈ 3.0 s, which matches rerank p50.

**Answer:** the ~2.7–3.1 s rerank is **output generation**. Fixed overhead / time to first token is about half a second, not the bulk.

Datadog: API key validates; this VM still cannot search spans (no application key). Tokens came from the local miss log line.

**Benchmark checklist.** Limiter: Haiku writing ~270 output tokens. Tuned as production rerank knobs (`max_tokens` 512, 15-word reasons, 25 candidates). Arithmetic matches generation, not a cache no-op. Errors 0/30 HTTP, 0/5 stream. One session of 30 misses plus 5 TTFT streams; not 5 full locust-sized repeats. End-to-end miss total p50 4.0 s, of which rerank is ~77%. Work happened: 6 results, stage header, token fields on every miss.

## 3. Clean load test

Claim: Locust `-u 4 -r 1 -t 2m`, sentinel-exclude misses, same warmup as the baseline, hit p95 and miss p95 from the client, inside the [backend/loadtest/README.md](../backend/loadtest/README.md) spend ceiling.

`MOODY_HOST` was 502, so Locust targeted `http://127.0.0.1:8001` (localhost allowlist; `MOODY_ALLOW_PROD` not required). Warmup 200 keys at ~80/min (under this process's 100/minute), 0 failed, then 60 s settle. `-t 2m` starts after warmup.

```
$ locust -f loadtest/locustfile.py --host http://127.0.0.1:8001 --headless -u 4 -r 1 -t 2m \
    --csv ../docs/loadtest/moody-local-2026-10-14 \
    --html ../docs/loadtest/moody-local-2026-10-14.html
Warm-up sent 200/200 keys (0 failed)
Warm-up done.
Shutting down (exit code 0)
```

Committed CSV:

| Path | Requests | Failures | Median | p95 | SLO |
| --- | --- | --- | --- | --- | --- |
| `/recommend hit` | 122 | 0 | 3 ms | **3 ms** | < 300 ms, pass (localhost) |
| `/recommend miss` | 43 | 0 | 3600 ms | **4000 ms** | < 3 s, fail |
| `/popular` | 45 | 0 | 2 ms | 3 ms | — |
| `/health` | 24 | 0 | 2 ms | 3 ms | — |
| Aggregated | 234 | 0 | 3 ms | 3700 ms | — |

The live Locust shutdown table was hit 124 / miss 43 / 0 failures; CSV is 122 hits (two hits at the last tick). Miss min 3 ms: the miss stat is by **intent**, so a repeated mood+sentinel can be a real cache hit. p95 4000 ms is still the slow tail.

Full HTML/CSV: [docs/loadtest/](loadtest/) (`moody-local-2026-10-14*` plus the earlier abortive test-host 30 s run).

Hit p95 is not comparable to the Railway baseline ~170 ms. This is in-process cache plus loopback. Miss p95 4.0 s is the same LLM-bound path as STRESS_TEST.md (4.75 s server-side p95 after `525a355`) plus a little client overhead, and still over the 3 s SLO.

**Benchmark checklist.** Locust errors 0. Warmup work happened (200/200). Hit path is cache (p95 3 ms). Miss path is LLM (p95 4 s). One run, same shape as the baseline. Load generator was not saturated (4 users, wait 0.8–2.0 s, local 100/min cap, no 429s). Spend: 200 warmup keys + 43 intent-misses, inside the README ceiling (warmup is the large term; miss pool 20).

## Earlier 401 attempt (same VM, before the key inject)

The first pass in this Cloud Agent had `ANTHROPIC_API_KEY` set (`sk-ant`) but Anthropic returned 401 `invalid x-api-key`. Eval, local `/recommend`, and a 30 s Locust against the test host all failed. That abortive Locust HTML remains under `docs/loadtest/moody-testing-2026-10-14*`. Do not use its 1600/2800 ms p95 values; those were 500s.

## Code in this PR (measurement only)

- Miss log line: `rerank_in` / `rerank_out`
- Locust sentinel exclude bust (no extra word)
- Eval-only `MOODY_EVAL_PRE_22=1`
- `MOODY_RECOMMEND_RATE_LIMIT` defaults to `10/minute`
- This file and `docs/loadtest/*`

No change to candidate count, overview truncation, expansion gating, reason length, or the 10/minute production default.

## Unit tests

```
$ pytest -q --tb=line
123 passed in 4.70s
Required test coverage of 75% reached. Total coverage: 79.79%
```

Those tests mock Anthropic. Live evidence is the eval JSON, the n=30 miss timings, and the Locust CSV/HTML.
