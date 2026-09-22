"""
Tests for the embeddings service.

Tests cover:
- embed_text returning a single embedding vector from the mocked OpenAI call
- embed_batch chunking requests and flattening results across batches
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services.embeddings import BATCH_SIZE, embed_batch, embed_text


def _mock_response(vectors: list[list[float]]):
    """Build a fake OpenAI embeddings response matching the client's shape."""
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=vector) for vector in vectors]
    )


class TestEmbedText:
    """Test suite for embed_text."""

    @pytest.mark.asyncio
    async def test_returns_single_embedding(self):
        """embed_text should return the embedding vector for one input string."""
        with patch(
            "app.services.embeddings.client.embeddings.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_response([[0.1, 0.2, 0.3]])

            result = await embed_text("a gripping crime thriller")

            assert result == [0.1, 0.2, 0.3]
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_text_and_model_to_client(self):
        """embed_text should forward the input text and configured model."""
        with patch(
            "app.services.embeddings.client.embeddings.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_response([[0.5]])

            await embed_text("cozy autumn movies")

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["input"] == "cozy autumn movies"
            assert call_kwargs["model"] == "text-embedding-3-small"


class TestEmbedBatch:
    """Test suite for embed_batch."""

    @pytest.mark.asyncio
    async def test_returns_embedding_per_input(self):
        """embed_batch should return one embedding per input text, in order."""
        with patch(
            "app.services.embeddings.client.embeddings.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_response([[0.1], [0.2], [0.3]])

            result = await embed_batch(["a", "b", "c"])

            assert result == [[0.1], [0.2], [0.3]]
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chunks_requests_larger_than_batch_size(self):
        """embed_batch should split inputs into BATCH_SIZE-sized chunks."""
        texts = [f"movie {i}" for i in range(BATCH_SIZE + 5)]

        with patch(
            "app.services.embeddings.client.embeddings.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = [
                _mock_response([[float(i)] for i in range(BATCH_SIZE)]),
                _mock_response([[float(i)] for i in range(5)]),
            ]

            result = await embed_batch(texts)

            assert mock_create.await_count == 2
            assert len(result) == BATCH_SIZE + 5

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_list(self):
        """embed_batch with no texts should not call the client at all."""
        with patch(
            "app.services.embeddings.client.embeddings.create",
            new_callable=AsyncMock,
        ) as mock_create:
            result = await embed_batch([])

            assert result == []
            mock_create.assert_not_awaited()
