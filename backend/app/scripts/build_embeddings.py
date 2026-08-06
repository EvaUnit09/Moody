import asyncio
import json
from pathlib import Path

from app.services.embeddings import embed_batch
from app.services.tmdb import genre_names

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def build_blob(movie: dict) -> str:
    genres = ", ".join(genre_names(movie.get("genre_ids", [])))
    keywords = ", ".join(movie.get("keywords", []))
    return (
        f"{movie['title']}. {movie['overview']} "
        f"Genres: {genres}. Keywords: {keywords}."
    )


async def build_embeddings() -> None:
    with open(DATA_DIR / "movies_with_keywords.json") as f:
        movies = json.load(f)

    blobs = [build_blob(movie) for movie in movies]
    embeddings = await embed_batch(blobs)

    empty_keyword_count = sum(1 for movie in movies if not movie.get("keywords"))
    avg_blob_length = sum(len(blob) for blob in blobs) / len(blobs)

    print(f"Embedded {len(embeddings)} movies")
    print(f"Movies with empty keywords: {empty_keyword_count}")
    print(f"Average blob length: {avg_blob_length:.1f} chars")


if __name__ == "__main__":
    asyncio.run(build_embeddings())
