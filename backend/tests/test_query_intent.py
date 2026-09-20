"""
Tests for the query expansion service.

Tests cover:
- Expanding ambiguous/short queries via the mocked Anthropic tool call
- Falling back to the original query when the model returns an empty string
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services.query_intent import expand_query


def _mock_message(expanded_query: str):
    """Build a fake Anthropic tool-use response matching expand_query's shape."""
    tool_use_block = SimpleNamespace(
        type="tool_use",
        input={"expanded_query": expanded_query},
    )
    return SimpleNamespace(
        content=[tool_use_block],
        usage=SimpleNamespace(input_tokens=50, output_tokens=15),
    )


class TestExpandQuery:
    """Test suite for expand_query."""

    @pytest.mark.asyncio
    async def test_expands_ambiguous_single_word_query(self):
        """A short, title-collision-prone query should be rewritten by the model."""
        with patch(
            "app.services.query_intent.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(
                "cozy, atmospheric movies to watch during autumn"
            )

            result = await expand_query("Fall")

            assert result == "cozy, atmospheric movies to watch during autumn"
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_through_already_descriptive_query(self):
        """A clear, descriptive query can be returned unchanged by the model."""
        query = "a gripping crime thriller with unexpected twists"
        with patch(
            "app.services.query_intent.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(query)

            result = await expand_query(query)

            assert result == query

    @pytest.mark.asyncio
    async def test_falls_back_to_original_query_on_empty_response(self):
        """An empty expanded_query from the model should not blank out the search."""
        with patch(
            "app.services.query_intent.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message("")

            result = await expand_query("Fall")

            assert result == "Fall"

    @pytest.mark.asyncio
    async def test_sends_original_query_in_prompt(self):
        """The original query should be included in the prompt sent to the model."""
        with patch(
            "app.services.query_intent.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message("autumn-appropriate movies")

            await expand_query("Fall")

            call_kwargs = mock_create.call_args.kwargs
            prompt = call_kwargs["messages"][0]["content"]
            assert "Fall" in prompt
