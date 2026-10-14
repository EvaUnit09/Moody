"""
Evaluation harness for MovieRec recommendation quality.

Provides systematic testing of recommendation quality with metrics for
relevance, diversity, and consistency.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from app.db import search_similar
from app.services import query_intent as query_intent_mod
from app.services import rerank as rerank_mod
from app.services.embeddings import embed_text
from app.services.query_intent import expand_query
from app.services.rerank import rerank

# Measurement-only. The /recommend route never reads this. Set to "1" to replay
# the pre-#22 knobs on this eval process: 40 candidates, always expand, full
# overviews, max_tokens 1024, uncapped reason text.
PRE_22_EVAL_ENV = "MOODY_EVAL_PRE_22"
MAIN_CANDIDATE_LIMIT = 25
PRE_22_CANDIDATE_LIMIT = 40
PRE_22_RERANK_MAX_TOKENS = 1024

PRE_22_RERANK_TOOL = {
    "name": "return_recommendations",
    "description": "Return the best movie recommendations with a one-line reason each.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": ["tmdb_id", "reason"],
                },
            }
        },
        "required": ["results"],
    },
}


def eval_uses_pre_22_settings() -> bool:
    return os.environ.get(PRE_22_EVAL_ENV) == "1"


def candidate_limit() -> int:
    return PRE_22_CANDIDATE_LIMIT if eval_uses_pre_22_settings() else MAIN_CANDIDATE_LIMIT


def _always_expand(_query: str) -> bool:
    return True


def _pre_22_format_candidates(candidates: list[dict]) -> str:
    return "\n".join(
        f"- tmdb_id: {c['tmdb_id']}, title: {c['title']}, overview: {c.get('overview')}"
        for c in candidates
    )


def _pre_22_build_prompt(query: str, candidates: list[dict]) -> str:
    candidate_lines = _pre_22_format_candidates(candidates)
    return (
        f'User request: "{query}"\n\n'
        f"Candidate movies (from vector search):\n{candidate_lines}\n\n"
        f"Pick the best {rerank_mod.TOP_N} matches for the user's request and give a "
        "one-line reason for each, grounded in the movie's overview. Judge "
        "fit by mood, theme, and content, not by whether the request's words "
        "literally appear in the title — a movie titled after the request "
        "isn't a good match unless its overview also fits."
    )


def _pre_22_truncate_overview(overview: str | None) -> str:
    return (overview or "").strip()


@contextmanager
def pre_22_measurement_knobs() -> Iterator[None]:
    """Patch expansion and rerank for a pre-#22 eval process, then restore.

    Does not touch the recommend router. Safe to use when the env var is unset
    (no-op) so evaluate_query can always wrap the pipeline.
    """
    if not eval_uses_pre_22_settings():
        yield
        return

    previous_should_expand = query_intent_mod.should_expand
    previous_max_tokens = rerank_mod.RERANK_MAX_TOKENS
    previous_max_overview = rerank_mod.MAX_OVERVIEW_CHARS
    previous_max_reason = rerank_mod.MAX_REASON_WORDS
    previous_tool = rerank_mod.RERANK_TOOL
    previous_build_prompt = rerank_mod._build_prompt
    previous_format_candidates = rerank_mod._format_candidates
    previous_truncate = rerank_mod._truncate_overview

    query_intent_mod.should_expand = _always_expand
    rerank_mod.RERANK_MAX_TOKENS = PRE_22_RERANK_MAX_TOKENS
    rerank_mod.MAX_OVERVIEW_CHARS = 10**9
    rerank_mod.MAX_REASON_WORDS = 10**9
    rerank_mod.RERANK_TOOL = PRE_22_RERANK_TOOL
    rerank_mod._build_prompt = _pre_22_build_prompt
    rerank_mod._format_candidates = _pre_22_format_candidates
    rerank_mod._truncate_overview = _pre_22_truncate_overview
    try:
        yield
    finally:
        query_intent_mod.should_expand = previous_should_expand
        rerank_mod.RERANK_MAX_TOKENS = previous_max_tokens
        rerank_mod.MAX_OVERVIEW_CHARS = previous_max_overview
        rerank_mod.MAX_REASON_WORDS = previous_max_reason
        rerank_mod.RERANK_TOOL = previous_tool
        rerank_mod._build_prompt = previous_build_prompt
        rerank_mod._format_candidates = previous_format_candidates
        rerank_mod._truncate_overview = previous_truncate


@dataclass
class EvalQuery:
    """Test query with expected characteristics for evaluation."""
    
    query: str
    description: str
    expected_genres: list[str]  # At least one must be present in results
    min_results: int = 3
    min_reason_length: int = 20  # Minimum characters in reason to be considered quality


@dataclass
class EvalResult:
    """Results from evaluating a single query."""
    
    query: str
    description: str
    results_count: int
    unique_genres_count: int
    genres_found: list[str]
    expected_genres_matched: int
    avg_vote_average: float
    avg_reason_length: float
    titles: list[str]
    reasons: list[str]
    passed: bool
    notes: str = ""


class EvaluationHarness:
    """Evaluation harness for systematic quality testing of recommendations."""

    @staticmethod
    def get_test_queries() -> list[EvalQuery]:
        """
        Return a curated set of test queries covering different moods and scenarios.
        
        These queries test:
        - Emotional/mood-based requests
        - Scenario-based requests
        - Genre-specific but mood-constrained requests
        - Abstract/conceptual requests
        """
        return [
            EvalQuery(
                query="something slow and melancholic, I just want to feel something",
                description="Emotional/mood request (slow, melancholic)",
                expected_genres=["Drama", "Romance"],
                min_results=3,
            ),
            EvalQuery(
                query="a lighthearted comedy for Friday night with friends",
                description="Scenario-based request (social gathering, light mood)",
                expected_genres=["Comedy"],
                min_results=3,
            ),
            EvalQuery(
                query="a mind-bending sci-fi movie that makes you question reality",
                description="Genre + mood request (sci-fi, mind-bending)",
                expected_genres=["Science Fiction", "Thriller", "Mystery"],
                min_results=3,
            ),
            EvalQuery(
                query="something dark and atmospheric for a rainy Sunday afternoon",
                description="Mood + context request (dark, atmospheric, lazy day)",
                expected_genres=["Thriller", "Drama", "Mystery", "Horror"],
                min_results=3,
            ),
            EvalQuery(
                query="an uplifting adventure that restores faith in humanity",
                description="Emotional outcome request (uplifting, inspiring)",
                expected_genres=["Adventure", "Drama", "Family"],
                min_results=3,
            ),
            EvalQuery(
                query="a gripping crime thriller with unexpected twists",
                description="Genre + characteristics request (crime, twists)",
                expected_genres=["Crime", "Thriller", "Mystery"],
                min_results=3,
            ),
            EvalQuery(
                query="something visually stunning with minimal dialogue",
                description="Artistic characteristics request (visual, minimal dialogue)",
                expected_genres=["Drama", "Fantasy", "Science Fiction", "Animation"],
                min_results=3,
            ),
            EvalQuery(
                query="a heartwarming family movie for all ages",
                description="Audience + mood request (family-friendly, heartwarming)",
                expected_genres=["Family", "Animation", "Adventure"],
                min_results=3,
            ),
            EvalQuery(
                query="Fall",
                description=(
                    "Ambiguous single-word season query — regression guard for "
                    "literal title-match bias (should mean 'autumn-appropriate "
                    "movies', not the movie titled Fall)"
                ),
                expected_genres=["Drama", "Romance", "Family", "Comedy", "Fantasy"],
                min_results=3,
            ),
        ]

    @staticmethod
    async def evaluate_query(eval_query: EvalQuery) -> EvalResult:
        """
        Evaluate a single query through the full recommendation pipeline.
        
        Returns metrics including result count, genre diversity, expected genre matching,
        and reason quality indicators.
        """
        # Run through the full pipeline. pre_22_measurement_knobs is a no-op
        # unless MOODY_EVAL_PRE_22=1, so /recommend is unaffected.
        with pre_22_measurement_knobs():
            search_query = await expand_query(eval_query.query)
            embedding = await embed_text(search_query)
            candidates = await search_similar(embedding, limit=candidate_limit())
            results = await rerank(eval_query.query, candidates)

        # Calculate metrics
        results_count = len(results)
        genres_set = set()
        vote_averages = []
        titles = []
        reasons = []
        reason_lengths = []

        for result in results:
            genres_set.update(result.get("genres", []))
            vote_averages.append(result.get("vote_average", 0))
            titles.append(result.get("title", "Unknown"))
            reason = result.get("reason", "")
            reasons.append(reason)
            reason_lengths.append(len(reason))

        avg_vote_average = sum(vote_averages) / len(vote_averages) if vote_averages else 0
        avg_reason_length = sum(reason_lengths) / len(reason_lengths) if reason_lengths else 0
        unique_genres_count = len(genres_set)

        # Check how many expected genres are present in results
        expected_genres_matched = sum(
            1 for genre in eval_query.expected_genres if genre in genres_set
        )

        # Determine if query passed quality checks
        passed = (
            results_count >= eval_query.min_results
            and unique_genres_count > 0
            and avg_vote_average >= 6.0
            and expected_genres_matched > 0  # At least one expected genre must match
            and avg_reason_length >= eval_query.min_reason_length  # Reasons must be substantive
        )

        notes = []
        if results_count < eval_query.min_results:
            notes.append(f"Insufficient results: {results_count} < {eval_query.min_results}")
        if unique_genres_count == 0:
            notes.append("No genres found in results")
        if avg_vote_average < 6.0:
            notes.append(f"Low average rating: {avg_vote_average:.2f}")
        if expected_genres_matched == 0:
            notes.append(f"No expected genres matched (expected: {', '.join(eval_query.expected_genres)})")
        if avg_reason_length < eval_query.min_reason_length:
            notes.append(f"Reasons too short: {avg_reason_length:.1f} < {eval_query.min_reason_length}")

        return EvalResult(
            query=eval_query.query,
            description=eval_query.description,
            results_count=results_count,
            unique_genres_count=unique_genres_count,
            genres_found=sorted(genres_set),
            expected_genres_matched=expected_genres_matched,
            avg_vote_average=avg_vote_average,
            avg_reason_length=avg_reason_length,
            titles=titles,
            reasons=reasons,
            passed=passed,
            notes="; ".join(notes) if notes else "All checks passed",
        )

    @staticmethod
    async def run_evaluation() -> dict[str, Any]:
        """
        Run the full evaluation suite and return aggregated results.
        
        Returns a summary with overall pass rate, metrics distribution,
        and individual query results.
        """
        test_queries = EvaluationHarness.get_test_queries()
        results = []

        for eval_query in test_queries:
            result = await EvaluationHarness.evaluate_query(eval_query)
            results.append(result)

        # Calculate aggregate metrics
        total_queries = len(results)
        passed_queries = sum(1 for r in results if r.passed)
        pass_rate = passed_queries / total_queries if total_queries > 0 else 0

        avg_results_per_query = sum(r.results_count for r in results) / total_queries if total_queries > 0 else 0
        avg_genre_diversity = sum(r.unique_genres_count for r in results) / total_queries if total_queries > 0 else 0
        avg_rating = sum(r.avg_vote_average for r in results) / total_queries if total_queries > 0 else 0

        return {
            "summary": {
                "total_queries": total_queries,
                "passed_queries": passed_queries,
                "failed_queries": total_queries - passed_queries,
                "pass_rate": round(pass_rate, 3),
                "avg_results_per_query": round(avg_results_per_query, 2),
                "avg_genre_diversity": round(avg_genre_diversity, 2),
                "avg_rating": round(avg_rating, 2),
                "settings": "pre_22" if eval_uses_pre_22_settings() else "main",
                "candidate_limit": candidate_limit(),
            },
            "results": [
                {
                    "query": r.query,
                    "description": r.description,
                    "passed": r.passed,
                    "results_count": r.results_count,
                    "unique_genres_count": r.unique_genres_count,
                    "genres_found": r.genres_found,
                    "expected_genres_matched": r.expected_genres_matched,
                    "avg_vote_average": round(r.avg_vote_average, 2),
                    "avg_reason_length": round(r.avg_reason_length, 1),
                    "titles": r.titles,
                    "reasons": r.reasons,
                    "notes": r.notes,
                }
                for r in results
            ],
        }
