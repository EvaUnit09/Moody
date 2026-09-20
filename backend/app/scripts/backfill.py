import psycopg2

from app.config import settings

DATABASE_URL = settings.supabase_db_url

BATCH_SIZE = 1000


def backfill():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM movies WHERE embedding_half IS NULL")
    remaining = cur.fetchone()[0]
    print(f"Remaining: {remaining}")

    while remaining > 0:
        cur.execute(
            """
            UPDATE movies
            SET embedding_half = embedding::halfvec(1536)
            WHERE tmdb_id IN (
                SELECT tmdb_id FROM movies
                WHERE embedding_half IS NULL
                LIMIT %s
            )
            """,
            (BATCH_SIZE,),
        )
        print(f"Updated {cur.rowcount} movies")

        cur.execute("VACUUM movies")

        cur.execute("SELECT count(*) FROM movies WHERE embedding_half IS NULL")
        remaining = cur.fetchone()[0]
        print(f"Remaining: {remaining}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    backfill()