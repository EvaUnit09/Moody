# Popular Movies Ingest

Scheduled ingest script to keep the `/popular` carousel fresh by updating TMDB popularity metrics in the Supabase `movies` table.

## Overview

The `/popular` endpoint serves movies ordered by the `popularity` column in the database. Without periodic updates, those rankings become stale. This ingest script:

1. Fetches current popular and trending movies from TMDB
2. Updates `popularity`, `vote_average`, `vote_count`, and metadata in the `movies` table
3. **Preserves enriched keywords and embeddings** (does not overwrite them)

The Railway app's in-memory `__popular__` cache automatically refreshes on the next `/popular` request or periodic warm cycle (every 55 minutes) after the database is updated.

## Active Schedule

**Current cadence:** Every 12 hours (midnight and noon UTC) via GitHub Actions

The workflow runs automatically via `.github/workflows/ingest-popular.yml` with cron schedule `0 0,12 * * *`.

### Required GitHub Secrets

Before the scheduled workflow can run, configure these repository secrets:

- ✅ `TMDB_API_READ_TOKEN` - TMDB API read access token
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

If database update fails (exit 2), the shelf may be partially updated. Check GitHub Actions logs for details.

### Blast Radius

- **Scope:** Updates popularity metrics for ~100-200 movies in the `movies` table (popular + trending sets)
- **User impact:** `/popular` endpoint rankings refresh to reflect current TMDB popularity
- **What's preserved:** Enriched keywords and embeddings are NOT overwritten (popularity-only UPDATE)
- **Rollback:** Popularity values are overwritten on each run; no manual rollback needed
- **Cache:** Railway app cache refreshes automatically on next `/popular` request or warm cycle (~55min)

## Running the script

### Locally

```bash
cd backend
python -m app.scripts.ingest_popular
```

Requires environment variables in `.env`:
- `API_READ_ACCESS_TOKEN` - TMDB API read access token
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

- **0**: Success (popularity updated, `/popular` will show updated rankings on next request)
- **1**: TMDB API error (existing shelf unchanged, **safe failure**)
- **2**: Database update error (partial failure, check logs)

Monitor via GitHub Actions logs. Exit code 1 is expected occasionally (TMDB rate limits or downtime) and is safe.

## Cache Behavior

The Railway app maintains an in-memory `__popular__` cache with a 2-hour TTL. After a successful ingest:

1. The database `popularity` column is updated
2. The Railway app cache is NOT directly busted (GitHub Actions runs in a separate process)
3. The cache refreshes automatically via:
   - **Next `/popular` request** after TTL expires (2 hours)
   - **Periodic warm cycle** every 55 minutes in the Railway app

**Result:** Updated popularity rankings appear in `/popular` within 55 minutes of a successful ingest run.

**Note:** The cache bust limitation is inherent to the architecture (GitHub Actions vs. Railway process separation). A shared cache store (Redis) would enable cross-process invalidation but is not currently implemented.

## Notes

- Fetches ~100-200 movies total (3 pages popular + 2 pages trending)
- Only movies with `vote_average >= 5.0` are updated
- Duplicates across popular/trending are deduplicated by TMDB ID
- **Preserves enriched keywords and embeddings** (popularity-only UPDATE, not full upsert)
- Updates: `popularity`, `vote_average`, `vote_count`, `title`, `poster_path`, `backdrop_path`, `release_date`, `genre_ids`
- Does NOT update: `keywords`, `embedding_half`, `overview`, `original_title`, `original_language`
