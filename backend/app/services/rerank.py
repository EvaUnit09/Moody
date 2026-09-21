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

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

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
                        "reason": {"type": "string"},
                    },
                    "required": ["tmdb_id", "reason"],
                },
            }
        },
        "required": ["results"],
    },
}


def _build_prompt(query: str, candidates: list[dict]) -> str:
    candidate_lines = "\n".join(
        f"- tmdb_id: {c['tmdb_id']}, title: {c['title']}, overview: {c['overview']}"
        for c in candidates
    )
    return (
        f'User request: "{query}"\n\n'
        f"Candidate movies (from vector search):\n{candidate_lines}\n\n"
        f"Pick the best {TOP_N} matches for the user's request and give a "
        "one-line reason for each, grounded in the movie's overview. Judge "
        "fit by mood, theme, and content, not by whether the request's words "
        "literally appear in the title — a movie titled after the request "
        "isn't a good match unless its overview also fits."
    )


@DatadogObservability.trace_llm_rerank
async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    prompt = _build_prompt(query, candidates)
    
    # Build context string for LLMObs hallucination eval
    # Format: each candidate on its own line with tmdb_id, title, and overview
    context = "\n".join(
        f"- tmdb_id: {c['tmdb_id']}, title: {c['title']}, overview: {c['overview']}"
        for c in candidates
    )
    
    # Wrap LLM call with LLM Observability context
    with DatadogObservability.wrap_llm_call(
        model=RERANK_MODEL,
        model_provider="anthropic",
        operation_name="rerank",
    ) as obs:
        message = await client.messages.create(
            model=RERANK_MODEL,
            max_tokens=1024,
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
                template=f'User request: "{{query}}"\n\nCandidate movies (from vector search):\n{{context}}\n\nPick the best {TOP_N} matches for the user\'s request and give a one-line reason for each, grounded in the movie\'s overview.',
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
