"""
Tests for evaluation harness.

Tests cover:
- EvalQuery and EvalResult dataclasses
- Expected genre matching logic
- Reason quality checks
- Pass/fail criteria
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Set dummy env vars before importing app
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services.eval import EvalQuery, EvalResult, EvaluationHarness


class TestEvalQuery:
    """Test EvalQuery dataclass."""

    def test_eval_query_creation(self):
        """EvalQuery should be created with required fields."""
        query = EvalQuery(
            query="test query",
            description="test description",
            expected_genres=["Drama", "Comedy"],
            min_results=3,
        )
        assert query.query == "test query"
        assert query.expected_genres == ["Drama", "Comedy"]
        assert query.min_results == 3
        assert query.min_reason_length == 20  # default

    def test_eval_query_custom_reason_length(self):
        """EvalQuery should accept custom min_reason_length."""
        query = EvalQuery(
            query="test",
            description="test",
            expected_genres=["Drama"],
            min_reason_length=50,
        )
        assert query.min_reason_length == 50


class TestEvalResult:
    """Test EvalResult dataclass."""

    def test_eval_result_creation(self):
        """EvalResult should capture all quality metrics."""
        result = EvalResult(
            query="test query",
            description="test description",
            results_count=5,
            unique_genres_count=3,
            genres_found=["Drama", "Comedy", "Thriller"],
            expected_genres_matched=2,
            avg_vote_average=7.5,
            avg_reason_length=45.2,
            titles=["Movie 1", "Movie 2"],
            reasons=["Reason 1", "Reason 2"],
            passed=True,
            notes="All checks passed",
        )
        assert result.results_count == 5
        assert result.expected_genres_matched == 2
        assert result.avg_reason_length == 45.2
        assert result.passed is True


class TestEvaluationHarness:
    """Test EvaluationHarness static methods."""

    def test_get_test_queries(self):
        """get_test_queries should return 9 curated queries."""
        queries = EvaluationHarness.get_test_queries()
        assert len(queries) == 9
        assert all(isinstance(q, EvalQuery) for q in queries)
        assert all(len(q.expected_genres) > 0 for q in queries)
        assert all(q.min_results >= 3 for q in queries)

    def test_test_queries_have_expected_genres(self):
        """All test queries should have expected_genres defined."""
        queries = EvaluationHarness.get_test_queries()
        for query in queries:
            assert len(query.expected_genres) > 0, f"Query '{query.query}' has no expected genres"

    @pytest.mark.asyncio
    async def test_evaluate_query_expected_genre_matching(self):
        """evaluate_query should check expected genre matching."""
        eval_query = EvalQuery(
            query="test comedy",
            description="test",
            expected_genres=["Comedy", "Romance"],
            min_results=2,
        )

        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Comedy Movie",
                "genres": ["Comedy", "Drama"],
                "vote_average": 7.5,
                "reason": "A hilarious comedy perfect for the request",
            },
            {
                "tmdb_id": 2,
                "title": "Drama Movie",
                "genres": ["Drama"],
                "vote_average": 8.0,
                "reason": "A compelling dramatic story that fits",
            },
        ]

        with patch('app.services.eval.expand_query', new_callable=AsyncMock) as mock_expand:
            with patch('app.services.eval.embed_text', new_callable=AsyncMock) as mock_embed:
                with patch('app.services.eval.search_similar', new_callable=AsyncMock) as mock_search:
                    with patch('app.services.eval.rerank', new_callable=AsyncMock) as mock_rerank:
                        mock_expand.side_effect = lambda q: q
                        mock_embed.return_value = [0.1] * 1536
                        mock_search.return_value = mock_results
                        mock_rerank.return_value = mock_results

                        result = await EvaluationHarness.evaluate_query(eval_query)

                        # Should match "Comedy" from expected genres
                        assert result.expected_genres_matched == 1
                        assert "Comedy" in result.genres_found
                        assert result.results_count == 2

    @pytest.mark.asyncio
    async def test_evaluate_query_reason_quality(self):
        """evaluate_query should check reason length quality."""
        eval_query = EvalQuery(
            query="test",
            description="test",
            expected_genres=["Drama"],
            min_results=1,
            min_reason_length=30,
        )

        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Good Movie",
                "genres": ["Drama"],
                "vote_average": 7.5,
                "reason": "This is a good reason that is long enough to pass the quality check",
            },
        ]

        with patch('app.services.eval.expand_query', new_callable=AsyncMock) as mock_expand:
            with patch('app.services.eval.embed_text', new_callable=AsyncMock) as mock_embed:
                with patch('app.services.eval.search_similar', new_callable=AsyncMock) as mock_search:
                    with patch('app.services.eval.rerank', new_callable=AsyncMock) as mock_rerank:
                        mock_expand.side_effect = lambda q: q
                        mock_embed.return_value = [0.1] * 1536
                        mock_search.return_value = mock_results
                        mock_rerank.return_value = mock_results

                        result = await EvaluationHarness.evaluate_query(eval_query)

                        assert result.avg_reason_length >= 30
                        assert result.passed is True

    @pytest.mark.asyncio
    async def test_evaluate_query_short_reasons_fail(self):
        """evaluate_query should fail when reasons are too short."""
        eval_query = EvalQuery(
            query="test",
            description="test",
            expected_genres=["Drama"],
            min_results=1,
            min_reason_length=30,
        )

        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Movie",
                "genres": ["Drama"],
                "vote_average": 7.5,
                "reason": "Short reason",  # Only 12 chars
            },
        ]

        with patch('app.services.eval.expand_query', new_callable=AsyncMock) as mock_expand:
            with patch('app.services.eval.embed_text', new_callable=AsyncMock) as mock_embed:
                with patch('app.services.eval.search_similar', new_callable=AsyncMock) as mock_search:
                    with patch('app.services.eval.rerank', new_callable=AsyncMock) as mock_rerank:
                        mock_expand.side_effect = lambda q: q
                        mock_embed.return_value = [0.1] * 1536
                        mock_search.return_value = mock_results
                        mock_rerank.return_value = mock_results

                        result = await EvaluationHarness.evaluate_query(eval_query)

                        assert result.avg_reason_length < 30
                        assert result.passed is False
                        assert "too short" in result.notes

    @pytest.mark.asyncio
    async def test_evaluate_query_no_expected_genre_match_fails(self):
        """evaluate_query should fail when no expected genres match."""
        eval_query = EvalQuery(
            query="horror movie",
            description="test",
            expected_genres=["Horror", "Thriller"],
            min_results=1,
        )

        # Results have Comedy, not Horror or Thriller
        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Comedy Movie",
                "genres": ["Comedy"],
                "vote_average": 7.5,
                "reason": "A funny comedy that makes you laugh out loud",
            },
        ]

        with patch('app.services.eval.expand_query', new_callable=AsyncMock) as mock_expand:
            with patch('app.services.eval.embed_text', new_callable=AsyncMock) as mock_embed:
                with patch('app.services.eval.search_similar', new_callable=AsyncMock) as mock_search:
                    with patch('app.services.eval.rerank', new_callable=AsyncMock) as mock_rerank:
                        mock_expand.side_effect = lambda q: q
                        mock_embed.return_value = [0.1] * 1536
                        mock_search.return_value = mock_results
                        mock_rerank.return_value = mock_results

                        result = await EvaluationHarness.evaluate_query(eval_query)

                        assert result.expected_genres_matched == 0
                        assert result.passed is False
                        assert "expected genres matched" in result.notes.lower()

    @pytest.mark.asyncio
    async def test_evaluate_query_all_criteria(self):
        """evaluate_query should check all pass criteria."""
        eval_query = EvalQuery(
            query="great drama",
            description="test",
            expected_genres=["Drama"],
            min_results=2,
            min_reason_length=25,
        )

        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Drama 1",
                "genres": ["Drama"],
                "vote_average": 7.5,
                "reason": "An emotionally powerful drama that resonates",
            },
            {
                "tmdb_id": 2,
                "title": "Drama 2",
                "genres": ["Drama", "Romance"],
                "vote_average": 8.0,
                "reason": "A beautifully crafted story of love and loss",
            },
        ]

        with patch('app.services.eval.expand_query', new_callable=AsyncMock) as mock_expand:
            with patch('app.services.eval.embed_text', new_callable=AsyncMock) as mock_embed:
                with patch('app.services.eval.search_similar', new_callable=AsyncMock) as mock_search:
                    with patch('app.services.eval.rerank', new_callable=AsyncMock) as mock_rerank:
                        mock_expand.side_effect = lambda q: q
                        mock_embed.return_value = [0.1] * 1536
                        mock_search.return_value = mock_results
                        mock_rerank.return_value = mock_results

                        result = await EvaluationHarness.evaluate_query(eval_query)

                        # All criteria should pass
                        assert result.results_count >= 2
                        assert result.expected_genres_matched > 0
                        assert result.avg_vote_average >= 6.0
                        assert result.avg_reason_length >= 25
                        assert result.passed is True
                        assert result.notes == "All checks passed"
