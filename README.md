# Moody

[![CI](https://github.com/EvaUnit09/Moody/actions/workflows/ci.yml/badge.svg)](https://github.com/EvaUnit09/Moody/actions/workflows/ci.yml)

A RAG-based movie recommendation app: describe a mood or scenario in plain
language and get back curated picks with reasons, instead of filtering by
genre/year dropdowns.

**Live demo:** https://moody-alpha-three.vercel.app

## How it works

1. ~30k movies (title, overview, genres, keywords) are embedded and stored in
   Postgres via pgvector.
2. A user's natural-language query (e.g. "something slow and melancholic")
   is expanded by an LLM if it's short/ambiguous, then embedded with the same
   model.
3. Vector search pulls the top candidates by cosine similarity.
4. An LLM reranks the candidates down to a shortlist and writes a one-line
   reason for each pick, grounded in the movie's overview.

Raw vector similarity alone gives "in the neighborhood" results, not good
judgment — the rerank step is what turns it into a curated shortlist. See
[docs/architecture.md](docs/architecture.md) for the full stack-decision
rationale (why pgvector, why Claude Haiku, cost estimates, etc.) and
[docs/plan/backend-buildout.md](docs/plan/backend-buildout.md) for the
original implementation plan.

## Tech stack

- **Backend:** FastAPI (Python), asyncpg
- **Vector store:** Supabase (Postgres + pgvector, HNSW index over half-precision embeddings)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Query expansion + reranking:** Claude Haiku (Anthropic)
- **Frontend:** React + TypeScript + Vite
- **Observability:** Datadog APM + LLM Observability
- **Hosting:** Vercel (frontend), Railway (backend)

## Running locally

### Backend

```bash
cd backend
cp .env.example .env   # fill in OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_DB_URL
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires a Postgres database with the `vector` extension enabled and the
`movies` table from `backend/sql/schema.sql`, populated via
`backend/app/scripts/fetch_movies.py` + `build_embeddings.py`.

### Frontend

```bash
cd frontend
cp .env.example .env.local   # defaults to http://localhost:8000, adjust if needed
npm install
npm run dev
```

### Tests

```bash
cd backend && pytest              # 66 tests
cd frontend && npm test           # 152 tests (3 skipped)
```

## Known limitations / what I'd improve next

- Rate limiting (`slowapi`, in-memory) is per-instance — fine for a single
  Railway replica, would need a shared store (Redis) to scale past one.
- No enforced coverage threshold yet; `rerank.py` and `embeddings.py` have
  thinner test coverage than the rest of the backend.
- No end-to-end tests (component + unit coverage only).

## License

[MIT](LICENSE)
