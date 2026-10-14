# About the three open stress-test questions

Branch: `cursor/measure-stress-open-questions-9b14`. Date: 2026-10-14.

This is a measurement report, not a fix. It answers the three unchecked items in [STRESS_TEST.md](STRESS_TEST.md). Noah reviews this PR before any follow-up change lands. Do not merge it as a product change.

The environment that ran this work had no live `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_DB_URL`, or `TMDB_API_READ_TOKEN`. It also had no Railway test-service URL. Quality, miss-stage p95, rerank token correlation, and the clean Locust hit/miss report are therefore **INCONCLUSIVE**. The code in this PR only adds rerank token fields on the existing miss log line and stops Locust from adding a word on cache misses.

## Verdict

| Question | Verdict | What we have |
| --- | --- | --- |
| 1. Quality on main vs pre-#22 | INCONCLUSIVE | Eval never ran. `run_eval.py` died on missing `SUPABASE_DB_URL` before any query. |
| 2. Rerank ~2.7 s, generation vs overhead | INCONCLUSIVE | No live miss timings or token counts. Logging is in place for the next run that has credentials. Time to first token was not added, because streaming would change the call path. |
| 3. Locust hit p95 and miss p95, word-count-safe misses | INCONCLUSIVE for latency. The miss bust no longer adds a word. | Production host was refused. No allowed load-test target was configured. |

## Preflight

Checked in this Cloud Agent VM with `printenv` name listing, `backend/.env` (absent), GitHub Actions secrets (403), and the live frontend bundle.

| Name | This environment |
| --- | --- |
| `ANTHROPIC_API_KEY` | unset |
| `OPENAI_API_KEY` | unset |
| `SUPABASE_DB_URL` | unset |
| `TMDB_API_READ_TOKEN` | unset |
| `MOODY_HOST` | unset |
| `MOODY_ALLOW_PROD` | unset |

The docs never print a backend URL. The deployed frontend at `https://www.moodyalpha.app` ships `https://moody-production-87c7.up.railway.app` as `VITE_API_URL`. That host is production. [STRESS_TEST.md](STRESS_TEST.md) says the Locust target is a Railway test service, never production. [backend/loadtest/README.md](../backend/loadtest/README.md) blocks every non-localhost host unless `MOODY_ALLOW_PROD=1` is set.

Read-only probes against that production host, no `POST /recommend`:

```
$ curl -sS -D - https://moody-production-87c7.up.railway.app/health
HTTP/2 200
server: railway-hikari
{"status":"ok"}

$ curl -sS -o /tmp/popular.json -w "%{http_code} %{size_download}\n" \
    https://moody-production-87c7.up.railway.app/popular
200 2756
```

Locust against the same host exited before any traffic:

```
$ SUPABASE_DB_URL='postgresql://x:x@127.0.0.1/x' \
    locust -f loadtest/locustfile.py \
    --host https://moody-production-87c7.up.railway.app \
    --headless -u 1 -r 1 -t 1s
[2026-10-14 13:32:18,429] cursor/INFO/locust.main: Starting Locust 2.46.7
Refusing to load test https://moody-production-87c7.up.railway.app: not in safe allowlist (localhost/127.0.0.1). Set MOODY_ALLOW_PROD=1 to override and test the deployed service.
```

Machine at measurement time: 4 cores, `load average: 0.18, 0.08, 0.02`, idle. That does not matter for the three open questions, because the live pipeline never ran.

## 1. Quality

Claim we wanted: pass rate and per-query pass/fail for the 9-query harness on main (25 candidates, gated expansion, 300-character overviews) versus the pre-#22 settings at `eb32d87` (40 candidates, every query expanded, full overviews), same eval set, with every dropped query named.

What ran:

```
$ python3 -m app.scripts.run_eval.py --verbose
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
supabase_db_url
  Field required [type=missing, input_value={}, input_type=dict]
```

No query scores exist. Do not treat the missing run as "quality held".

The eval set on both `main` (`0d915ef`) and `eb32d87` is the same 9 queries in `EvaluationHarness.get_test_queries`. `eval.py` at `eb32d87` still called `search_similar(..., limit=25)` even though `/recommend` used `CANDIDATE_LIMIT = 40`. A fair pre-#22 run has to pass `limit=40` into that call. The other pre-#22 knobs are in `query_intent.py` (always call Haiku) and `rerank.py` (full overviews, `max_tokens=1024`, no 15-word reason cap).

**Benchmark checklist.** Sample size 0. Cold versus warm does not apply. The limiter of this result is missing `SUPABASE_DB_URL`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY`. `TMDB_API_READ_TOKEN` is not required for `run_eval.py`, which skips watch providers.

## 2. Miss latency and rerank tokens

Claim we wanted: p50/p95/max per stage from `Server-Timing` and `StageTimer`, plus rerank input/output tokens, optional time to first token, and latency versus output length, so we can say whether the ~2.7 s rerank p50 is output generation or fixed overhead.

Nothing in that set was measured. Production was not POSTed. Local `/recommend` cannot start without `SUPABASE_DB_URL`.

What this PR changes, measurement only:

- After the Anthropic rerank response, `_record_token_usage` writes `rerank tokens input=N output=M` at INFO and attaches `rerank_in` / `rerank_out` to the existing `recommend miss timings ...` line.
- Those fields are not added to `Server-Timing`. The header stays duration-only.
- The rerank call is still a single non-streaming `messages.create`. Time to first token needs `messages.stream`, which would change the path under test, so it was left out.

Unit tests cover the log line and the timer fields with a mocked Anthropic payload (`input_tokens=100`, `output_tokens=40`). That is not a live limiter.

**Benchmark checklist.** Sample size 0 for live rerank. The ~2.7 s / 3.3 s p95 figures in STRESS_TEST.md remain the last live numbers (246 misses, server-side, after `525a355`). This run did not reproduce them. Haiku output speed as a back-of-envelope bound is a guess until tokens and wall time sit on the same line from a real miss.

## 3. Clean load test

Claim we wanted: Locust `-u 4 -r 1 -t 2m` with the same warm-up as the baseline, miss queries that do not add a word, then hit p95 and miss p95 from the client.

Locust did not run against an allowed target. There is no hit p95 or miss p95 from this session.

The miss bust did change. Misses used to append `" v{n}"`. That extra word made some 2-word moods look like 3-word moods, so `should_expand` skipped Haiku. Misses now send `exclude_tmdb_ids` containing `2000000000 + n` (`n` in `0 .. MOODY_MISS_POOL-1`). The query string is the typed mood. The sentinel id is not a real TMDB title, so the exclude filter is a no-op on the candidate list. The cache key still changes because it includes sorted exclude ids.

Word-count bias of the old suffix, measured on the committed 100-query file with production `should_expand` (deterministic, one pass, no network):

```
mood_queries=100
would_expand_as_typed=5
skip_expand_as_typed=95
old_suffix_flips_expand_off=3
still_expand_with_v0=2
flipped queries:
  'feel-good'
  'heist comedy'
  'office satire'
```

The five moods that expand as typed are `uplifting`, `thriller` (still expand after `" v0"`, because they stay under 3 words), plus the three flipped above. 95 of 100 moods already skip expansion without any suffix. The old Locust miss path therefore under-counted expansion relative to real 1-word and 2-word traffic, but the effect is 3 queries in this pool, not most of the pool.

**Benchmark checklist.** Locust latency sample size 0. The word-count table is N=100 strings from `backend/loadtest/mood_queries.json`, cold versus warm N/A, limiter is `should_expand` itself. It reproduces on every run. Errors 0. It does not stand in for hit/miss p95.

A Locust run that matches STRESS_TEST.md still needs:

- A Railway **test** service URL in `MOODY_HOST`, not `https://moody-production-87c7.up.railway.app`
- That service on a branch with `@limiter.limit("100/minute")` (production is `10/minute`)
- `MOODY_ALLOW_PROD=1` only for that test host
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_DB_URL`, `TMDB_API_READ_TOKEN` on the service
- Client-side `locust -f loadtest/locustfile.py --headless -u 4 -r 1 -t 2m` from `backend/`

Localhost is an allowed Locust host, but this VM has no credentials to serve `/recommend`, so localhost was not used as a substitute.

## Code in this PR

- `app/services/rerank.py`, `app/services/timing.py`, `app/routers/recommend.py`: token fields on the miss log line
- `backend/README.md`: documents those fields on the miss log line
- `backend/loadtest/locustfile.py` and `backend/loadtest/README.md`: sentinel exclude bust
- Tests for the log line and timer extras
- This file

No change to candidate count, overview truncation, expansion gating, reason length, or the 10/minute production limit.

## How to finish the three questions

1. Put `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `SUPABASE_DB_URL` in `backend/.env`.
2. From `backend/`: `python -m app.scripts.run_eval.py --verbose --json` on this branch. Save the JSON.
3. In a worktree, restore pre-#22 `query_intent.py` and `rerank.py` from `eb32d87`, set `search_similar(..., limit=40)` in `eval.py`, and run the same command. Diff `results[].query` where `passed` flipped.
4. Deploy this branch to a Railway test service with a raised recommend limit. Set `MOODY_HOST` to that URL. Run Locust as above. Collect the Locust HTML/CSV and the `recommend miss timings` / `rerank tokens` lines.
5. For each miss line, plot `rerank` ms against `rerank_out`. If wall time tracks output tokens, generation dominates. If wall time stays near 2.7 s while `rerank_out` stays small, fixed overhead dominates. Time to first token still needs a separate streaming probe.

## Unit tests that did run

```
$ pytest -q --tb=line
112 passed in 4.13s
Required test coverage of 75% reached. Total coverage: 78.31%
```

Those tests mock Anthropic. They do not replace a live eval or Locust report.
