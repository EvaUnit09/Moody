import psycopg2

from app.config import settings

DATABASE_URL = settings.supabase_db_url

def create_index():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SET statement_timeout = '10min'")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS movies_embedding_half_hnsw_idx
        ON movies
        USING hnsw (embedding_half halfvec_cosine_ops)
        WITH (m = 16, ef_construction = 64)
""")
    cur.close()
    conn.close()
    print("Index created")

if __name__ == "__main__":
    create_index()