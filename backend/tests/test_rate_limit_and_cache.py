"""
Tests for rate limiting and cache hardening.

Tests cover:
- Rate limiting on /recommend endpoint
- Cache key normalization (punctuation, whitespace)
- Variable TTL for popular moods
- Cache hit/miss logging
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import time

# Set dummy env vars before importing app
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app import cache
from app.main import app


class TestCacheNormalization:
    """Test cache key normalization."""

    def setup_method(self):
        """Clear cache before each test."""
        cache._cache.clear()
        cache._cache_stats["hits"] = 0
        cache._cache_stats["misses"] = 0

    def test_normalize_query_basic(self):
        """normalize_query should strip and lowercase."""
        assert cache.normalize_query("  Test Query  ") == "test query"
        assert cache.normalize_query("UPPERCASE") == "uppercase"

    def test_normalize_query_punctuation(self):
        """normalize_query should remove/normalize punctuation."""
        assert cache.normalize_query("What's a good movie?") == "whats a good movie"
        assert cache.normalize_query("Sci-fi, please!") == "sci-fi please"
        assert cache.normalize_query("Action... drama???") == "action drama"

    def test_normalize_query_whitespace(self):
        """normalize_query should collapse multiple spaces."""
        assert cache.normalize_query("too   many    spaces") == "too many spaces"
        assert cache.normalize_query("test\t\ttabs") == "test tabs"

    def test_cache_collision_near_duplicates(self):
        """Near-duplicate queries should hit the same cache entry."""
        results = [{"tmdb_id": 1, "title": "Test Movie"}]
        
        cache.store("sci-fi action", results)
        
        # These should all hit the same cache entry
        assert cache.get("sci-fi action") == results
        assert cache.get("Sci-Fi Action") == results
        assert cache.get("  sci-fi action  ") == results
        assert cache.get("sci-fi, action!") == results
        
        # Verify it's all cache hits
        assert cache._cache_stats["hits"] == 4
        assert cache._cache_stats["misses"] == 0

    def test_cache_stats(self):
        """Cache should track hits and misses."""
        results = [{"tmdb_id": 1, "title": "Test"}]
        
        # Miss
        assert cache.get("query1") is None
        assert cache._cache_stats["misses"] == 1
        
        # Store and hit
        cache.store("query1", results)
        assert cache.get("query1") == results
        assert cache._cache_stats["hits"] == 1
        
        # Another miss
        assert cache.get("query2") is None
        assert cache._cache_stats["misses"] == 2
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["total_requests"] == 3
        assert stats["hit_rate_percent"] == 33.3


class TestPopularMoodTTL:
    """Test variable TTL for popular moods."""

    def setup_method(self):
        """Clear cache before each test."""
        cache._cache.clear()

    def test_is_popular_mood(self):
        """_is_popular_mood should detect popular keywords."""
        assert cache._is_popular_mood("romantic comedy")
        assert cache._is_popular_mood("Horror movie please")
        assert cache._is_popular_mood("something for Friday night")
        assert cache._is_popular_mood("A feel-good family movie")
        assert not cache._is_popular_mood("obscure indie film from 1973")

    def test_popular_mood_longer_ttl(self):
        """Popular mood queries should get longer TTL."""
        results = [{"tmdb_id": 1}]
        
        # Store popular mood
        cache.store("romantic comedy", results)
        popular_key = cache.normalize_query("romantic comedy")
        popular_ttl = cache._cache[popular_key][0] - time.monotonic()
        
        # Store non-popular mood
        cache.store("obscure indie experimental", results)
        regular_key = cache.normalize_query("obscure indie experimental")
        regular_ttl = cache._cache[regular_key][0] - time.monotonic()
        
        # Popular should have longer TTL
        assert popular_ttl > regular_ttl
        assert popular_ttl > cache.CACHE_TTL_SECONDS
        assert abs(popular_ttl - cache.POPULAR_CACHE_TTL_SECONDS) < 1  # within 1 second


class TestRateLimiting:
    """Test rate limiting on /recommend endpoint."""

    def setup_method(self):
        """Reset rate limiter before each test."""
        from app.routers.recommend import limiter
        limiter._storage.storage.clear()

    def test_rate_limit_exceeded(self):
        """Bursting /recommend should return 429."""
        client = TestClient(app)
        
        # Mock the recommend logic to avoid actual API calls
        with patch('app.routers.recommend.embed_text', new_callable=AsyncMock) as mock_embed:
            with patch('app.routers.recommend.search_similar', new_callable=AsyncMock) as mock_search:
                with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                    mock_embed.return_value = [0.1] * 1536
                    mock_search.return_value = []
                    mock_rerank.return_value = [
                        {
                            "tmdb_id": 1,
                            "title": "Test Movie",
                            "poster_path": "/test.jpg",
                            "year": 2024,
                            "vote_average": 7.5,
                            "genres": ["Drama"],
                            "reason": "A great movie for your mood"
                        }
                    ]
                    
                    # Make requests up to the limit (10/minute)
                    for i in range(10):
                        response = client.post(
                            "/recommend",
                            json={"query": f"test query {i}"}  # Different queries to avoid cache
                        )
                        assert response.status_code == 200, f"Request {i+1} should succeed"
                    
                    # 11th request should be rate limited
                    response = client.post(
                        "/recommend",
                        json={"query": "test query 11"}
                    )
                    assert response.status_code == 429
                    
                    # Check friendly error message
                    data = response.json()
                    assert "error" in data
                    assert "rate limit" in data["error"].lower()
                    assert "message" in data
                    assert "try again" in data["message"].lower()
                    
                    # Check Retry-After header
                    assert "retry-after" in response.headers
                    assert response.headers["retry-after"] == "60"

    def test_rate_limit_friendly_message(self):
        """Rate limit response should have friendly JSON body."""
        client = TestClient(app)
        
        # Mock to avoid API calls
        with patch('app.routers.recommend.embed_text', new_callable=AsyncMock) as mock_embed:
            with patch('app.routers.recommend.search_similar', new_callable=AsyncMock) as mock_search:
                with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                    mock_embed.return_value = [0.1] * 1536
                    mock_search.return_value = []
                    mock_rerank.return_value = [{
                        "tmdb_id": 1,
                        "title": "Test",
                        "poster_path": "/test.jpg",
                        "year": 2024,
                        "vote_average": 7.5,
                        "genres": ["Drama"],
                        "reason": "Good movie"
                    }]
                    
                    # Exhaust rate limit
                    for i in range(10):
                        client.post("/recommend", json={"query": f"query {i}"})
                    
                    # Get 429 response
                    response = client.post("/recommend", json={"query": "one more"})
                    
                    assert response.status_code == 429
                    data = response.json()
                    
                    # Verify message structure
                    assert "error" in data
                    assert "message" in data
                    assert isinstance(data["message"], str)
                    assert len(data["message"]) > 0


class TestCacheWithRateLimit:
    """Test cache hits bypass rate limit cost."""

    def setup_method(self):
        """Clear cache and reset rate limiter before each test."""
        cache._cache.clear()
        # Reset rate limiter storage
        from app.routers.recommend import limiter
        limiter._storage.storage.clear()

    def test_cache_hit_still_counts_toward_rate_limit(self):
        """Cache hits still count toward rate limit (they're still requests)."""
        client = TestClient(app)
        
        with patch('app.routers.recommend.embed_text', new_callable=AsyncMock) as mock_embed:
            with patch('app.routers.recommend.search_similar', new_callable=AsyncMock) as mock_search:
                with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                    mock_embed.return_value = [0.1] * 1536
                    mock_search.return_value = []
                    mock_rerank.return_value = [{
                        "tmdb_id": 1,
                        "title": "Test",
                        "poster_path": "/test.jpg",
                        "year": 2024,
                        "vote_average": 7.5,
                        "genres": ["Drama"],
                        "reason": "Good movie"
                    }]
                    
                    # Make one request to populate cache
                    response = client.post("/recommend", json={"query": "test"})
                    assert response.status_code == 200
                    
                    # Verify LLM was called once
                    assert mock_rerank.call_count == 1
                    
                    # Make 9 more identical requests (should hit cache)
                    for i in range(9):
                        response = client.post("/recommend", json={"query": "test"})
                        assert response.status_code == 200
                    
                    # Verify LLM was NOT called again (cache working)
                    assert mock_rerank.call_count == 1
                    
                    # 11th request should be rate limited, even though it's a cache hit
                    response = client.post("/recommend", json={"query": "test"})
                    assert response.status_code == 429
