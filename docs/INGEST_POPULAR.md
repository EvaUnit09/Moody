# Popular Movies Ingest

Scheduled ingest script to keep the `/popular` carousel fresh by updating TMDB popularity metrics in the Supabase `movies` table.

## Overview

The `/popular` endpoint serves movies ordered by the `popularity` column in the database. Without periodic updates, those rankings become stale. This ingest script:

1. Fetches current popular and trending movies from TMDB
2. Updates `popularity`, `vote_average`, `vote_count`, and metadata in the `movies` table
3. **Preserves enriched keywords and embeddings** (does not overwrite them)

The Railway app keeps `/popular` in an in-memory `__popular__` entry. A warm
loop reloads it every 3300 seconds (55 minutes), and the process also warms
it on startup. A request serves the cached list until that entry expires or
the warm loop replaces it. See [Cache behavior](#cache-behavior-important).

## Active Schedule

**Current cadence:** Every 12 hours (midnight and noon UTC) via GitHub Actions

The workflow runs automatically via `.github/workflows/ingest-popular.yml` with cron schedule `0 0,12 * * *`.

### Required GitHub Secrets

Before the scheduled workflow can run, configure these repository secrets:

- ✅ `TMDB_API_READ_TOKEN` - TMDB API read access token
- ✅ `SUPABASE_DB_URL` - Postgres connection string (production database)

**To configure:** Go to GitHub repo Settings → Secrets and variables → Actions → New repository secret

**Note:** `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are NOT required for this ingest workflow (popularity-only updates, no embedding generation).

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
- **Cache:** Railway serves the previous `__popular__` entry until the 55-minute warm loop or the 1-hour TTL. The next HTTP request alone does not reload the shelf while the entry is still valid.

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

- **0**: Success (popularity rows written). The carousel still serves the previous in-memory list until the warm loop or TTL described below.
- **1**: TMDB API error (existing shelf unchanged, **safe failure**)
- **2**: Database update error (partial failure, check logs)

Monitor via GitHub Actions logs. Exit code 1 is expected occasionally (TMDB rate limits or downtime) and is safe.

## Cache Behavior (Important)

**Key limitation:** GitHub Actions runs in a separate process from Railway. Any cache bust in this script is **process-local and does NOT affect Railway's cache.**

`GET /popular` calls `cache.store("__popular__", movies)` with the default TTL, which is `CACHE_TTL_SECONDS` (3600). The 2-hour TTL (`POPULAR_CACHE_TTL_SECONDS`) applies only to `/recommend` queries that match a popular-mood keyword. It does not apply to the carousel.

After a successful ingest:

1. The `popularity` column in Postgres is updated.
2. Railway's in-memory cache is left as-is. GitHub Actions cannot clear it.
3. The carousel picks up the new ranking when either of these happens:
   - The background warm loop in `main.py` runs (`POPULAR_CACHE_REFRESH_SECONDS` = 3300). It reloads from Postgres whether or not the TTL has elapsed.
   - The `__popular__` entry expires (1 hour) and the next `GET /popular` misses, which calls `warm_popular_cache()`.
   - The Railway process restarts, which warms the cache during lifespan startup.

**Freshness:** With a healthy warm loop, updated rankings show up on the next cycle, at most about 55 minutes after ingest. If the warm loop is not running, the previous list can be served until the 1-hour TTL.

The browser also keeps `movierec:popular-cache` for first paint (10 minutes). `App` still requests `/popular` on load, so that local copy is replaced as soon as the server responds.

**Why the gap exists:** GitHub Actions and Railway are separate processes. A shared cache store (Redis) would allow the ingest job to invalidate `__popular__` immediately. That store is not in the stack.

## Notes

- Fetches 3 pages of `/movie/popular` and 2 pages of weekly `/trending/movie/week` (~100–200 titles before filtering)
- Writes with `UPDATE ... WHERE tmdb_id = $1`. A title that was never embedded is left out of the catalog. The script's "updated" count is the number of statements sent, including ids that matched no row.
- Only movies with `vote_average >= 5.0` are updated
- Duplicates across popular/trending are deduplicated by TMDB ID
- **Preserves enriched keywords and embeddings** (popularity-only UPDATE, not full upsert)
- Updates: `popularity`, `vote_average`, `vote_count`, `title`, `poster_path`, `backdrop_path`, `release_date`, `genre_ids`
- Does NOT update: `keywords`, `embedding_half`, `overview`, `original_title`, `original_language`
