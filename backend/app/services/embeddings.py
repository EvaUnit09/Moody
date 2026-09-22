from openai import AsyncOpenAI

from app.config import settings
from app.services.observability import DatadogObservability

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
PROGRESS_INTERVAL = 1000

client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=20.0)


@DatadogObservability.trace_embedding
async def embed_text(text: str) -> list[float]:
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        response = await client.embeddings.create(model=EMBEDDING_MODEL, input=chunk)
        embeddings.extend(item.embedding for item in response.data)
        if len(embeddings) % PROGRESS_INTERVAL == 0 or len(embeddings) == len(texts):
            print(f"Embedded {len(embeddings)}/{len(texts)} movies")
    return embeddings
