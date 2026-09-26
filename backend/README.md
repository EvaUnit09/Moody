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
2. **Query expansion.** `expand_query` always calls Claude Haiku (`claude-haiku-4-5`). The model is instructed to leave an already-clear mood or plot request unchanged, and to rewrite short or ambiguous text (a season, a single word) into a 1–2 sentence description so the embedding does not latch onto a title. The expanded string is what gets embedded. The **original** query is what the reranker sees.
3. **Embed + search.** `text-embedding-3-small`, then cosine search on `movies.embedding_half` (`halfvec(1536)`). Limit is 40 (`CANDIDATE_LIMIT`). Rows with `vote_average` below 5.0 are dropped in SQL.
4. **Excludes.** Matching `tmdb_id`s are removed from those 40 candidates before rerank. The search does not fetch replacements, so a long exclude list can leave the reranker a short pool.
5. **Rerank.** Haiku picks up to 6 of the remaining candidates and writes a one-line reason grounded in the overview. Picks whose id is not in the candidate set are discarded.
6. **Watch providers.** TMDB `/movie/{id}/watch/providers` for the region, concurrency capped at 10. Preference order is flatrate, then buy, then rent. Links must be `https://www.themoviedb.org/...` or `https://www.justwatch.com/...`. A failed fetch returns `[]` for that title and is not cached.

The web client omits `region`, so production traffic uses `US`.

### `GET /popular`

Returns 16 movies (`POPULAR_LIMIT`) with `vote_count >= 100` and `vote_average >= 5.0`, ordered by the `popularity` column. No request body. Served from the in-memory `__popular__` entry (1 hour TTL). Startup warms that entry, and a background task refreshes it every 3300 seconds. See [docs/INGEST_POPULAR.md](../docs/INGEST_POPULAR.md) for how the column stays current.

### `GET /health`

`{"status": "ok"}`. Not rate limited.

## Caching and rate limits

`POST /recommend` is limited to **10 requests per minute per client IP** (`slowapi`, in-memory). Behind Railway, the key is the first hop of `X-Forwarded-For`, otherwise the direct socket address. Each replica keeps its own counters, so N replicas allow about N×10/min. A `429` body is `{ "error": "Rate limit exceeded", "message": "..." }` with `Retry-After: 60`. The frontend reads `detail` on errors, so the UI shows the status code for this response.

The recommend cache and the popular cache are process-local. A GitHub Actions ingest does not clear them. Anthropic or OpenAI failures during expansion, embed, or rerank are not caught in the router; they surface as a 500 and are not cached.

## Layout

- `app/main.py` — FastAPI app, CORS, rate-limit handler, popular-cache warm loop
- `app/routers/` — `recommend.py` (`POST /recommend`), `popular.py` (`GET /popular`)
- `app/services/` — `embeddings.py`, `query_intent.py` (query expansion), `rerank.py`, `tmdb.py` (genre names + watch providers)
- `app/cache.py` — in-memory TTL cache and cache-key normalization
- `app/db.py` — Supabase/pgvector access (asyncpg), including popularity-only updates
- `app/scripts/` — `fetch_movies.py`, `build_embeddings.py`, `ingest_popular.py`, `create_index.py`, `run_eval.py`
- `sql/schema.sql` — `movies` table + HNSW index on `embedding_half`, run manually in the Supabase SQL editor

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
