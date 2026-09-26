# Moody

[![CI](https://github.com/EvaUnit09/Moody/actions/workflows/ci.yml/badge.svg)](https://github.com/EvaUnit09/Moody/actions/workflows/ci.yml)

A RAG-based movie recommendation app: describe a mood or scenario in plain
language and get back curated picks with reasons, instead of filtering by
genre/year dropdowns.

**Live demo:** https://moody-alpha-three.vercel.app

## How it works

1. ~30k movies (title, overview, genres, keywords) are embedded and stored in
   Postgres as `halfvec(1536)` via pgvector.
2. Every query is sent to Claude Haiku for expansion. Short or ambiguous text
   is rewritten into a mood description; an already-clear request is returned
   unchanged. That expanded text is embedded with `text-embedding-3-small`.
   The original wording is what the reranker judges.
3. Vector search returns the top 40 candidates with `vote_average >= 5.0`.
   Hidden titles (`exclude_tmdb_ids`, at most 100) are removed from that
   list before rerank. The web client sends its local passed list when
   "don't show hidden" is on.
4. Haiku reranks that pool to at most 6 picks and writes a one-line reason
   for each, grounded in the movie's overview. Watch-provider links for the
   `US` region are attached before the response is cached.

The home screen carousel is a separate `GET /popular` read of the
`popularity` column, refreshed by the ingest job in
[docs/INGEST_POPULAR.md](docs/INGEST_POPULAR.md).

Raw vector similarity alone gives "in the neighborhood" results, not good
judgment — the rerank step is what turns it into a curated shortlist. Request
and response details, cache TTLs, and the exclude-list limit are in
[backend/README.md](backend/README.md). Browser-only state (hidden titles,
watchlist, recent moods, `?q=` links) is in
[frontend/README.md](frontend/README.md). See
[docs/architecture.md](docs/architecture.md) for the stack-decision rationale
and [docs/plan/backend-buildout.md](docs/plan/backend-buildout.md) for the
original implementation plan.

## Tech stack

- **Backend:** FastAPI (Python), asyncpg
- **Vector store:** Supabase (Postgres + pgvector, HNSW index over half-precision embeddings)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Query expansion + reranking:** Claude Haiku (Anthropic)
- **Frontend:** React + TypeScript + Vite
- **Observability:** Datadog APM + LLM Observability
- **Hosting:** Vercel (frontend), Railway (backend)


## Known limitations / what I'd improve next

- Rate limiting (`slowapi`, in-memory) is per-instance — fine for a single
  Railway replica, would need a shared store (Redis) to scale past one.
- No enforced coverage threshold yet; `rerank.py` and `embeddings.py` have
  thinner test coverage than the rest of the backend.
- No end-to-end tests (component + unit coverage only).

## License

[MIT](LICENSE)
