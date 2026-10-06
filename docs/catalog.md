# Catalog load

One-time path that fills `movies` before `/recommend` or `/popular` can return anything. This is separate from the scheduled popularity refresh in [INGEST_POPULAR.md](INGEST_POPULAR.md). That job only `UPDATE`s rows that already exist.

Run the scripts from `backend/` so `app` imports resolve. `TMDB_API_READ_TOKEN` and `SUPABASE_DB_URL` come from `.env`. `OPENAI_API_KEY` is required only for the embedding step.

```bash
mkdir -p data
python -m app.scripts.fetch_movies
python -m app.scripts.fetch_keywords
python -m app.scripts.build_embeddings
```

JSON lands in `backend/data/` and is gitignored (`raw_movies.json`, `movies_with_keywords.json`). The scripts do not create `data/`; opening the output file fails if the directory is missing.

Apply `sql/schema.sql` in the Supabase SQL editor before the upsert. Enable the `vector` extension first. The table stores one `embedding_half halfvec(1536)` column. There is no full-precision `vector` column.

## Discover (`fetch_movies.py`)

TMDB `/discover/movie`, sorted by `popularity.desc`, `include_adult=false`. Filters: `vote_count >= 20` and `vote_average >= 5.0` (`MIN_VOTE_AVERAGE` in `tmdb.py`). Concurrency is 15, timeout 30s. Movies are deduped by TMDB id across years.

Per-year quotas (page size 20):

| Years | Movies requested per year |
| --- | --- |
| 2015 through the current year | 800 |
| 2000–2014 | 600 |
| 1980–1999 | 400 |
| 1950–1979 | 150 |

A failed page is printed and stored as an empty list, so a year can finish under quota. The script does not drop rows that lack `release_date`. That check happens later, at upsert.

## Keywords (`fetch_keywords.py`)

Reads `data/raw_movies.json` and calls `/movie/{id}/keywords` (concurrency 15, timeout 30s). A failed call stores `[]` for that id and continues. Writes `data/movies_with_keywords.json`.

## Embed and upsert (`build_embeddings.py`, `embeddings.py`, `db.py`)

Each movie becomes one string:

```text
{title}. {overview} Genres: {names}. Keywords: {names}.
```

Genre names come from the hardcoded `GENRE_MAP` in `tmdb.py`. Unknown ids are dropped. Keywords are joined as stored; an empty list leaves `Keywords: .`.

`embed_batch` calls OpenAI `text-embedding-3-small` in chunks of 100 (timeout 20s). That batch helper is not wrapped in the `embedding.generate` span. Only `embed_text`, used by `/recommend`, is.

`upsert_movies` writes batches of 1000 with `ON CONFLICT (tmdb_id) DO UPDATE`. A rerun replaces keywords, overview, and `embedding_half`. The value is cast `$14::vector(1536)::halfvec(1536)`. `release_date` is parsed with `date.fromisoformat` while building the row list, before any batch is sent. A missing or non-ISO date aborts the script with nothing written. A failure inside a later batch can leave earlier batches committed: the loop uses autocommit, not one transaction.

`ingest_popular` does not insert. A title that never made it through this upsert stays off the carousel.

## HNSW index

`sql/schema.sql` creates `movies_embedding_half_hnsw_idx` on `embedding_half` with `halfvec_cosine_ops` (`m = 16`, `ef_construction = 64`). Search orders by `embedding_half <=> $1` and drops rows under `vote_average` 5.0.

`app/scripts/create_index.py` runs the same `CREATE INDEX IF NOT EXISTS` with a 10-minute statement timeout. It imports `psycopg2`, which is not in `requirements.txt`. Prefer the SQL file. Re-running either path is a no-op once the index exists.
