import asyncio

from app.db import close_pool, search_similar
from app.routers.recommend import CANDIDATE_LIMIT
from app.scripts.test_retrieval import QUERIES
from app.services.embeddings import embed_text
from app.services.rerank import rerank

OVERVIEW_CHARS = 160


async def test_retrieval_reranked() -> None:
    for query in QUERIES:
        embedding = await embed_text(query)
        candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
        results = await rerank(query, candidates)

        print(f"\n{'=' * 72}")
        print(f"Query: {query}")
        print(f"{'=' * 72}")

        for i, movie in enumerate(results, 1):
            overview = movie["overview"] or ""
            if len(overview) > OVERVIEW_CHARS:
                overview = overview[:OVERVIEW_CHARS].rstrip() + "..."
            print(f"{i}. {movie['title']} (vote_average={movie['vote_average']})")
            print(f"   reason: {movie['reason']}")
            print(f"   {overview}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(test_retrieval_reranked())
