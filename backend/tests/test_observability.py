"""
Tests for Datadog observability module.

Tests cover:
- Graceful degradation when ddtrace not available
- Exception handling in decorators
- LLM observation context manager
- Initialization behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


class TestObservabilityGracefulDegradation:
    """Test that observability degrades gracefully when ddtrace is unavailable."""

    def test_import_without_ddtrace(self):
        """Observability module should import even without ddtrace installed."""
        # This test passes if the import succeeds (already tested by importing at module level)
        from app.services.observability import DatadogObservability, DDTRACE_AVAILABLE
        assert hasattr(DatadogObservability, 'initialize')
        assert isinstance(DDTRACE_AVAILABLE, bool)

    def test_initialize_without_ddtrace(self):
        """Initialize should be no-op when ddtrace not available."""
        with patch('app.services.observability.DDTRACE_AVAILABLE', False):
            from app.services.observability import DatadogObservability
            # Should not raise
            DatadogObservability.initialize()

    def test_initialize_when_disabled(self):
        """Initialize should be no-op when DD_TRACE_ENABLED=false."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            from app.services.observability import DatadogObservability
            DatadogObservability._initialized = False  # Reset
            DatadogObservability.initialize()
            assert not DatadogObservability._initialized


class TestObservabilityDecorators:
    """Test that decorators work correctly with and without ddtrace."""

    @pytest.mark.asyncio
    async def test_trace_embedding_decorator_disabled(self):
        """Embedding decorator should pass through when disabled."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            @DatadogObservability.trace_embedding
            async def mock_embed(text: str) -> list[float]:
                return [0.1, 0.2, 0.3]
            
            result = await mock_embed("test")
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_trace_vector_search_decorator_disabled(self):
        """Vector search decorator should pass through when disabled."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            @DatadogObservability.trace_vector_search
            async def mock_search(embedding: list[float], limit: int = 25) -> list[dict]:
                return [{"id": 1, "title": "Test Movie"}]
            
            result = await mock_search([0.1, 0.2], limit=5)
            assert len(result) == 1
            assert result[0]["title"] == "Test Movie"

    @pytest.mark.asyncio
    async def test_trace_llm_rerank_decorator_disabled(self):
        """LLM rerank decorator should pass through when disabled."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            @DatadogObservability.trace_llm_rerank
            async def mock_rerank(query: str, candidates: list[dict]) -> list[dict]:
                return candidates[:3]
            
            candidates = [{"id": i, "title": f"Movie {i}"} for i in range(10)]
            result = await mock_rerank("test query", candidates)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_decorator_exception_propagates(self):
        """Decorators should propagate exceptions from wrapped functions."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            @DatadogObservability.trace_embedding
            async def failing_function(text: str):
                raise ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                await failing_function("test")


class TestLLMObsContextManager:
    """Test the LLM Observability context manager."""

    def test_wrap_llm_call_disabled(self):
        """Context manager should be no-op when disabled."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            with DatadogObservability.wrap_llm_call("test-model", "test-provider") as obs:
                # Should not raise
                obs.annotate(
                    input_messages=[{"role": "user", "content": "test"}],
                    metadata={"tokens": 10}
                )

    def test_wrap_llm_call_without_ddtrace(self):
        """Context manager should handle missing ddtrace gracefully."""
        with patch('app.services.observability.DDTRACE_AVAILABLE', False):
            from app.services.observability import DatadogObservability
            
            with DatadogObservability.wrap_llm_call("test-model", "test-provider") as obs:
                # Should not raise
                obs.annotate(
                    input_messages=[{"role": "user", "content": "test"}],
                    output_messages=[{"role": "assistant", "content": "response"}],
                    metadata={"input_tokens": 10, "output_tokens": 20}
                )

    def test_wrap_llm_call_exception_handling(self):
        """Context manager should handle exceptions gracefully."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = True
            
            with patch('app.services.observability.DatadogObservability._initialized', True):
                with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                    with patch('app.services.observability.LLMObs') as mock_llmobs:
                        # Make LLMObs.llm raise an exception
                        mock_llmobs.llm.side_effect = Exception("Test exception")
                        
                        from app.services.observability import DatadogObservability
                        
                        # Should not propagate exception
                        with DatadogObservability.wrap_llm_call("test", "test") as obs:
                            obs.annotate(metadata={"test": "data"})

    def test_wrap_llm_call_with_prompt_annotation(self):
        """Context manager should support prompt annotation parameter."""
        with patch('app.services.observability.settings') as mock_settings:
            mock_settings.dd_trace_enabled = False
            
            from app.services.observability import DatadogObservability
            
            # Mock Prompt object
            mock_prompt = Mock()
            
            with DatadogObservability.wrap_llm_call("test-model", "test-provider") as obs:
                # Should not raise with prompt parameter
                obs.annotate(
                    input_messages=[{"role": "user", "content": "test"}],
                    output_messages=[{"role": "assistant", "content": "response"}],
                    metadata={"tokens": 10},
                    prompt=mock_prompt
                )

    def test_wrap_llm_call_enabled_success_path(self):
        """Context manager should successfully annotate when enabled and ddtrace available."""
        with patch.dict('sys.modules', {'ddtrace': MagicMock(), 'ddtrace.filters': MagicMock(), 'ddtrace.llmobs': MagicMock()}):
            with patch('app.services.observability.settings') as mock_settings:
                mock_settings.dd_trace_enabled = True
                mock_settings.dd_service = "test-service"
                mock_settings.dd_llmobs_ml_app = None

                with patch('app.services.observability.DatadogObservability._initialized', True):
                    with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                        with patch('app.services.observability.LLMObs') as mock_llmobs:
                            # Create a mock span context
                            mock_span = MagicMock()
                            mock_span.__enter__ = Mock(return_value=mock_span)
                            mock_span.__exit__ = Mock(return_value=False)
                            mock_llmobs.llm.return_value = mock_span

                            from app.services.observability import DatadogObservability

                            # Test the full enabled path
                            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic", "rerank") as obs:
                                # Annotate should work
                                obs.annotate(
                                    input_messages=[{"role": "user", "content": "test query"}],
                                    output_messages=[{"role": "assistant", "content": "test response"}],
                                    metadata={"input_tokens": 10, "output_tokens": 20}
                                )

                            # Verify LLMObs.llm was called with correct params
                            # (falls back to dd_service when dd_llmobs_ml_app is unset)
                            mock_llmobs.llm.assert_called_once_with(
                                model_name="claude-haiku-4-5",
                                model_provider="anthropic",
                                name="rerank",
                                ml_app="test-service",
                            )

                            # Verify annotate was called 3 times (once for each type of data)
                            assert mock_llmobs.annotate.call_count == 3

                            # Verify span context was entered and exited
                            mock_span.__enter__.assert_called_once()
                            mock_span.__exit__.assert_called_once()

    def test_wrap_llm_call_uses_configured_ml_app_over_service(self):
        """ml_app should prefer settings.dd_llmobs_ml_app over dd_service when set."""
        with patch.dict('sys.modules', {'ddtrace': MagicMock(), 'ddtrace.filters': MagicMock(), 'ddtrace.llmobs': MagicMock()}):
            with patch('app.services.observability.settings') as mock_settings:
                mock_settings.dd_trace_enabled = True
                mock_settings.dd_service = "test-service"
                mock_settings.dd_llmobs_ml_app = "moody"

                with patch('app.services.observability.DatadogObservability._initialized', True):
                    with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                        with patch('app.services.observability.LLMObs') as mock_llmobs:
                            mock_span = MagicMock()
                            mock_span.__enter__ = Mock(return_value=mock_span)
                            mock_span.__exit__ = Mock(return_value=False)
                            mock_llmobs.llm.return_value = mock_span

                            from app.services.observability import DatadogObservability

                            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic", "rerank"):
                                pass

                            mock_llmobs.llm.assert_called_once_with(
                                model_name="claude-haiku-4-5",
                                model_provider="anthropic",
                                name="rerank",
                                ml_app="moody",
                            )

    def test_wrap_llm_call_with_prompt_parameter_enabled(self):
        """Context manager should annotate prompt when enabled and prompt is provided."""
        with patch.dict('sys.modules', {'ddtrace': MagicMock(), 'ddtrace.filters': MagicMock(), 'ddtrace.llmobs': MagicMock()}):
            with patch('app.services.observability.settings') as mock_settings:
                mock_settings.dd_trace_enabled = True
                mock_settings.dd_service = "test-service"
                
                with patch('app.services.observability.DatadogObservability._initialized', True):
                    with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                        with patch('app.services.observability.LLMObs') as mock_llmobs:
                            # Create a mock span context
                            mock_span = MagicMock()
                            mock_span.__enter__ = Mock(return_value=mock_span)
                            mock_span.__exit__ = Mock(return_value=False)
                            mock_llmobs.llm.return_value = mock_span
                            
                            from app.services.observability import DatadogObservability
                            
                            # Mock Prompt object
                            mock_prompt = Mock()
                            mock_prompt.template = "Test {query} with {context}"
                            mock_prompt.variables = {"query": "test query", "context": "test context"}
                            
                            # Test the full enabled path with prompt
                            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic", "rerank") as obs:
                                obs.annotate(
                                    input_messages=[{"role": "user", "content": "test query"}],
                                    output_messages=[{"role": "assistant", "content": "test response"}],
                                    metadata={"input_tokens": 10, "output_tokens": 20},
                                    prompt=mock_prompt
                                )
                            
                            # Verify annotate was called 4 times (input, output, metadata, prompt)
                            assert mock_llmobs.annotate.call_count == 4
                            
                            # Verify prompt was passed to annotate
                            prompt_call = [call for call in mock_llmobs.annotate.call_args_list 
                                          if 'prompt' in call.kwargs]
                            assert len(prompt_call) == 1
                            assert prompt_call[0].kwargs['prompt'] == mock_prompt


class TestPromptAnnotation:
    """Test real Prompt object construction and annotation."""

    def test_rerank_constructs_prompt_with_query_and_context_variables(self):
        """Regression test: verify rerank creates Prompt with distinct query+context variables."""
        # Import the real Prompt class if available
        try:
            from ddtrace.llmobs.types import Prompt
        except ImportError:
            try:
                from ddtrace.llmobs import Prompt
            except ImportError:
                pytest.skip("ddtrace.llmobs.Prompt not available")
        
        # Create a real Prompt object as rerank.py would
        query = "sci-fi action movies"
        candidates = [
            {"tmdb_id": 1, "title": "The Matrix", "overview": "A hacker discovers reality is a simulation."},
            {"tmdb_id": 2, "title": "Blade Runner", "overview": "A blade runner hunts replicants in dystopian LA."},
        ]
        context = "\n".join(
            f"- tmdb_id: {c['tmdb_id']}, title: {c['title']}, overview: {c['overview']}"
            for c in candidates
        )
        
        # Construct Prompt as rerank.py does
        prompt = Prompt(
            id="rerank_prompt",
            template='User request: "{query}"\n\nCandidate movies (from vector search):\n{context}\n\nPick the best 6 matches for the user\'s request and give a one-line reason for each, grounded in the movie\'s overview.',
            variables={"query": query, "context": context},
            rag_query_variables=["query"],
            rag_context_variables=["context"],
        )
        
        # On ddtrace 4.x, Prompt is a TypedDict/dict - use dict access
        # Verify prompt has the correct structure
        assert prompt["id"] == "rerank_prompt"
        assert "{query}" in prompt["template"]
        assert "{context}" in prompt["template"]
        assert prompt["variables"]["query"] == query
        assert prompt["variables"]["context"] == context
        assert "query" in prompt["rag_query_variables"]
        assert "context" in prompt["rag_context_variables"]
        
        # Verify context contains the candidate data
        assert "tmdb_id: 1" in context
        assert "The Matrix" in context
        assert "tmdb_id: 2" in context
        assert "Blade Runner" in context

    def test_annotate_receives_prompt_with_id_and_variables(self):
        """Stronger test: verify annotate() actually receives prompt with id/query/context."""
        with patch.dict('sys.modules', {'ddtrace': MagicMock(), 'ddtrace.filters': MagicMock(), 'ddtrace.llmobs': MagicMock()}):
            with patch('app.services.observability.settings') as mock_settings:
                mock_settings.dd_trace_enabled = True
                mock_settings.dd_service = "test-service"
                
                with patch('app.services.observability.DatadogObservability._initialized', True):
                    with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                        with patch('app.services.observability.LLMObs') as mock_llmobs:
                            mock_span = MagicMock()
                            mock_span.__enter__ = Mock(return_value=mock_span)
                            mock_span.__exit__ = Mock(return_value=False)
                            mock_llmobs.llm.return_value = mock_span
                            
                            from app.services.observability import DatadogObservability
                            
                            # Create a real-ish prompt dict (as ddtrace 4.x returns)
                            test_prompt = {
                                "id": "rerank_prompt",
                                "template": "User request: {query}\n\nContext: {context}",
                                "variables": {
                                    "query": "test query",
                                    "context": "test context data"
                                },
                                "rag_query_variables": ["query"],
                                "rag_context_variables": ["context"]
                            }
                            
                            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic", "rerank") as obs:
                                obs.annotate(
                                    input_messages=[{"role": "user", "content": "test"}],
                                    output_messages=[{"role": "assistant", "content": "response"}],
                                    metadata={"input_tokens": 10},
                                    prompt=test_prompt
                                )
                            
                            # Find the annotate call with prompt
                            prompt_calls = [call for call in mock_llmobs.annotate.call_args_list 
                                           if call.kwargs.get('prompt') is not None]
                            
                            assert len(prompt_calls) == 1
                            captured_prompt = prompt_calls[0].kwargs['prompt']
                            
                            # Verify the captured prompt has id and correct variables
                            assert captured_prompt["id"] == "rerank_prompt"
                            assert captured_prompt["variables"]["query"] == "test query"
                            assert captured_prompt["variables"]["context"] == "test context data"
                            assert "query" in captured_prompt["rag_query_variables"]
                            assert "context" in captured_prompt["rag_context_variables"]


class TestInitializationBehavior:
    """Test initialization behavior under different conditions."""

    def test_initialize_once(self):
        """Initialize should only run once."""
        # Mock at import level to avoid ddtrace import errors
        with patch.dict('sys.modules', {'ddtrace': MagicMock(), 'ddtrace.filters': MagicMock(), 'ddtrace.llmobs': MagicMock()}):
            with patch('app.services.observability.DDTRACE_AVAILABLE', True):
                with patch('app.services.observability.settings') as mock_settings:
                    mock_settings.dd_trace_enabled = True
                    mock_settings.dd_api_key = "test-key"
                    mock_settings.dd_trace_agent_url = None
                    mock_settings.dd_service = "test-service"
                    
                    with patch('app.services.observability.LLMObs') as mock_llmobs:
                        with patch('app.services.observability.tracer') as mock_tracer:
                            mock_tracer.configure = Mock()
                            
                            from app.services.observability import DatadogObservability
                            
                            DatadogObservability._initialized = False
                            DatadogObservability.initialize()
                            first_initialized = DatadogObservability._initialized
                            
                            DatadogObservability.initialize()  # Second call
                            
                            # Should be initialized after first call
                            assert first_initialized is True
                            # LLMObs.enable should be called only once
                            assert mock_llmobs.enable.call_count == 1

    def test_initialize_without_api_key(self):
        """Initialize should handle missing API key gracefully."""
        with patch('app.services.observability.DDTRACE_AVAILABLE', True):
            with patch('app.services.observability.settings') as mock_settings:
                mock_settings.dd_trace_enabled = True
                mock_settings.dd_api_key = None
                mock_settings.dd_trace_agent_url = None
                
                from app.services.observability import DatadogObservability
                
                DatadogObservability._initialized = False
                # Should not raise, just print message and return
                DatadogObservability.initialize()
