# Catalog rebuild

One-time pipeline that fills the `movies` table used by `POST /recommend`. This is separate from the popularity refresh in [INGEST_POPULAR.md](INGEST_POPULAR.md). That job only `UPDATE`s rows that already exist. This pipeline is what creates them, including keywords and `embedding_half`.

Run every command from `backend/` so `app` imports resolve. JSON lands in `backend/data/`, which is gitignored.

## Order

1. In the Supabase SQL editor, enable the `vector` extension, then run [`backend/sql/schema.sql`](../backend/sql/schema.sql). That creates `movies` and the HNSW index `movies_embedding_half_hnsw_idx` (`halfvec_cosine_ops`, `m = 16`, `ef_construction = 64`).
2. Fetch discover pages.
3. Attach keywords.
4. Embed and upsert.

```bash
cd backend
python -m app.scripts.fetch_movies
python -m app.scripts.fetch_keywords
python -m app.scripts.build_embeddings
```

| Step | Needs | Writes |
| --- | --- | --- |
| `fetch_movies` | `API_READ_ACCESS_TOKEN` | `data/raw_movies.json` |
| `fetch_keywords` | `API_READ_ACCESS_TOKEN` | `data/movies_with_keywords.json` |
| `build_embeddings` | `OPENAI_API_KEY`, `SUPABASE_DB_URL` | rows in `movies` |

`ANTHROPIC_API_KEY` is not used here. Query expansion and rerank run only on live `/recommend` traffic.

`create_index.py` builds the same HNSW index as `schema.sql`. It imports `psycopg2`, which is not in `requirements.txt`, and `CREATE INDEX IF NOT EXISTS` does nothing when the index is already there. Prefer the SQL file. Postgres maintains the existing index as rows are upserted; you do not re-run the script after a load.

## What each script keeps

### Discover (`fetch_movies.py`)

TMDB `/discover/movie`, sorted by `popularity.desc`, `include_adult=false`. A title must have `vote_count >= 20` and `vote_average >= 5.0` (`MIN_VOTE_AVERAGE` in `app/services/tmdb.py`).

Per-year quotas, so recent decades are not crowded out:

| Years | Movies requested per year |
| --- | --- |
| 2015 through the current year | 800 |
| 2000–2014 | 600 |
| 1980–1999 | 400 |
| 1950–1979 | 150 |

Pages are 20 results. Up to 15 requests run at once. Titles are deduped by TMDB id across years. The script comment targets about 30k movies; the saved count is whatever the run prints after dedupe.

A failed page is logged and stored as an empty list. The year still finishes, with a hole where that page should have been. Re-run the script if the log shows fetch failures.

### Keywords (`fetch_keywords.py`)

One `/movie/{id}/keywords` call per title, concurrency 15. A failed call stores `keywords: []` and the movie stays in the file. Empty keywords still get embedded; the blob just has an empty keyword list.

### Embed and load (`build_embeddings.py`, `db.upsert_movies`)

Each movie becomes one string:

```text
{title}. {overview} Genres: {names}. Keywords: {names}.
```

Genre names come from the hardcoded map in `tmdb.py`. Unknown ids are dropped. Embeddings are OpenAI `text-embedding-3-small` (1536 dims), sent 100 texts at a time. The client timeout is 20 seconds.

Upsert batches are 1000 rows. The vector is stored as `embedding_half halfvec(1536)` via `::vector(1536)::halfvec(1536)`. On `tmdb_id` conflict, the row is fully replaced: title, overview, genres, keywords, poster fields, release date, popularity, votes, and the embedding.

`release_date` must be an ISO date. `datetime.date.fromisoformat` runs before any insert, so one missing date aborts the whole load. `title` and `overview` are required keys on the JSON object.

## Do not mix this up with the carousel job

| | Catalog upsert | `ingest_popular` |
| --- | --- | --- |
| SQL | `INSERT ... ON CONFLICT DO UPDATE` | `UPDATE ... WHERE tmdb_id = $1` |
| New titles | Inserted | Left out (no matching row, no insert) |
| Keywords and `embedding_half` | Overwritten | Left unchanged |
| Also writes | Overview, original title, original language | Popularity, votes, title, posters, release date, `genre_ids` |

Re-running `build_embeddings` is a full metadata and vector replace for every id in the JSON file. Use `ingest_popular` when you only want fresh popularity numbers. See [INGEST_POPULAR.md](INGEST_POPULAR.md) for schedule, exit codes, and the Railway cache lag.
