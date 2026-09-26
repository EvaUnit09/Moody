from anthropic import AsyncAnthropic

from app.config import settings
from app.services.observability import DatadogObservability

EXPANSION_MODEL = "claude-haiku-4-5"

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    """Lazy initialization of Anthropic client (only fails if query expansion is actually used)."""
    global _client
    if _client is None:
        if settings.anthropic_api_key is None:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for query expansion. "
                "Set it in .env or environment variables."
            )
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=20.0)
    return _client

EXPAND_QUERY_TOOL = {
    "name": "expand_search_query",
    "description": (
        "Rewrite a movie search query into a description of the mood, theme, "
        "setting, or occasion it implies, suitable for semantic vector search "
        "over movie descriptions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "expanded_query": {
                "type": "string",
                "description": (
                    "A short phrase (1-2 sentences) describing what kind of "
                    "movies the user is likely looking for. If the original "
                    "query is already a clear, descriptive mood/genre/plot "
                    "request, return it unchanged."
                ),
            },
        },
        "required": ["expanded_query"],
    },
}


def _build_prompt(query: str) -> str:
    return (
        f'A user of a "movie recommendations by mood" app typed: "{query}"\n\n'
        "This text will be embedded and matched against movie descriptions via "
        "semantic vector search. Short, ambiguous, or single-word queries tend "
        "to match movies whose titles literally contain that word, which is "
        'almost never what the user means (e.g. "Fall" should mean "movies '
        'good to watch in autumn", not the movie titled Fall).\n\n'
        "Rewrite the query into a short, concrete description (1-2 sentences) "
        "of the mood, theme, setting, season, or occasion it most plausibly "
        "implies. If the query is already a clear, descriptive request, "
        "return it unchanged. Do not invent specific plot details or movie "
        "titles."
    )


@DatadogObservability.trace_query_expansion
async def expand_query(query: str) -> str:
    """Rewrite short/ambiguous queries into intent-rich phrasing before embedding."""
    client = _get_client()
    prompt = _build_prompt(query)

    with DatadogObservability.wrap_llm_call(
        model=EXPANSION_MODEL,
        model_provider="anthropic",
        operation_name="query_expansion",
    ) as obs:
        message = await client.messages.create(
            model=EXPANSION_MODEL,
            max_tokens=256,
            tools=[EXPAND_QUERY_TOOL],
            tool_choice={"type": "tool", "name": "expand_search_query"},
            messages=[{"role": "user", "content": prompt}],
        )

        obs.annotate(
            input_messages=[{"role": "user", "content": prompt}],
            output_messages=[{"role": "assistant", "content": str(message.content)}],
            metadata={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            },
        )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    expanded = tool_use.input.get("expanded_query", "").strip()
    return expanded or query
