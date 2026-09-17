"""
Unit tests for recommend endpoint watch provider enrichment.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.routers.recommend import _enrich_with_providers
from app.services.tmdb import WatchProviderService


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
