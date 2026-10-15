"""Pins the span name, resource, and tags each traced pipeline stage sends to Datadog."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import db
from app.services import embeddings, observability, query_intent, rerank


@pytest.fixture
def spans(monkeypatch):
    recorded = []

    def trace(name, service, resource):
        span = SimpleNamespace(tags={}, set_tag=None)
        span.set_tag = lambda key, value: span.tags.__setitem__(key, value)
        recorded.append({"name": name, "service": service, "resource": resource, "tags": span.tags})
        context = MagicMock()
        context.__enter__.return_value = span
        return context

    monkeypatch.setattr(observability, "DDTRACE_AVAILABLE", True)
    monkeypatch.setattr(observability, "tracer", SimpleNamespace(trace=trace))
    monkeypatch.setattr(observability.settings, "dd_trace_enabled", True)
    monkeypatch.setattr(observability.settings, "dd_service", "svc")
    return recorded


def _anthropic_client(tool_input: dict) -> MagicMock:
    message = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", input=tool_input)],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=message)
    return client


async def test_embedding_span(spans):
    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * 4)]))
    with patch.object(embeddings, "_get_client", return_value=client):
        await embeddings.embed_text("cozy night")

    assert spans == [
        {
            "name": "embedding.generate",
            "service": "svc",
            "resource": "openai.text-embedding-3-small",
            "tags": {
                "embedding.model": "text-embedding-3-small",
                "embedding.provider": "openai",
                "embedding.input_length": 10,
                "embedding.dimension": 4,
            },
        }
    ]


async def test_vector_search_span(spans):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[{"tmdb_id": 1, "genre_ids": []}])

    @asynccontextmanager
    async def fake_connection():
        yield conn

    with patch.object(db, "_connection", fake_connection):
        await db.search_similar([0.1], limit=25)

    assert spans == [
        {
            "name": "vector_search.similarity",
            "service": "svc",
            "resource": "supabase.pgvector",
            "tags": {
                "vector_search.provider": "supabase",
                "vector_search.index_type": "hnsw",
                "vector_search.similarity_metric": "cosine",
                "vector_search.limit": 25,
                "vector_search.results_count": 1,
            },
        }
    ]


async def test_rerank_span(spans):
    candidates = [{"tmdb_id": 1, "title": "Heat", "overview": "A heist."}]
    client = _anthropic_client({"results": [{"tmdb_id": 1, "reason": "Tense."}]})
    with patch.object(rerank, "_get_client", return_value=client):
        await rerank.rerank("tense", candidates)

    assert spans == [
        {
            "name": "llm.rerank",
            "service": "svc",
            "resource": f"anthropic.{rerank.RERANK_MODEL}",
            "tags": {
                "llm.provider": "anthropic",
                "llm.model": rerank.RERANK_MODEL,
                "llm.operation": "rerank",
                "llm.query_length": 5,
                "llm.candidate_count": 1,
                "llm.output_count": 1,
            },
        }
    ]


async def test_query_expansion_span(spans):
    client = _anthropic_client({"expanded_query": "autumn movies"})
    with patch.object(query_intent, "_get_client", return_value=client):
        await query_intent.expand_query("fall")

    assert spans == [
        {
            "name": "llm.query_expansion",
            "service": "svc",
            "resource": f"anthropic.{query_intent.EXPANSION_MODEL}",
            "tags": {
                "llm.provider": "anthropic",
                "llm.model": query_intent.EXPANSION_MODEL,
                "llm.operation": "query_expansion",
                "llm.query_length": 4,
                "llm.expanded_query_length": 13,
            },
        }
    ]
