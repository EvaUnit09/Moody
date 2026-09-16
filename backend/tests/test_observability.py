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

    def test_wrap_llm_call_enabled_success_path(self):
        """Context manager should successfully annotate when enabled and ddtrace available."""
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
                            
                            # Test the full enabled path
                            with DatadogObservability.wrap_llm_call("claude-haiku-4-5", "anthropic", "rerank") as obs:
                                # Annotate should work
                                obs.annotate(
                                    input_messages=[{"role": "user", "content": "test query"}],
                                    output_messages=[{"role": "assistant", "content": "test response"}],
                                    metadata={"input_tokens": 10, "output_tokens": 20}
                                )
                            
                            # Verify LLMObs.llm was called with correct params
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
