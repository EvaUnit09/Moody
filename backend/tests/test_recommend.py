"""
Unit tests for recommend endpoint watch provider enrichment and exclude filtering.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.routers.recommend import _enrich_with_providers
from app.services.tmdb import WatchProviderService
from app import cache


class TestRecommendEnrichment:
    """Test suite for recommend endpoint provider enrichment."""
    
    @pytest.mark.asyncio
    async def test_enrich_with_providers_success(self):
        """Test successful batch enrichment with providers."""
        results = [
            {"tmdb_id": 550, "title": "Fight Club", "reason": "Great movie"},
            {"tmdb_id": 680, "title": "Pulp Fiction", "reason": "Classic"},
        ]
        
        async def mock_fetch(tmdb_id: int, region: str):
            if tmdb_id == 550:
                return [
                    {"name": "Netflix", "logo_url": "https://image.tmdb.org/logo.jpg", "link": "https://www.themoviedb.org/movie/550/watch"}
                ]
            return []
        
        with patch.object(WatchProviderService, 'fetch_providers', side_effect=mock_fetch):
            import asyncio
            semaphore = asyncio.Semaphore(10)
            enriched = await _enrich_with_providers(results, "US", semaphore)
            
            assert len(enriched) == 2
            assert len(enriched[0]["providers"]) == 1
            assert enriched[0]["providers"][0].name == "Netflix"
            assert len(enriched[1]["providers"]) == 0
    
    @pytest.mark.asyncio
    async def test_enrich_with_providers_empty_list(self):
        """Test enrichment with empty results list."""
        import asyncio
        semaphore = asyncio.Semaphore(10)
        enriched = await _enrich_with_providers([], "US", semaphore)
        
        assert enriched == []
    
    @pytest.mark.asyncio
    async def test_enrich_with_providers_concurrency_control(self):
        """Test enrichment respects semaphore concurrency limit."""
        results = [{"tmdb_id": i, "title": f"Movie {i}", "reason": "test"} for i in range(20)]
        
        call_count = 0
        max_concurrent = 0
        current_concurrent = 0
        
        async def mock_fetch(tmdb_id: int, region: str):
            nonlocal call_count, max_concurrent, current_concurrent
            call_count += 1
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)  # Simulate async work
            current_concurrent -= 1
            return []
        
        import asyncio
        with patch.object(WatchProviderService, 'fetch_providers', side_effect=mock_fetch):
            semaphore = asyncio.Semaphore(5)
            enriched = await _enrich_with_providers(results, "US", semaphore)
            
            assert len(enriched) == 20
            assert call_count == 20
            assert max_concurrent <= 5  # Semaphore limited concurrency
    
    @pytest.mark.asyncio
    async def test_enrich_with_providers_preserves_data(self):
        """Test enrichment preserves all existing movie data."""
        results = [
            {
                "tmdb_id": 550,
                "title": "Fight Club",
                "reason": "Great movie",
                "year": 1999,
                "genres": ["Drama", "Thriller"],
                "vote_average": 8.4,
            }
        ]
        
        with patch.object(WatchProviderService, 'fetch_providers', return_value=[]):
            import asyncio
            semaphore = asyncio.Semaphore(10)
            enriched = await _enrich_with_providers(results, "US", semaphore)
            
            assert enriched[0]["tmdb_id"] == 550
            assert enriched[0]["title"] == "Fight Club"
            assert enriched[0]["reason"] == "Great movie"
            assert enriched[0]["year"] == 1999
            assert enriched[0]["genres"] == ["Drama", "Thriller"]
            assert enriched[0]["vote_average"] == 8.4
            assert "providers" in enriched[0]


class TestExcludeFiltering:
    """Test suite for exclude_tmdb_ids filtering."""
    
    def test_exclude_list_oversize_rejected(self):
        """Test that exclude list longer than 100 is rejected with 422."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Create a list with 101 items (over the limit of 100)
        oversized_list = list(range(101))
        
        response = client.post(
            "/recommend",
            json={
                "query": "action movies",
                "region": "US",
                "exclude_tmdb_ids": oversized_list
            }
        )
        
        # Should reject with 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Verify error mentions the field and constraint
        error_msg = str(data["detail"]).lower()
        assert "exclude_tmdb_ids" in error_msg or "list" in error_msg
    
    @pytest.mark.asyncio
    async def test_exclude_filters_candidates(self):
        """Test that excluded tmdb_ids are filtered from candidates before rerank."""
        from app.routers.recommend import recommend
        from fastapi import Request
        from unittest.mock import Mock
        
        # Mock request object
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        # Create request body with excludes
        from app.models import RecommendRequest
        body = RecommendRequest(
            query="action movies",
            region="US",
            exclude_tmdb_ids=[550, 680]  # Exclude Fight Club and Pulp Fiction
        )
        
        # Mock the pipeline
        candidates = [
            {"tmdb_id": 550, "title": "Fight Club", "overview": "An insomniac...", "genres": ["Drama"], "poster_path": "/test.jpg", "year": 1999, "vote_average": 8.4},
            {"tmdb_id": 680, "title": "Pulp Fiction", "overview": "A burger-loving...", "genres": ["Crime"], "poster_path": "/test2.jpg", "year": 1994, "vote_average": 8.5},
            {"tmdb_id": 13, "title": "Forrest Gump", "overview": "Life is like...", "genres": ["Drama"], "poster_path": "/test3.jpg", "year": 1994, "vote_average": 8.3},
        ]
        
        with patch('app.routers.recommend.expand_query', new_callable=AsyncMock, return_value="action movies"):
            with patch('app.routers.recommend.embed_text', new_callable=AsyncMock, return_value=[0.1] * 1536):
                with patch('app.routers.recommend.search_similar', new_callable=AsyncMock, return_value=candidates):
                    with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                        with patch('app.routers.recommend._enrich_with_providers', new_callable=AsyncMock) as mock_enrich:
                            # Set up rerank to return what it receives (minus the excluded ones)
                            mock_rerank.return_value = [
                                {**c, "reason": "Great movie"} for c in candidates if c["tmdb_id"] not in [550, 680]
                            ]
                            mock_enrich.return_value = mock_rerank.return_value
                            
                            response = await recommend(body, request)
                            
                            # Verify rerank received filtered candidates (excluded IDs removed)
                            rerank_call_args = mock_rerank.call_args
                            rerank_candidates = rerank_call_args[0][1]
                            
                            # Should only have Forrest Gump, not Fight Club or Pulp Fiction
                            assert len(rerank_candidates) == 1
                            assert rerank_candidates[0]["tmdb_id"] == 13
                            assert 550 not in [c["tmdb_id"] for c in rerank_candidates]
                            assert 680 not in [c["tmdb_id"] for c in rerank_candidates]
                            
                            # Verify response doesn't contain excluded IDs
                            result_ids = [r.tmdb_id for r in response.results]
                            assert 550 not in result_ids
                            assert 680 not in result_ids
    
    @pytest.mark.asyncio
    async def test_exclude_empty_list_unchanged_behavior(self):
        """Test that empty exclude list behaves like current behavior."""
        from app.routers.recommend import recommend
        from fastapi import Request
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        from app.models import RecommendRequest
        body = RecommendRequest(query="comedy", region="US", exclude_tmdb_ids=[])
        
        candidates = [
            {"tmdb_id": 550, "title": "Fight Club", "overview": "An insomniac...", "genres": ["Drama"], "poster_path": "/test.jpg", "year": 1999, "vote_average": 8.4},
        ]
        
        with patch('app.routers.recommend.expand_query', new_callable=AsyncMock, return_value="comedy"):
            with patch('app.routers.recommend.embed_text', new_callable=AsyncMock, return_value=[0.1] * 1536):
                with patch('app.routers.recommend.search_similar', new_callable=AsyncMock, return_value=candidates):
                    with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                        with patch('app.routers.recommend._enrich_with_providers', new_callable=AsyncMock) as mock_enrich:
                            mock_rerank.return_value = [{**candidates[0], "reason": "Great"}]
                            mock_enrich.return_value = mock_rerank.return_value
                            
                            response = await recommend(body, request)
                            
                            # Should pass all candidates to rerank (no filtering)
                            rerank_call_args = mock_rerank.call_args
                            rerank_candidates = rerank_call_args[0][1]
                            assert len(rerank_candidates) == 1
                            assert rerank_candidates[0]["tmdb_id"] == 550
    
    @pytest.mark.asyncio
    async def test_exclude_none_unchanged_behavior(self):
        """Test that None exclude list behaves like current behavior."""
        from app.routers.recommend import recommend
        from fastapi import Request
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        from app.models import RecommendRequest
        body = RecommendRequest(query="drama", region="US", exclude_tmdb_ids=None)
        
        candidates = [
            {"tmdb_id": 550, "title": "Fight Club", "overview": "An insomniac...", "genres": ["Drama"], "poster_path": "/test.jpg", "year": 1999, "vote_average": 8.4},
        ]
        
        with patch('app.routers.recommend.expand_query', new_callable=AsyncMock, return_value="drama"):
            with patch('app.routers.recommend.embed_text', new_callable=AsyncMock, return_value=[0.1] * 1536):
                with patch('app.routers.recommend.search_similar', new_callable=AsyncMock, return_value=candidates):
                    with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                        with patch('app.routers.recommend._enrich_with_providers', new_callable=AsyncMock) as mock_enrich:
                            mock_rerank.return_value = [{**candidates[0], "reason": "Great"}]
                            mock_enrich.return_value = mock_rerank.return_value
                            
                            response = await recommend(body, request)
                            
                            # Should pass all candidates to rerank (no filtering)
                            rerank_call_args = mock_rerank.call_args
                            rerank_candidates = rerank_call_args[0][1]
                            assert len(rerank_candidates) == 1


class TestExcludeCacheKey:
    """Test suite for cache key behavior with exclude_tmdb_ids."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache._cache.clear()
        cache._cache_stats["hits"] = 0
        cache._cache_stats["misses"] = 0
    
    def test_build_cache_key_with_excludes(self):
        """Test cache key includes sorted exclude list."""
        key1 = cache.build_cache_key("action movies", [550, 680, 13])
        key2 = cache.build_cache_key("action movies", [13, 680, 550])  # Different order
        
        # Should produce same key regardless of order
        assert key1 == key2
        assert "exclude" in key1
        assert "13" in key1
        assert "550" in key1
        assert "680" in key1
    
    def test_build_cache_key_deduplicates_excludes(self):
        """Test cache key deduplicates exclude list so [1,1,2] matches [1,2]."""
        key1 = cache.build_cache_key("action movies", [1, 2])
        key2 = cache.build_cache_key("action movies", [1, 1, 2])  # Duplicates
        key3 = cache.build_cache_key("action movies", [2, 1, 1])  # Duplicates, different order
        
        # All should produce same key
        assert key1 == key2
        assert key1 == key3
        assert key2 == key3
        
        # Verify it contains deduplicated IDs
        assert "1" in key1
        assert "2" in key1
        # Should not have duplicate representation in key string
        assert key1 == cache.normalize_query("action movies") + ":exclude:1,2"
    
    def test_build_cache_key_without_excludes(self):
        """Test cache key without excludes matches current behavior."""
        key1 = cache.build_cache_key("action movies", None)
        key2 = cache.build_cache_key("action movies", [])
        
        # Both should produce same normalized key without exclude suffix
        assert key1 == key2
        assert "exclude" not in key1
        assert key1 == cache.normalize_query("action movies")
    
    def test_cache_separate_entries_for_different_excludes(self):
        """Test that different exclude lists create separate cache entries."""
        results1 = [{"tmdb_id": 1, "title": "Movie 1"}]
        results2 = [{"tmdb_id": 2, "title": "Movie 2"}]
        
        # Store with different exclude lists
        key1 = cache.build_cache_key("action:US", [550])
        key2 = cache.build_cache_key("action:US", [680])
        key3 = cache.build_cache_key("action:US", None)
        
        cache.store(key1, results1)
        cache.store(key2, results2)
        cache.store(key3, results1)
        
        # Should retrieve different results
        assert cache.get(key1) == results1
        assert cache.get(key2) == results2
        assert cache.get(key3) == results1
        
        # Verify all are cache hits
        assert cache._cache_stats["hits"] == 3
        assert cache._cache_stats["misses"] == 0
    
    @pytest.mark.asyncio
    async def test_cache_hit_with_excludes(self):
        """Test that cache hit works correctly with excludes."""
        from app.routers.recommend import recommend
        from fastapi import Request
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        from app.models import RecommendRequest
        body = RecommendRequest(query="action", region="US", exclude_tmdb_ids=[550])
        
        candidates = [
            {"tmdb_id": 13, "title": "Forrest Gump", "overview": "Life is like...", "genres": ["Drama"], "poster_path": "/test.jpg", "year": 1994, "vote_average": 8.3},
        ]
        
        with patch('app.routers.recommend.expand_query', new_callable=AsyncMock, return_value="action"):
            with patch('app.routers.recommend.embed_text', new_callable=AsyncMock, return_value=[0.1] * 1536):
                with patch('app.routers.recommend.search_similar', new_callable=AsyncMock, return_value=candidates):
                    with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                        with patch('app.routers.recommend._enrich_with_providers', new_callable=AsyncMock) as mock_enrich:
                            mock_rerank.return_value = [{**candidates[0], "reason": "Great", "providers": []}]
                            mock_enrich.return_value = mock_rerank.return_value
                            
                            # First call - cache miss
                            response1 = await recommend(body, request)
                            assert mock_rerank.call_count == 1
                            
                            # Second call with same excludes - should hit cache
                            response2 = await recommend(body, request)
                            assert mock_rerank.call_count == 1  # Not called again
                            
                            # Results should be identical
                            assert response1.results == response2.results
    
    @pytest.mark.asyncio
    async def test_cache_miss_with_different_excludes(self):
        """Test that different excludes cause cache miss."""
        from app.routers.recommend import recommend
        from fastapi import Request
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        from app.models import RecommendRequest
        
        candidates = [
            {"tmdb_id": 13, "title": "Forrest Gump", "overview": "Life is like...", "genres": ["Drama"], "poster_path": "/test.jpg", "year": 1994, "vote_average": 8.3},
        ]
        
        with patch('app.routers.recommend.expand_query', new_callable=AsyncMock, return_value="action"):
            with patch('app.routers.recommend.embed_text', new_callable=AsyncMock, return_value=[0.1] * 1536):
                with patch('app.routers.recommend.search_similar', new_callable=AsyncMock, return_value=candidates):
                    with patch('app.routers.recommend.rerank', new_callable=AsyncMock) as mock_rerank:
                        with patch('app.routers.recommend._enrich_with_providers', new_callable=AsyncMock) as mock_enrich:
                            mock_rerank.return_value = [{**candidates[0], "reason": "Great", "providers": []}]
                            mock_enrich.return_value = mock_rerank.return_value
                            
                            # First call with exclude [550]
                            body1 = RecommendRequest(query="action", region="US", exclude_tmdb_ids=[550])
                            await recommend(body1, request)
                            assert mock_rerank.call_count == 1
                            
                            # Second call with different exclude [680] - should miss cache
                            body2 = RecommendRequest(query="action", region="US", exclude_tmdb_ids=[680])
                            await recommend(body2, request)
                            assert mock_rerank.call_count == 2  # Called again
