# MovieRec Backend Build-Out Plan

## Context

`docs/architecture.md` already defines the target design: TMDB movie data embedded
with OpenAI `text-embedding-3-small`, stored in Supabase (pgvector), searched and
reranked by Claude Haiku 4.5 behind a FastAPI `POST /recommend` endpoint.

Current repo state: `scripts/fetch_movies.py` and `scripts/fetch_keywords.py` already
work and produced `raw_movies.json` / `movies_with_keywords.json` with 200 movies
(not yet the full ~30k target). Nothing past that exists yet — no `backend/`
directory, no FastAPI app, no Supabase schema, no `openai`/`anthropic`/`fastapi`
packages installed, and the directory is not yet a git repo.

Decision: validate the full pipeline (embed → store → retrieve → rerank) end to end
on the existing 200-movie sample before investing in scaling the fetch script to
~30k movies. This plan covers everything from git init through a working local
`/recommend` endpoint.

**Out of scope for this plan** (explicit follow-ups, not covered by any step below):
scaling `fetch_movies.py`/`fetch_keywords.py` to ~30k movies, the React frontend,
deploying to Railway/Vercel, Datadog observability, and IP-based rate limiting.

Three steps below require creating an external account before the step can be
executed (OpenAI, Supabase, Anthropic) — these are called out as manual checkpoints
immediately before the step that needs them, since account signup/payment setup
isn't something an agent chain can do.

---

## Step 1 — Initialize git and add .gitignore

**Intent**: Initialize a git repository at the project root and add a `.gitignore`
that excludes `.env`, `venv/`, and generated data JSON files, so secrets and
regeneratable build output never get committed. Add a short root `README.md`
pointing at `docs/architecture.md`.

**Acceptance**: `git status` shows a clean initialized repo; `.env` does not appear
in `git status` output even after later steps create `backend/.env`.

---

## Step 2 — Restructure repo into backend/

**Intent**: Refactor the existing top-level `scripts/`, `.env`, and data JSON files
into a `backend/app/` package layout (`app/scripts/`, `app/services/`, `app/routers/`,
`backend/data/`), so the fetch scripts share a common TMDB client instead of
duplicating auth logic, and so the FastAPI app added in later steps has a
conventional package structure (`uvicorn app.main:app`).

**Acceptance**: `backend/app/scripts/fetch_movies.py` and `fetch_keywords.py` run
successfully from `backend/` using `python -m app.scripts.fetch_movies` and produce
identical output to before the move; `backend/data/movies_with_keywords.json` still
has 200 movies with keywords.

---

## Step 3 — Add requirements.txt and install dependencies

**Intent**: Create `backend/requirements.txt` (`fastapi`, `uvicorn`, `openai`,
`anthropic`, `asyncpg`, `pgvector`, `pydantic-settings`, `python-dotenv`, `httpx`)
and install into the existing venv. Direct `asyncpg` + `pgvector` Postgres access is
chosen over `supabase-py` so the vector search query can use a plain cosine-distance
SQL operator instead of wrapping it in a PostgREST RPC function.

**Acceptance**: `pip freeze` in the venv shows all listed packages installed with no
build errors; flag and resolve any wheel-build failures under Python 3.14 if they
occur.

---

> **Manual checkpoint — OpenAI account**: sign up at platform.openai.com, attach a
> payment method (required for the Embeddings API), create an API key, and add
> `OPENAI_API_KEY=sk-...` to `backend/.env`. Required before Step 4.

## Step 4 — Build the embedding pipeline

**Intent**: Implement `app/config.py` (pydantic-settings reading `.env`),
`app/services/tmdb.py` (shared TMDB client + hardcoded genre-ID-to-name map),
`app/services/embeddings.py` (async OpenAI wrapper with single and batched embed
functions), and `app/scripts/build_embeddings.py`, which reads
`backend/data/movies_with_keywords.json` directly, builds a title+overview+genres+
keywords text blob per movie, and batch-embeds all 200 movies via the OpenAI API.

**Acceptance**: running the script embeds all 200 movies with 1536-dimension
vectors and prints a summary (count embedded, count with empty keyword lists,
average blob length) with no unhandled exceptions.

---
> **Manual checkpoint — Supabase account**: sign up at supabase.com, create a
> project, enable the pgvector extension (Database → Extensions → "vector"), and
> capture `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_DB_URL` (session
> pooler connection string) into `backend/.env`. Required before Step 5.

## Step 5 — Create Supabase schema and load embeddings

**Intent**: Write `backend/sql/schema.sql` defining a `movies` table with a
`vector(1536)` column and an HNSW index (`vector_cosine_ops`) — chosen over IVFFlat
because HNSW needs no row-count-dependent tuning parameter and works fine at both
200 rows now and ~30k rows later. Run the schema manually in the Supabase SQL
Editor. Implement `app/db.py` (asyncpg connection pool + `search_similar` cosine
distance query, with the pgvector codec registered on the pool). Extend
`app/scripts/build_embeddings.py` to upsert each embedded movie into the `movies`
table (idempotent, keyed on `tmdb_id`).

**Acceptance**: `select count(*) from movies;` in the Supabase SQL Editor returns
200 after running `build_embeddings.py`; re-running the script does not create
duplicate rows.

## Step 6 — Retrieval quality test

**Intent**: Write a throwaway `app/scripts/test_retrieval.py` that embeds ~5
representative mood/scenario queries (e.g. "something slow and melancholic",
"a lighthearted comedy for Friday night", "a mind-bending sci-fi movie"), runs
`db.search_similar` for each, and prints ranked title/distance/overview for manual
review. Not part of the shipped app — a diagnostic gate before building the API on
top of the retrieval layer.

**Acceptance**: script runs against the live Supabase table with no exceptions;
returned cosine distances are in a sane range (roughly 0–2); manual read of results
shows at least directionally relevant matches per query, given the sample is only
200 currently-popular movies.

---

> **Manual checkpoint — Anthropic account**: sign up at console.anthropic.com,
> attach a payment method, create an API key under Settings → API Keys, and add
> `ANTHROPIC_API_KEY=sk-ant-...` to `backend/.env`. Use model `claude-haiku-4-5`.
> Required before Step 7.

## Step 7 — Build the FastAPI /recommend endpoint

**Intent**: Implement `app/models.py` (Pydantic request/response schemas),
`app/services/rerank.py` (Claude Haiku wrapper using structured JSON output to rerank
~25 vector-search candidates down to the top 5 with a one-line reason each,
defensively truncating and dropping any hallucinated `tmdb_id`), `app/cache.py`
(in-memory dict + TTL keyed on normalized query text), `app/routers/recommend.py`
(`POST /recommend`: cache check → embed query → vector search top ~25 → Haiku
rerank → cache store → return), and `app/main.py` (FastAPI app with lifespan-managed
asyncpg pool, the recommend router, and a `GET /health` endpoint).

**Acceptance**: server starts with `uvicorn app.main:app`; `/health` returns 200.

## Step 8 — End-to-end local verification

**Intent**: Run the server locally and verify the full request flow: `GET /health`
returns 200; `POST /recommend` with a real mood query returns a JSON `results` array
of up to 5 items with coherent, query-specific one-line reasons; an identical
repeat request hits the in-memory cache (observable via a server-side debug log
line); an empty-string query returns 400, not a 500; `/docs` (FastAPI's Swagger UI)
works for interactive spot-checks against the Step 6 query set.

**Acceptance**: all of the above checks pass with no unhandled exceptions in server
logs.
