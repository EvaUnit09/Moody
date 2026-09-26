# Popular Movies Ingest

Scheduled ingest script to keep the `/popular` carousel fresh by re-upserting TMDB popular and trending movies into the Supabase `movies` table.

## Overview

The `/popular` endpoint serves movies ordered by the `popularity` column in the database. Without periodic updates, those rankings become stale. This ingest script:

1. Fetches current popular and trending movies from TMDB
2. Generates embeddings for them (OpenAI `text-embedding-3-small`)
3. Upserts into `movies` table (updates `popularity`, `vote_average`, etc.)
4. Busts the `__popular__` in-memory cache so the next `/popular` request sees fresh data

## Running the script

### Locally

```bash
cd backend
python -m app.scripts.ingest_popular
```

Requires environment variables in `.env`:
- `API_READ_ACCESS_TOKEN` - TMDB API read access token
- `OPENAI_API_KEY` - OpenAI API key for embeddings
- `SUPABASE_DB_URL` - Postgres connection string

### Via GitHub Actions

A workflow stub is provided in `.github/workflows/ingest-popular.yml`:

1. **Configure secrets** in GitHub repo settings:
   - `TMDB_API_READ_TOKEN`
   - `OPENAI_API_KEY`
   - `SUPABASE_DB_URL`

2. **Set schedule**: Uncomment and adjust the `cron` line in the workflow.
   - **Suggested cadence**: Daily (every 12-24 hours)
   - Example: `0 6 * * *` runs at 6 AM UTC daily

3. **Enable workflow**: The workflow is set to `workflow_dispatch` (manual) by default for testing.

### Via Railway / Production cron

Ops may prefer to run this as a Railway cron job:

```bash
cd backend && python -m app.scripts.ingest_popular
```

Railway environment variables should already include the required keys.

## Exit codes

- **0**: Success (movies ingested, cache busted)
- **1**: TMDB API error (existing shelf unchanged, safe failure)
- **2**: Database or embedding error (partial failure)

## Failure handling

If TMDB is down, the script exits with code 1 and **does not modify the database**. The existing popular shelf remains available.

If embeddings or DB upsert fail (exit 2), the shelf may be partially updated. Check logs for details.

## Cache behavior

After successful ingest, the `__popular__` cache key is deleted from the in-memory cache. The next `/popular` request will fetch fresh rankings from the DB and repopulate the cache.

- **Cache TTL**: 2 hours (7200s) as defined in `app/cache.py`
- **Periodic refresh**: The main app also warms the cache every 55 minutes

## Notes

- Fetches ~100-200 movies total (3 pages popular + 2 pages trending)
- Only movies with `vote_average >= 5.0` are ingested
- Duplicates across popular/trending are deduplicated by TMDB ID
- Embeddings are regenerated on every ingest (ensures consistency if movie overviews change)
