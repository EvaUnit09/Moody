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

## Layout

- `app/main.py` — FastAPI app, CORS, rate-limit error handler
- `app/routers/` — `recommend.py` (`POST /recommend`), `popular.py` (`GET /popular`)
- `app/services/` — `embeddings.py`, `query_intent.py` (query expansion), `rerank.py`, `tmdb.py`
- `app/db.py` — Supabase/pgvector access (asyncpg)
- `app/scripts/` — one-off data ingestion (`fetch_movies.py`, `build_embeddings.py`) and eval (`run_eval.py`)
- `sql/schema.sql` — `movies` table + HNSW index, run manually in the Supabase SQL editor

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
