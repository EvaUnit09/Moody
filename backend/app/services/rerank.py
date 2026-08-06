from anthropic import AsyncAnthropic

from app.config import settings

RERANK_MODEL = "claude-haiku-4-5"
TOP_N = 5

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


async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    message = await client.messages.create(
        model=RERANK_MODEL,
        max_tokens=1024,
        tools=[RERANK_TOOL],
        tool_choice={"type": "tool", "name": "return_recommendations"},
        messages=[{"role": "user", "content": _build_prompt(query, candidates)}],
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
