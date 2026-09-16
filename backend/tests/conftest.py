"""
Pytest configuration and fixtures for backend tests.
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up required environment variables for testing."""
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
    os.environ.setdefault("DD_TRACE_ENABLED", "false")
    os.environ.setdefault("DD_API_KEY", "")
    yield
