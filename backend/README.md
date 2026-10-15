# Moody — backend

FastAPI backend for [Moody](../README.md): embeds movies + queries, runs
vector search over Supabase/pgvector, and reranks results with Claude Haiku.

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_DB_URL
uvicorn app.main:app --reload   # http://localhost:8000
pytest                           # run tests
ruff check app                   # lint
```

## HTTP API

### `POST /recommend`

Body (`RecommendRequest`):

| Field | Constraint |
| --- | --- |
| `query` | Required string, 1–200 characters. Whitespace-only is rejected with `400` after trim. |
| `region` | Optional 2-letter ISO code. Empty or omitted becomes `US`. Anything else is `400`. |
| `exclude_tmdb_ids` | Optional list of TMDB ids, at most 100. More than that is `422`. |

```bash
curl -s -X POST http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"query":"slow and melancholic","exclude_tmdb_ids":[550,680]}'
```

Response is `{ "results": [ ... ] }`. Each result is a movie plus `reason` and `providers` (up to 3 watch links for the region). The reranker returns at most 6 titles (`TOP_N` in `rerank.py`).

Pipeline, in order:

1. **Cache lookup.** The key is `build_cache_key(f"{query}:{region}", exclude_ids)`. `normalize_query` lowercases, turns hyphens into spaces, and strips other punctuation, so the region code is concatenated onto the normalized query. Exclude ids are sorted and de-duplicated; an empty list is stored the same as omitting the field. A hit skips every step below. Default TTL is 1 hour. Queries that match a popular-mood keyword in `cache.py` are stored for 2 hours.
2. **Query expansion.** `should_expand` counts words in `normalize_query(query)` (lowercase, hyphens become spaces, other punctuation dropped). Fewer than 3 words (`MIN_DESCRIPTIVE_WORDS`) calls Claude Haiku (`claude-haiku-4-5`, `max_tokens` 256) to rewrite the text into 1–2 sentences so the embedding does not latch onto a title. Three or more words return the original string and do not call the model. `"Fall"` and `"date night"` expand. `"sci-fi"` becomes two words (`sci fi`) and expands. `"cozy rainy day"` is embedded as typed. The string returned by `expand_query` is what gets embedded. The **original** query is what the reranker sees.
3. **Embed + search.** `text-embedding-3-small`, then cosine search on `movies.embedding_half` (`halfvec(1536)`). Limit is 25 (`CANDIDATE_LIMIT` in `recommend.py`; `search_similar` defaults to the same 25). Rows with `vote_average` below 5.0 are dropped in SQL.
4. **Excludes.** Matching `tmdb_id`s are removed from those 25 candidates before rerank. The search does not fetch replacements, so a long exclude list can leave the reranker a short pool.
5. **Rerank.** Haiku (`max_tokens` 512) picks up to 6 of the remaining candidates. Each overview in the prompt is cut to 300 characters at a word boundary (`MAX_OVERVIEW_CHARS`); a cut is marked with `…`. The tool schema asks for one sentence of at most 15 words (`MAX_REASON_WORDS`), grounded in that truncated overview. The API does not reject a longer reason. Picks whose id is not in the candidate set are discarded.
6. **Watch providers.** TMDB `/movie/{id}/watch/providers` for the region, concurrency capped at 10, timeout 5s, through one process-wide `httpx.AsyncClient` that `main.py` closes on shutdown. Preference order is flatrate, then buy, then rent, at most 3. Every logo on a title shares that region's one link. The link must match `https://www.themoviedb.org/...` or `https://www.justwatch.com/...`; anything else drops the title's providers. A failed fetch returns `[]` and is not cached. Successful non-empty responses are cached in-process with no TTL, keyed `{tmdb_id}|{REGION}`. The bearer token is `TMDB_API_READ_TOKEN` (read at import). A missing or wrong token is a 401 from TMDB, which this step turns into `[]`. The recommend response is still 200.

The web client omits `region`, so production traffic uses `US`.

### Stage timing

Every successful `POST /recommend` sets `Server-Timing`. Durations are milliseconds with one decimal (`expand;dur=812.4`), and the value always ends with `total`.

| Outcome | Header stages | Log |
| --- | --- | --- |
| Cache hit | `cache`, `total` | none (the hit is DEBUG inside `cache.get`) |
| Cache miss | `cache`, `expand`, `embed`, `search`, `rerank`, `providers`, `total` | one INFO line: `recommend miss timings cache=…ms expand=…ms embed=…ms search=…ms rerank=…ms providers=…ms total=…ms` |

`app` loggers are INFO and the root logger is WARNING, so third-party INFO lines stay quiet and the miss line still shows up. A failure in expansion, embed, or rerank is a 500: no `Server-Timing` header, no timing line, and the result is not cached. The frontend does not read the header.

Empty `providers` on an otherwise successful response usually means TMDB rejected the call. Confirm `TMDB_API_READ_TOKEN` on the service. The name `API_READ_ACCESS_TOKEN` is not read. `fetch_providers` logs the failure with `print`, not the `app` logger.

### `GET /popular`

Returns 16 movies (`POPULAR_LIMIT`) with `vote_count >= 100` and `vote_average >= 5.0`, ordered by the `popularity` column. No request body. Served from the in-memory `__popular__` entry (1 hour TTL). Startup warms that entry, and a background task refreshes it every 3300 seconds. See [docs/INGEST_POPULAR.md](../docs/INGEST_POPULAR.md) for how the column stays current.

### `GET /health`

`{"status": "ok"}`. Not rate limited.

## Caching and rate limits

`POST /recommend` is limited to **10 requests per minute per client IP** (`slowapi`, in-memory). Behind Railway, the key is `X-Real-IP`, the edge's documented client-IP header, otherwise the direct socket address. `X-Forwarded-For` is ignored because callers can write to it. Each replica keeps its own counters, so N replicas allow about N×10/min. A `429` body is `{ "error": "Rate limit exceeded", "message": "..." }` with `Retry-After: 60`. The frontend reads `detail` on errors, so the UI shows the status code for this response.

The recommend cache and the popular cache are process-local. A GitHub Actions ingest does not clear them. Anthropic or OpenAI failures during expansion, embed, or rerank are not caught in the router; they surface as a 500 and are not cached.

## Layout

- `app/main.py` — FastAPI app, CORS, rate-limit handler, popular-cache warm loop
- `app/routers/` — `recommend.py` (`POST /recommend`), `popular.py` (`GET /popular`)
- `app/services/` — `embeddings.py`, `query_intent.py` (query expansion), `rerank.py`, `timing.py` (`Server-Timing`), `tmdb.py` (genre names + watch providers)
- `app/cache.py` — in-memory TTL cache and cache-key normalization
- `app/db.py` — Supabase/pgvector access (asyncpg), including popularity-only updates
- `app/scripts/` — `fetch_movies.py`, `fetch_keywords.py`, `build_embeddings.py`, `ingest_popular.py`, `create_index.py`, `run_eval.py`
- `sql/schema.sql` — `movies` table + HNSW index on `embedding_half`, run manually in the Supabase SQL editor

Catalog order, quotas, and the `psycopg2` gap in `create_index.py` are in [docs/catalog.md](../docs/catalog.md). CI uses Python 3.12 (`requires-python >= 3.11`), `ruff check app`, and `pytest`.

## Connection budget

This service is sized for **1 uvicorn worker** (the Procfile has no `--workers` / `WEB_CONCURRENCY`). Do not raise worker count without lowering `DB_POOL_MAX_SIZE`.

`SUPABASE_DB_URL` is the Supabase **session** pooler (`*.pooler.supabase.com`, port **5432**). Session mode pins one Postgres backend to each client. The pooler `pool_size` is **15**, shared by TEST and production. Client 16 raises `asyncpg.exceptions.InternalServerError: (EMAXCONNSESSION) max clients reached in session mode`. Stay on the session pooler for now.

`get_pool()` in `app/db.py` creates one process-wide asyncpg pool, rebound when the event loop changes. Lifespan opens it on startup and `close_pool()` closes it on shutdown. Scripts that open the pool (`ingest_popular.py`, `build_embeddings.py`, `run_eval.py`, `test_retrieval.py`) close it before exit.

| Knob | Default | Env |
| --- | --- | --- |
| Idle connections per process (production) | 1 | `DB_POOL_MIN_SIZE` |
| Idle connections on TEST | 0 (set on the TEST service) | `DB_POOL_MIN_SIZE=0` |
| Connections per process under load | 2 | `DB_POOL_MAX_SIZE` |
| Query `command_timeout` (seconds) | 30 | `DB_COMMAND_TIMEOUT` |
| Pool acquire timeout (seconds) | 5 | `DB_POOL_ACQUIRE_TIMEOUT` |
| `pg_stat_activity.application_name` | `moody` | `DB_APPLICATION_NAME` |
| Direct Postgres URL for `create_index.py` | unset (falls back to `SUPABASE_DB_URL`) | `SUPABASE_DB_DIRECT_URL` |

Code default for `DB_POOL_MIN_SIZE` is **1** (production). The TEST Railway service must set `DB_POOL_MIN_SIZE=0` so an idle TEST replica holds no session slots. `DB_POOL_MAX_SIZE` stays **2**.

An acquire timeout on `/recommend` is HTTP 503 (`Database busy, try again shortly`).

Slots in use at peak with the planned 1 worker:

```
production: 1 replica × 1 worker × 2 = 2  (idle 1)
TEST:       1 replica × 1 worker × 2 = 2  (idle 0 when DB_POOL_MIN_SIZE=0)
+ ingest/eval scripts (each another process, same max)
+ 1 to 2 for the Supabase dashboard
```

Keep that sum **under 15**. TEST and production share the session pooler, so count both.

Transaction mode (port **6543**) is viable: set `statement_cache_size=0` on `create_pool` and keep `register_vector` as the pool `init`. That multiplexes clients onto fewer backends. `LISTEN` still does not work in transaction mode. It is not chosen. The URL stays on 5432.

`create_index.py` uses `psycopg2` and sits outside the asyncpg budget. Point it at the direct Postgres URL with `SUPABASE_DB_DIRECT_URL` (not the pooler) so a long `CREATE INDEX` does not hold a session-pooler slot. If that env is unset, the script falls back to `SUPABASE_DB_URL`.

If you add replicas or workers, lower `DB_POOL_MAX_SIZE` until the formula fits. Set `DB_APPLICATION_NAME` to `moody-test` or `moody-production` so `pg_stat_activity` shows which service holds a slot.

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
