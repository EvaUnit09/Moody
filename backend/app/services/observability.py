"""
Datadog observability instrumentation for MovieRec.

Provides custom spans for embedding, vector search, and LLM reranking calls,
plus LLM Observability integration for tracking token usage and costs.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from app.config import settings

T = TypeVar("T")

# Optional ddtrace imports - gracefully handle missing dependency
try:
    from ddtrace import tracer
    from ddtrace.llmobs import LLMObs
    DDTRACE_AVAILABLE = True
except ImportError:
    tracer = None
    LLMObs = None
    DDTRACE_AVAILABLE = False


class DatadogObservability:
    """Datadog instrumentation utilities with static methods for tracing and LLM observability."""

    _initialized = False

    @staticmethod
    def initialize() -> None:
        """Initialize Datadog LLM Observability and configure trace filtering."""
        if DatadogObservability._initialized:
            return

        if not settings.dd_trace_enabled:
            print("[Datadog] DD_TRACE_ENABLED=false, observability disabled")
            return

        if not DDTRACE_AVAILABLE:
            print("[Datadog] ddtrace not installed, observability disabled")
            return

        # Configure tracer to use agentless mode or custom agent URL
        try:
            # Configure trace filtering to only trace /recommend endpoint
            from ddtrace.trace import TraceFilter

            class RecommendOnlyFilter(TraceFilter):
                """Filter to only keep traces for /recommend endpoint."""

                def process_trace(self, trace):
                    if not trace:
                        return trace

                    # Check the root span for the HTTP path
                    root_span = trace[0] if trace else None
                    if root_span:
                        http_url = root_span.get_tag("http.url") or ""
                        http_route = root_span.get_tag("http.route") or ""

                        # Keep traces for /recommend, drop everything else
                        if "/recommend" in http_url or "/recommend" in http_route:
                            return trace

                    # Drop this trace (not /recommend)
                    return None

            trace_processors = [RecommendOnlyFilter()]

            # If using agentless mode (DD_API_KEY set), disable APM tracing
            # entirely so ddtrace never tries to flush spans to a local agent.
            # LLM Observability is reported separately via LLMObs.enable() below.
            if settings.dd_api_key:
                tracer.configure(apm_tracing_disabled=True, trace_processors=trace_processors)
                print("[Datadog] Using agentless mode (LLM Observability only)")
            elif settings.dd_trace_agent_url:
                # ddtrace reads the agent URL from the DD_TRACE_AGENT_URL env var
                # at tracer init time; configure() no longer accepts an agent_url kwarg.
                tracer.configure(trace_processors=trace_processors)
                print(f"[Datadog] Using custom agent URL: {settings.dd_trace_agent_url}")
            else:
                # No API key and no agent URL = disable to prevent connection attempts
                print("[Datadog] No DD_API_KEY or DD_TRACE_AGENT_URL, disabling to prevent agent connection")
                return

            print("[Datadog] Trace filtering enabled (only /recommend endpoint)")
        except Exception as e:
            print(f"[Datadog] Failed to configure tracer: {e}")
            return

        # Enable LLM Observability if API key is provided
        if settings.dd_api_key:
            try:
                ml_app = settings.dd_llmobs_ml_app or settings.dd_service
                LLMObs.enable(
                    ml_app=ml_app,
                    integrations_enabled=True,
                    agentless_enabled=True,
                    api_key=settings.dd_api_key,
                    site=settings.dd_site,
                )
                DatadogObservability._initialized = True
                print(f"[Datadog] LLM Observability enabled for {ml_app}")
            except Exception as e:
                print(f"[Datadog] Failed to enable LLM Observability: {e}")
        else:
            print("[Datadog] DD_API_KEY not set, LLM Observability disabled")

    @staticmethod
    def trace_embedding(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to trace embedding calls with custom span."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.dd_trace_enabled or not DDTRACE_AVAILABLE:
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
            if not settings.dd_trace_enabled or not DDTRACE_AVAILABLE:
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
            if not settings.dd_trace_enabled or not DDTRACE_AVAILABLE:
                return await func(*args, **kwargs)

            # Extract query and candidates for metadata
            query = args[0] if args else kwargs.get("query", "")
            candidates = args[1] if len(args) > 1 else kwargs.get("candidates", [])

            with tracer.trace(
                "llm.rerank",
                service=settings.dd_service,
                resource="anthropic.claude-haiku-4-5",
            ) as span:
                span.set_tag("llm.provider", "anthropic")
                span.set_tag("llm.model", "claude-haiku-4-5")
                span.set_tag("llm.operation", "rerank")
                
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
    def trace_query_expansion(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to trace query expansion (pre-embedding query rewrite) calls."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not settings.dd_trace_enabled or not DDTRACE_AVAILABLE:
                return await func(*args, **kwargs)

            query = args[0] if args else kwargs.get("query", "")

            with tracer.trace(
                "llm.query_expansion",
                service=settings.dd_service,
                resource="anthropic.claude-haiku-4-5",
            ) as span:
                span.set_tag("llm.provider", "anthropic")
                span.set_tag("llm.model", "claude-haiku-4-5")
                span.set_tag("llm.operation", "query_expansion")

                if isinstance(query, str):
                    span.set_tag("llm.query_length", len(query))

                result = await func(*args, **kwargs)

                if isinstance(result, str):
                    span.set_tag("llm.expanded_query_length", len(result))

                return result
        return wrapper

    @staticmethod
    def wrap_llm_call(
        model: str,
        model_provider: str,
        operation_name: str = "llm",
    ):
        """
        Context manager to wrap an LLM call with LLM Observability.
        
        Usage:
            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic") as obs:
                response = await client.messages.create(...)
                obs.annotate(
                    input_messages=[...],
                    output_messages=[...],
                    metadata={"input_tokens": ..., "output_tokens": ...}
                )
        """
        class LLMObsContext:
            def __init__(self, enabled: bool):
                self.enabled = enabled
                self.llm_obs_span = None
            
            def __enter__(self):
                if not self.enabled or not DDTRACE_AVAILABLE or not DatadogObservability._initialized:
                    return self
                
                try:
                    # Create LLMObs span context
                    self.llm_obs_span = LLMObs.llm(
                        model_name=model,
                        model_provider=model_provider,
                        name=operation_name,
                        ml_app=settings.dd_llmobs_ml_app or settings.dd_service,
                    )
                    self.llm_obs_span.__enter__()
                except Exception as e:
                    print(f"[Datadog] Failed to create LLMObs span: {e}")
                    self.llm_obs_span = None
                
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.llm_obs_span is not None:
                    try:
                        self.llm_obs_span.__exit__(exc_type, exc_val, exc_tb)
                    except Exception as e:
                        print(f"[Datadog] Failed to close LLMObs span: {e}")
                return False
            
            def annotate(
                self,
                input_messages: list[dict[str, str]] | None = None,
                output_messages: list[dict[str, str]] | None = None,
                metadata: dict[str, Any] | None = None,
                prompt: Any | None = None,
            ) -> None:
                """Annotate the current LLM span with input/output/metadata/prompt."""
                if not self.enabled or self.llm_obs_span is None:
                    return
                
                try:
                    if input_messages:
                        LLMObs.annotate(
                            input_data=input_messages,
                            span=self.llm_obs_span,
                        )
                    if output_messages:
                        LLMObs.annotate(
                            output_data=output_messages,
                            span=self.llm_obs_span,
                        )
                    if metadata:
                        LLMObs.annotate(
                            metadata=metadata,
                            span=self.llm_obs_span,
                        )
                    if prompt:
                        LLMObs.annotate(
                            prompt=prompt,
                            span=self.llm_obs_span,
                        )
                except Exception as e:
                    print(f"[Datadog] Failed to annotate LLMObs span: {e}")
        
        enabled = settings.dd_trace_enabled and DatadogObservability._initialized and DDTRACE_AVAILABLE
        return LLMObsContext(enabled)
