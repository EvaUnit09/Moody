import asyncio

from app.db import close_pool, search_similar
from app.services.embeddings import embed_text

QUERIES = [
    "something slow and melancholic",
    "a lightheared comedy for Friday night",
    "a mind-bending sc-fi movie",
    "a tense thriller with a twist",
    "an epic fantasy adventure",
    "A young Johnny Depp",
]

RESULTS_PER_QUERY = 10
OVERVIEW_CHARS = 160

async def test_retrieval() -> None:
    for query in QUERIES:
        embedding = await embed_text(query)
        results = await search_similar(embedding, limit=RESULTS_PER_QUERY)

        print(f"\n{'=' * 72}")
        print(f"Query: {query}")
        print(f"{'=' * 72}")

        for i, movie in enumerate(results, 1):
            overview = movie["overview"] or ''
            if len(overview) > OVERVIEW_CHARS:
                overview = overview[:OVERVIEW_CHARS].rstrip() + "..."
            print(f"{i}. {movie['title']} distance={movie['distance']:.4f}")
            print(f"   {overview}")

    
    await close_pool


if __name__ == "__main__":
    asyncio.run(test_retrieval())