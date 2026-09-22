"""
Tests for the rerank service.

Tests cover:
- Empty candidate list short-circuiting without calling the model
- Merging model picks back onto the original candidate data
- Skipping picks that reference an unknown tmdb_id
- Truncating results to TOP_N even if the model returns more
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services.rerank import TOP_N, rerank

CANDIDATES = [
    {"tmdb_id": 1, "title": "Movie One", "overview": "A quiet drama."},
    {"tmdb_id": 2, "title": "Movie Two", "overview": "A loud comedy."},
    {"tmdb_id": 3, "title": "Movie Three", "overview": "A tense thriller."},
]


def _mock_message(picks: list[dict]):
    """Build a fake Anthropic tool-use response matching rerank's shape."""
    tool_use_block = SimpleNamespace(
        type="tool_use",
        input={"results": picks},
    )
    return SimpleNamespace(
        content=[tool_use_block],
        usage=SimpleNamespace(input_tokens=100, output_tokens=40),
    )


class TestRerank:
    """Test suite for rerank."""

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty_without_calling_model(self):
        """No candidates means nothing to rerank — skip the LLM call entirely."""
        with patch(
            "app.services.rerank.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            result = await rerank("cozy autumn movies", [])

            assert result == []
            mock_create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_merges_model_reason_onto_candidate_data(self):
        """Picked candidates should keep their original fields plus the model's reason."""
        with patch(
            "app.services.rerank.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(
                [{"tmdb_id": 2, "reason": "Great for a laugh."}]
            )

            result = await rerank("something funny", CANDIDATES)

            assert result == [
                {
                    "tmdb_id": 2,
                    "title": "Movie Two",
                    "overview": "A loud comedy.",
                    "reason": "Great for a laugh.",
                }
            ]

    @pytest.mark.asyncio
    async def test_skips_picks_with_unknown_tmdb_id(self):
        """A pick referencing an id not in the candidate pool should be dropped."""
        with patch(
            "app.services.rerank.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(
                [
                    {"tmdb_id": 999, "reason": "Not a real candidate."},
                    {"tmdb_id": 1, "reason": "A solid pick."},
                ]
            )

            result = await rerank("a quiet evening", CANDIDATES)

            assert len(result) == 1
            assert result[0]["tmdb_id"] == 1

    @pytest.mark.asyncio
    async def test_truncates_to_top_n(self):
        """Even if the model returns more picks than TOP_N, only TOP_N come back."""
        many_candidates = [
            {"tmdb_id": i, "title": f"Movie {i}", "overview": "..."}
            for i in range(TOP_N + 3)
        ]
        picks = [
            {"tmdb_id": i, "reason": f"Reason {i}"} for i in range(TOP_N + 3)
        ]

        with patch(
            "app.services.rerank.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(picks)

            result = await rerank("anything", many_candidates)

            assert len(result) == TOP_N

    @pytest.mark.asyncio
    async def test_includes_query_and_candidates_in_prompt(self):
        """The prompt sent to the model should include the query and candidate titles."""
        with patch(
            "app.services.rerank.client.messages.create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _mock_message(
                [{"tmdb_id": 1, "reason": "Fits the mood."}]
            )

            await rerank("a quiet evening", CANDIDATES)

            call_kwargs = mock_create.call_args.kwargs
            prompt = call_kwargs["messages"][0]["content"]
            assert "a quiet evening" in prompt
            assert "Movie One" in prompt
