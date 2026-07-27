# Architecture Decisions

A RAG-based movie recommendation app. Users describe a mood or scenario in plain
language ("something slow and melancholic, I just want to feel something") and
get back curated picks with reasons, instead of filtering by genre/year dropdowns.

## Core concept

1. Embed TMDB movie data (overview, keywords, genres) into a vector store
2. Embed the user's natural-language query with the same model
3. Vector search pulls top candidates
4. An LLM reranks and justifies the top 5 picks
5. Results shown with poster art and a one-line reason per pick

The RAG-then-rerank pattern is the differentiator: raw vector similarity alone
gives "in the neighborhood" results, not good judgment. Reranking with an LLM
turns it into a curated shortlist.

## Stack decisions

| Layer | Choice | Why |
| --- | --- | --- |
| Data source | TMDB API | Free, well-documented, rich metadata |
| Dataset scope | ~30k movies | Wide enough coverage for niche/obscure requests without ballooning embedding cost or prep time |
| Embedding model | OpenAI text-embedding-3-small | Cheap ($0.02/1M tokens), reliable, well-documented |
| Vector store | Supabase (pgvector) | Stays in Postgres, familiar from prior work, generous free tier |
| Backend framework | FastAPI | Project is fundamentally a RAG service, not a full-stack gateway — no need for a Node layer |
| Reranking LLM | Claude Haiku 4.5 | Fast, cheap, keeps tooling consistent with other AI projects (ops-agent, LangSmith) |
| Query caching | In-memory (dict + TTL) | Cuts redundant LLM calls on repeat queries with near-zero build cost; upgradeable to Redis later as a scaling story |
| Rate limiting | IP-based | Simplest to build, no user state required, protects the public LLM endpoint from abuse |
| Auth | None | Fully stateless and public; fits the "type a mood, get a movie" use case without added security surface area |
| Backend hosting | Railway | Usage-based pricing fits low, bursty traffic |
| Frontend hosting | Vercel | Simple deploy for a React app |
| Observability | Datadog | All-in-one: APM tracing on FastAPI + LLM Observability for the Haiku call, rather than splitting across Datadog and LangSmith |

## Observability plan

- `ddtrace-run` wraps the FastAPI app for APM
- Custom spans around: embedding call, vector search, Haiku rerank call
- Datadog LLM Observability tracks token counts, cost per request, and latency
on the Haiku call specifically
- Dashboard: requests/min, p50/p95 latency, error rate, cost per day
- Tracing scoped to `/recommend` only — not static assets or health checks,
both for free-tier limits and signal-to-noise

## Repo structure

```
movie-mood/
  backend/
    app/
      main.py
      config.py
      db.py
      models.py
      routers/
        recommend.py
      services/
        tmdb.py
        embeddings.py
        rerank.py
      scripts/
        fetch_movies.py
        build_embeddings.py
    requirements.txt
  frontend/
    src/
      App.tsx
      components/
        SearchBox.tsx
        MovieCard.tsx
        ResultsGrid.tsx
      api.ts
    package.json
  README.md
```

## Build order

1. Fetch script — pull ~30k movies from TMDB (title, overview, genres, keywords,
poster path), dump to JSON. Runs once, not called live from the app.
2. Embed + load — build a text blob per movie, embed with
text-embedding-3-small, insert into Supabase with a `vector(1536)` column.
Standalone script.
3. Test retrieval — throwaway script embedding a test query and running
cosine similarity against the table, to confirm data quality before
building anything on top of it.
4. FastAPI endpoint — `POST /recommend`: embed query → vector search top ~25 →
Haiku rerank → return top 5 with reasons.
5. Datadog instrumentation — APM tracing + custom spans + LLM Observability,
added before deploying so there's a real request flow to instrument.
6. Rate limiting — IP-based limiter (e.g. slowapi), informed by what Datadog
shows about actual traffic patterns.
7. Frontend — one search box, one results grid, poster art, one-line reasons.
Deliberately no filters/dropdowns.
8. Deploy — frontend to Vercel, backend to Railway, env vars for Supabase,
Anthropic, TMDB, and Datadog keys.
9. Polish — loading state during the LLM call, error handling, verify
in-memory cache is trimming repeat-query cost.

## Estimated costs

| Item | Cost |
| --- | --- |
| TMDB API | Free |
| Embeddings (~30k movies, one-time) | ~$0.10–0.20 |
| Supabase (pgvector) | Free tier |
| Claude Haiku (reranking) | Fractions of a cent per request; a few dollars/month at low volume |
| Railway (backend) | Usage-based, likely low single digits/month for a demo |
| Vercel (frontend) | Free tier |
| Datadog | Free tier (scoped tracing) |
| Domain (optional) | ~$12/year |

**Total: effectively free to ship, low single-digit dollars/month to keep it
always-on and demo-ready for interviews.**