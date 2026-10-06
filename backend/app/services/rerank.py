from anthropic import AsyncAnthropic

from app.config import settings
from app.services.observability import DatadogObservability

try:
    # Try importing from ddtrace.llmobs.types first (ddtrace 4.x+)
    from ddtrace.llmobs.types import Prompt
    PROMPT_AVAILABLE = True
except ImportError:
    try:
        # Fallback to ddtrace.llmobs for older versions
        from ddtrace.llmobs import Prompt
        PROMPT_AVAILABLE = True
    except ImportError:
        Prompt = None
        PROMPT_AVAILABLE = False

RERANK_MODEL = "claude-haiku-4-5"
TOP_N = 6
# Output tokens dominate rerank latency: Haiku writes each reason token by token,
# so cap reason length and the token budget. 6 short reasons fit well under 512.
RERANK_MAX_TOKENS = 512
MAX_REASON_WORDS = 15
# Trims input tokens; the opening of an overview carries most of its mood/premise.
MAX_OVERVIEW_CHARS = 300

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    """Lazy initialization of Anthropic client (only fails if reranking is actually used)."""
    global _client
    if _client is None:
        if settings.anthropic_api_key is None:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for reranking. "
                "Set it in .env or environment variables."
            )
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=20.0)
    return _client

RERANK_TOOL = {
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
                        "reason": {
                            "type": "string",
                            "description": f"One short sentence, at most {MAX_REASON_WORDS} words.",
                        },
                    },
                    "required": ["tmdb_id", "reason"],
                },
            }
        },
        "required": ["results"],
    },
}


def _truncate_overview(overview: str | None) -> str:
    """Cut an overview to MAX_OVERVIEW_CHARS at a word boundary, marking the cut with an ellipsis."""
    text = (overview or "").strip()
    if len(text) <= MAX_OVERVIEW_CHARS:
        return text
    cut = text[:MAX_OVERVIEW_CHARS].rsplit(" ", 1)[0]
    return f"{cut.rstrip(',;:.')}…"


def _format_candidates(candidates: list[dict]) -> str:
    return "\n".join(
        f"- tmdb_id: {c['tmdb_id']}, title: {c['title']}, overview: {_truncate_overview(c.get('overview'))}"
        for c in candidates
    )


def _build_prompt(query: str, candidates: list[dict]) -> str:
    candidate_lines = _format_candidates(candidates)
    return (
        f'User request: "{query}"\n\n'
        f"Candidate movies (from vector search):\n{candidate_lines}\n\n"
        f"Pick the best {TOP_N} matches for the user's request and give a "
        f"short reason for each (one sentence, at most {MAX_REASON_WORDS} words), "
        "grounded in the movie's overview. Judge "
        "fit by mood, theme, and content, not by whether the request's words "
        "literally appear in the title — a movie titled after the request "
        "isn't a good match unless its overview also fits."
    )


@DatadogObservability.trace_llm_rerank
async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    client = _get_client()
    prompt = _build_prompt(query, candidates)
    
    # Context for the LLMObs hallucination eval: the same truncated text the model saw
    context = _format_candidates(candidates)
    
    # Wrap LLM call with LLM Observability context
    with DatadogObservability.wrap_llm_call(
        model=RERANK_MODEL,
        model_provider="anthropic",
        operation_name="rerank",
    ) as obs:
        message = await client.messages.create(
            model=RERANK_MODEL,
            max_tokens=RERANK_MAX_TOKENS,
            tools=[RERANK_TOOL],
            tool_choice={"type": "tool", "name": "return_recommendations"},
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Build prompt annotation for hallucination evaluation
        # The hallucination eval expects distinct query and context variables
        prompt_annotation = None
        if PROMPT_AVAILABLE and Prompt is not None:
            prompt_annotation = Prompt(
                id="rerank_prompt",
                template=(
                    'User request: "{query}"\n\n'
                    "Candidate movies (from vector search):\n{context}\n\n"
                    f"Pick the best {TOP_N} matches for the user's request and "
                    f"give a short reason for each (one sentence, at most {MAX_REASON_WORDS} words), "
                    "grounded in the movie's overview."
                ),
                variables={"query": query, "context": context},
                rag_query_variables=["query"],
                rag_context_variables=["context"],
            )
        
        # Annotate with token usage, metadata, and prompt variables
        obs.annotate(
            input_messages=[{"role": "user", "content": prompt}],
            output_messages=[{"role": "assistant", "content": str(message.content)}],
            metadata={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
                "candidate_count": len(candidates),
            },
            prompt=prompt_annotation,
        )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    picks = tool_use.input.get("results", [])

    candidates_by_id = {c["tmdb_id"]: c for c in candidates}
    results = []
    for pick in picks:
        candidate = candidates_by_id.get(pick.get("tmdb_id"))
        if candidate is None:
            continue
        results.append({**candidate, "reason": pick["reason"]})
        if len(results) == TOP_N:
            break

    return results
