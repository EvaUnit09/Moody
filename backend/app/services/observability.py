"""
Datadog observability instrumentation for MovieRec.

Provides custom spans for embedding, vector search, and LLM reranking calls,
plus LLM Observability integration for tracking token usage and costs.
"""

from typing import Any, Callable, TypeVar
from functools import wraps

from ddtrace import tracer
from ddtrace.llmobs import LLMObs

from app.config import settings

T = TypeVar("T")


class DatadogObservability:
    """Datadog instrumentation utilities with static methods for tracing and LLM observability."""

    _initialized = False

    @staticmethod
    def initialize() -> None:
        """Initialize Datadog LLM Observability. Call once at startup."""
        if DatadogObservability._initialized or not settings.dd_trace_enabled:
            return

        if settings.dd_api_key:
            try:
                LLMObs.enable(
                    ml_app=settings.dd_service,
                    integrations_enabled=True,
                    agentless_enabled=True,
                    api_key=settings.dd_api_key,
                    site="datadoghq.com",
                )
                DatadogObservability._initialized = True
                print(f"[Datadog] LLM Observability enabled for {settings.dd_service}")
            except Exception as e:
                print(f"[Datadog] Failed to enable LLM Observability: {e}")
        else:
            print("[Datadog] DD_API_KEY not set, LLM Observability disabled")

    @staticmethod
    def trace_embedding(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to trace embedding calls with custom span."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.dd_trace_enabled:
                return await func(*args, **kwargs)

            with tracer.trace(
                "embedding.generate",
                service=settings.dd_service,
                resource="openai.text-embedding-3-small",
            ) as span:
                span.set_tag("embedding.model", "text-embedding-3-small")
                span.set_tag("embedding.provider", "openai")
                
                # Extract input text for metadata
                text = args[0] if args else kwargs.get("text", "")
                if isinstance(text, str):
                    span.set_tag("embedding.input_length", len(text))
                
                result = await func(*args, **kwargs)
                
                if isinstance(result, list) and len(result) > 0:
                    span.set_tag("embedding.dimension", len(result))
                
                return result
        return wrapper

    @staticmethod
    def trace_vector_search(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to trace vector similarity search with custom span."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.dd_trace_enabled:
                return await func(*args, **kwargs)

            with tracer.trace(
                "vector_search.similarity",
                service=settings.dd_service,
                resource="supabase.pgvector",
            ) as span:
                span.set_tag("vector_search.provider", "supabase")
                span.set_tag("vector_search.index_type", "hnsw")
                span.set_tag("vector_search.similarity_metric", "cosine")
                
                # Extract limit parameter
                limit = kwargs.get("limit", args[1] if len(args) > 1 else None)
                if limit:
                    span.set_tag("vector_search.limit", limit)
                
                result = await func(*args, **kwargs)
                
                if isinstance(result, list):
                    span.set_tag("vector_search.results_count", len(result))
                
                return result
        return wrapper

    @staticmethod
    def trace_llm_rerank(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to trace LLM reranking with LLM Observability."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.dd_trace_enabled:
                return await func(*args, **kwargs)

            with tracer.trace(
                "llm.rerank",
                service=settings.dd_service,
                resource="anthropic.claude-haiku-4-5",
            ) as span:
                span.set_tag("llm.provider", "anthropic")
                span.set_tag("llm.model", "claude-haiku-4-5")
                span.set_tag("llm.operation", "rerank")
                
                # Extract query and candidates for metadata
                query = args[0] if args else kwargs.get("query", "")
                candidates = args[1] if len(args) > 1 else kwargs.get("candidates", [])
                
                if isinstance(query, str):
                    span.set_tag("llm.query_length", len(query))
                if isinstance(candidates, list):
                    span.set_tag("llm.candidate_count", len(candidates))
                
                result = await func(*args, **kwargs)
                
                if isinstance(result, list):
                    span.set_tag("llm.output_count", len(result))
                
                return result
        return wrapper

    @staticmethod
    def annotate_llm_call(
        model: str,
        input_messages: list[dict[str, str]],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Annotate an LLM call with LLM Observability.
        
        This captures token usage, cost estimates, and other LLM-specific metrics
        that are tracked in Datadog's LLM Observability dashboard.
        """
        if not settings.dd_trace_enabled or not DatadogObservability._initialized:
            return

        try:
            # Extract token usage from response
            usage = output_data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            # Build metadata
            llm_metadata = {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                **(metadata or {}),
            }

            # Log the LLM observation
            LLMObs.annotate(
                input_data=input_messages,
                output_data=output_data.get("content", []),
                metadata=llm_metadata,
                tags={
                    "ml_app": settings.dd_service,
                    "env": settings.dd_env,
                },
            )
        except Exception as e:
            print(f"[Datadog] Failed to annotate LLM call: {e}")
