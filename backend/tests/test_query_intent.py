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
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message("cozy, atmospheric movies to watch during autumn")
        )
        
        with patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query("Fall")

            assert result == "cozy, atmospheric movies to watch during autumn"
            mock_client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_through_already_descriptive_query(self):
        """A clear, descriptive query can be returned unchanged by the model."""
        query = "a gripping crime thriller with unexpected twists"
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_message(query))
        
        with patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query(query)

            assert result == query

    @pytest.mark.asyncio
    async def test_falls_back_to_original_query_on_empty_response(self):
        """An empty expanded_query from the model should not blank out the search."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_message(""))
        
        with patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query("Fall")

            assert result == "Fall"

    @pytest.mark.asyncio
    async def test_sends_original_query_in_prompt(self):
        """The original query should be included in the prompt sent to the model."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_message("autumn-appropriate movies"))
        
        with patch("app.services.query_intent._get_client", return_value=mock_client):
            await expand_query("Fall")

            call_kwargs = mock_client.messages.create.call_args.kwargs
            prompt = call_kwargs["messages"][0]["content"]
            assert "Fall" in prompt


class TestShouldExpandGate:
    """expand_query skips the model entirely when should_expand says no."""

    @pytest.mark.asyncio
    async def test_skips_model_when_should_expand_false(self):
        mock_client = AsyncMock()

        with patch("app.services.query_intent.should_expand", return_value=False), \
             patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query("a slow-burn psychological thriller set in a snowy small town")

        assert result == "a slow-burn psychological thriller set in a snowy small town"
        mock_client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_model_when_should_expand_true(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_message("autumn cozy movies"))

        with patch("app.services.query_intent.should_expand", return_value=True), \
             patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query("Fall")

        assert result == "autumn cozy movies"
        mock_client.messages.create.assert_called_once()


class TestShouldExpand:
    """Word-count heuristic deciding whether a query needs expansion."""

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("Fall", True),
            ("date night", True),
            ("sci-fi", True),
            ("  Fall!!  ", True),
            ("cozy rainy day", False),
            ("a slow-burn thriller in a snowy town", False),
        ],
    )
    def test_should_expand(self, query, expected):
        from app.services.query_intent import should_expand

        assert should_expand(query) is expected

    @pytest.mark.asyncio
    async def test_descriptive_query_skips_model_end_to_end(self):
        mock_client = AsyncMock()

        with patch("app.services.query_intent._get_client", return_value=mock_client):
            result = await expand_query("cozy rainy day")

        assert result == "cozy rainy day"
        mock_client.messages.create.assert_not_called()
