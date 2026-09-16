from anthropic import AsyncAnthropic

from app.config import settings
from app.services.observability import DatadogObservability

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
        "one-line reason for each, grounded in the movie's overview."
    )


@DatadogObservability.trace_llm_rerank
async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    prompt = _build_prompt(query, candidates)
    message = await client.messages.create(
        model=RERANK_MODEL,
        max_tokens=1024,
        tools=[RERANK_TOOL],
        tool_choice={"type": "tool", "name": "return_recommendations"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Annotate LLM call for Datadog LLM Observability
    DatadogObservability.annotate_llm_call(
        model=RERANK_MODEL,
        input_messages=[{"role": "user", "content": prompt}],
        output_data={
            "content": message.content,
            "usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        },
        metadata={
            "query": query,
            "candidate_count": len(candidates),
            "model": RERANK_MODEL,
        },
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
