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

from app.services import query_intent as query_intent_mod
from app.services import rerank as rerank_mod
from app.services.eval import (
    MAIN_CANDIDATE_LIMIT,
    PRE_22_CANDIDATE_LIMIT,
    PRE_22_EVAL_ENV,
    PRE_22_RERANK_MAX_TOKENS,
    EvalQuery,
    EvalResult,
    EvaluationHarness,
    candidate_limit,
    eval_uses_pre_22_settings,
    pre_22_measurement_knobs,
)


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

    @pytest.mark.asyncio
    async def test_evaluate_query_uses_main_candidate_limit_by_default(self):
        eval_query = EvalQuery(
            query="test",
            description="test",
            expected_genres=["Drama"],
            min_results=1,
        )
        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Drama",
                "genres": ["Drama"],
                "vote_average": 7.5,
                "reason": "A long enough reason for the quality check",
            },
        ]
        with (
            patch("app.services.eval.expand_query", new_callable=AsyncMock) as mock_expand,
            patch("app.services.eval.embed_text", new_callable=AsyncMock) as mock_embed,
            patch("app.services.eval.search_similar", new_callable=AsyncMock) as mock_search,
            patch("app.services.eval.rerank", new_callable=AsyncMock) as mock_rerank,
        ):
            mock_expand.side_effect = lambda q: q
            mock_embed.return_value = [0.1] * 1536
            mock_search.return_value = mock_results
            mock_rerank.return_value = mock_results
            await EvaluationHarness.evaluate_query(eval_query)

        assert mock_search.await_args.kwargs["limit"] == MAIN_CANDIDATE_LIMIT

    @pytest.mark.asyncio
    async def test_evaluate_query_pre_22_passes_limit_40(self, monkeypatch):
        monkeypatch.setenv(PRE_22_EVAL_ENV, "1")
        eval_query = EvalQuery(
            query="test",
            description="test",
            expected_genres=["Drama"],
            min_results=1,
        )
        mock_results = [
            {
                "tmdb_id": 1,
                "title": "Drama",
                "genres": ["Drama"],
                "vote_average": 7.5,
                "reason": "A long enough reason for the quality check",
            },
        ]
        with (
            patch("app.services.eval.expand_query", new_callable=AsyncMock) as mock_expand,
            patch("app.services.eval.embed_text", new_callable=AsyncMock) as mock_embed,
            patch("app.services.eval.search_similar", new_callable=AsyncMock) as mock_search,
            patch("app.services.eval.rerank", new_callable=AsyncMock) as mock_rerank,
        ):
            mock_expand.side_effect = lambda q: q
            mock_embed.return_value = [0.1] * 1536
            mock_search.return_value = mock_results
            mock_rerank.return_value = mock_results
            await EvaluationHarness.evaluate_query(eval_query)

        assert mock_search.await_args.kwargs["limit"] == PRE_22_CANDIDATE_LIMIT


class TestPre22MeasurementKnobs:
    """MOODY_EVAL_PRE_22 patches eval-only; recommend constants restore afterward."""

    def test_env_off_is_main_settings(self, monkeypatch):
        monkeypatch.delenv(PRE_22_EVAL_ENV, raising=False)
        assert eval_uses_pre_22_settings() is False
        assert candidate_limit() == MAIN_CANDIDATE_LIMIT

    def test_env_on_selects_pre_22_limit(self, monkeypatch):
        monkeypatch.setenv(PRE_22_EVAL_ENV, "1")
        assert eval_uses_pre_22_settings() is True
        assert candidate_limit() == PRE_22_CANDIDATE_LIMIT

    def test_knobs_patch_and_restore(self, monkeypatch):
        monkeypatch.setenv(PRE_22_EVAL_ENV, "1")
        original_tokens = rerank_mod.RERANK_MAX_TOKENS
        original_overview = rerank_mod.MAX_OVERVIEW_CHARS
        original_reason = rerank_mod.MAX_REASON_WORDS
        original_tool = rerank_mod.RERANK_TOOL
        original_build = rerank_mod._build_prompt
        original_format = rerank_mod._format_candidates
        original_truncate = rerank_mod._truncate_overview
        original_expand = query_intent_mod.should_expand

        with pre_22_measurement_knobs():
            assert rerank_mod.RERANK_MAX_TOKENS == PRE_22_RERANK_MAX_TOKENS
            assert query_intent_mod.should_expand("cozy rainy day movies for a sunday") is True
            prompt = rerank_mod._build_prompt(
                "Fall",
                [{"tmdb_id": 1, "title": "Fall", "overview": "x" * 400}],
            )
            assert "x" * 400 in prompt
            assert "at most" not in prompt
            assert "one-line reason" in prompt
            reason_schema = rerank_mod.RERANK_TOOL["input_schema"]["properties"]["results"]["items"]["properties"]["reason"]
            assert "description" not in reason_schema

        assert rerank_mod.RERANK_MAX_TOKENS == original_tokens
        assert rerank_mod.MAX_OVERVIEW_CHARS == original_overview
        assert rerank_mod.MAX_REASON_WORDS == original_reason
        assert rerank_mod.RERANK_TOOL is original_tool
        assert rerank_mod._build_prompt is original_build
        assert rerank_mod._format_candidates is original_format
        assert rerank_mod._truncate_overview is original_truncate
        assert query_intent_mod.should_expand is original_expand
        assert query_intent_mod.should_expand("cozy rainy day") is False

    def test_knobs_are_noop_without_env(self, monkeypatch):
        monkeypatch.delenv(PRE_22_EVAL_ENV, raising=False)
        original_tokens = rerank_mod.RERANK_MAX_TOKENS
        with pre_22_measurement_knobs():
            assert rerank_mod.RERANK_MAX_TOKENS == original_tokens
            assert query_intent_mod.should_expand("cozy rainy day") is False
