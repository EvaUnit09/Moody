# Popular Movies Ingest

Scheduled ingest script to keep the `/popular` carousel fresh by re-upserting TMDB popular and trending movies into the Supabase `movies` table.

## Overview

The `/popular` endpoint serves movies ordered by the `popularity` column in the database. Without periodic updates, those rankings become stale. This ingest script:

1. Fetches current popular and trending movies from TMDB
2. Generates embeddings for them (OpenAI `text-embedding-3-small`)
3. Upserts into `movies` table (updates `popularity`, `vote_average`, etc.)
4. Busts the `__popular__` in-memory cache so the next `/popular` request sees fresh data

## Active Schedule

**Current cadence:** Every 12 hours (midnight and noon UTC) via GitHub Actions

The workflow runs automatically via `.github/workflows/ingest-popular.yml` with cron schedule `0 0,12 * * *`.

### Required GitHub Secrets

Before the scheduled workflow can run, configure these repository secrets:

- ✅ `TMDB_API_READ_TOKEN` - TMDB API read access token
- ✅ `OPENAI_API_KEY` - OpenAI API key for embeddings  
- ✅ `SUPABASE_DB_URL` - Postgres connection string (production database)

**To configure:** Go to GitHub repo Settings → Secrets and variables → Actions → New repository secret

### Adjusting the Schedule

To change the cadence, edit the `cron` line in `.github/workflows/ingest-popular.yml`:

- **Daily (once per day):** `0 6 * * *` - runs at 6 AM UTC
- **Every 6 hours:** `0 0,6,12,18 * * *` - runs at midnight, 6am, noon, 6pm UTC
- **Every 24 hours:** `0 0 * * *` - runs at midnight UTC

After editing, commit and push to `main`. The next run will follow the new schedule.

### Rollback / Disabling

To disable scheduled runs:

1. **Option A (temporary):** Comment out the `schedule` block in the workflow:
   ```yaml
   # schedule:
   #   - cron: "0 0,12 * * *"
   ```

2. **Option B (permanent):** Delete the workflow file or disable it via GitHub Actions UI

Manual runs via `workflow_dispatch` remain available regardless of schedule state.

## Failure Handling & Blast Radius

### Fail-Safe Behavior

If TMDB is down or unreachable, the script exits with code 1 and **does not modify the database**. The existing popular shelf remains available to users.

If embeddings or DB upsert fail (exit 2), the shelf may be partially updated. Check GitHub Actions logs for details.

### Blast Radius

- **Scope:** Updates ~100-200 movies in the `movies` table (popular + trending sets)
- **User impact:** `/popular` endpoint rankings refresh to reflect current TMDB popularity
- **Rollback:** Popularity values are overwritten on each run; no manual rollback needed
- **Cache:** In-memory `__popular__` cache is busted after successful ingest

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

### Via GitHub Actions (Active)

The workflow in `.github/workflows/ingest-popular.yml` is **currently enabled** and runs every 12 hours.

**Monitoring:**
- View workflow runs: GitHub repo → Actions → "Ingest Popular Movies"
- Check logs for each run to verify success or diagnose failures
- Failed runs will show in the Actions tab with red X indicators

**Manual trigger:**
- Go to Actions → "Ingest Popular Movies" → "Run workflow" → Select branch → "Run workflow"
- Useful for testing or forcing an immediate refresh

### Via Railway / Production cron

Ops may prefer to run this as a Railway cron job:

```bash
cd backend && python -m app.scripts.ingest_popular
```

Railway environment variables should already include the required keys.

## Exit Codes & Monitoring

- **0**: Success (movies ingested, cache busted, `/popular` will show updated rankings)
- **1**: TMDB API error (existing shelf unchanged, **safe failure**)
- **2**: Database or embedding error (partial failure, check logs)

Monitor via GitHub Actions logs. Exit code 1 is expected occasionally (TMDB rate limits or downtime) and is safe.

## Cache behavior

After successful ingest, the `__popular__` cache key is deleted from the in-memory cache. The next `/popular` request will fetch fresh rankings from the DB and repopulate the cache.

- **Cache TTL**: 2 hours (7200s) as defined in `app/cache.py`
- **Periodic refresh**: The main app also warms the cache every 55 minutes

## Notes

- Fetches ~100-200 movies total (3 pages popular + 2 pages trending)
- Only movies with `vote_average >= 5.0` are ingested
- Duplicates across popular/trending are deduplicated by TMDB ID
- Embeddings are regenerated on every ingest (ensures consistency if movie overviews change)
