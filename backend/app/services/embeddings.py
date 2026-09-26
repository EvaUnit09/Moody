from openai import AsyncOpenAI

from app.config import settings
from app.services.observability import DatadogObservability

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
PROGRESS_INTERVAL = 1000

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Lazy initialization of OpenAI client (only fails if embeddings are actually used)."""
    global _client
    if _client is None:
        if settings.openai_api_key is None:
            raise ValueError(
                "OPENAI_API_KEY is required for embedding generation. "
                "Set it in .env or environment variables."
            )
        _client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=20.0)
    return _client


@DatadogObservability.trace_embedding
async def embed_text(text: str) -> list[float]:
    client = _get_client()
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        response = await client.embeddings.create(model=EMBEDDING_MODEL, input=chunk)
        embeddings.extend(item.embedding for item in response.data)
        if len(embeddings) % PROGRESS_INTERVAL == 0 or len(embeddings) == len(texts):
            print(f"Embedded {len(embeddings)}/{len(texts)} movies")
    return embeddings
