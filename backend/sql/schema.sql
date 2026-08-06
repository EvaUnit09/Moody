-- Run manually in the Supabase SQL Editor (Database → Extensions → enable
-- "vector" first). Documents the schema already created for this project.

create table if not exists movies (
    tmdb_id bigint primary key,
    title text not null,
    original_title text,
    original_language text,
    overview text,
    genre_ids integer[],
    keywords text[],
    poster_path text,
    backdrop_path text,
    release_date date,
    popularity double precision,
    vote_average double precision,
    vote_count integer,
    embedding vector(1536)
);

create index if not exists movies_embedding_hnsw_idx
    on movies using hnsw (embedding vector_cosine_ops);
