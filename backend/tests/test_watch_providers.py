"""
Unit tests for WatchProviderService.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.tmdb import WatchProviderService


class TestWatchProviderService:
    """Test suite for WatchProviderService."""
    
    def test_validate_region_default(self):
        """Test region validation with None returns default US."""
        result = WatchProviderService._validate_region(None)
        assert result == "US"
    
    def test_validate_region_uppercase(self):
        """Test region validation uppercases input."""
        result = WatchProviderService._validate_region("gb")
        assert result == "GB"
    
    def test_validate_region_valid(self):
        """Test region validation accepts valid 2-letter codes."""
        assert WatchProviderService._validate_region("US") == "US"
        assert WatchProviderService._validate_region("GB") == "GB"
        assert WatchProviderService._validate_region("ca") == "CA"
    
    def test_validate_region_invalid_length(self):
        """Test region validation rejects invalid length."""
        with pytest.raises(ValueError, match="Invalid region code"):
            WatchProviderService._validate_region("USA")
        
        with pytest.raises(ValueError, match="Invalid region code"):
            WatchProviderService._validate_region("U")
    
    def test_validate_region_invalid_chars(self):
        """Test region validation rejects non-letter characters."""
        with pytest.raises(ValueError, match="Invalid region code"):
            WatchProviderService._validate_region("U1")
        
        with pytest.raises(ValueError, match="Invalid region code"):
            WatchProviderService._validate_region("US!")
    
    def test_is_link_allowed_tmdb(self):
        """Test link allowlist accepts TMDB links."""
        assert WatchProviderService._is_link_allowed("https://www.themoviedb.org/movie/550/watch")
        assert WatchProviderService._is_link_allowed("https://themoviedb.org/movie/550/watch")
    
    def test_is_link_allowed_justwatch(self):
        """Test link allowlist accepts JustWatch links."""
        assert WatchProviderService._is_link_allowed("https://www.justwatch.com/us/movie/fight-club")
        assert WatchProviderService._is_link_allowed("https://justwatch.com/us/movie/fight-club")
    
    def test_is_link_allowed_rejects_http(self):
        """Test link allowlist rejects non-HTTPS."""
        assert not WatchProviderService._is_link_allowed("http://www.themoviedb.org/movie/550/watch")
        assert not WatchProviderService._is_link_allowed("http://justwatch.com/movie/550")
    
    def test_is_link_allowed_rejects_other_hosts(self):
        """Test link allowlist rejects non-allowlisted hosts."""
        assert not WatchProviderService._is_link_allowed("https://evil.com/movie/550")
        assert not WatchProviderService._is_link_allowed("https://netflix.com/watch/123")
        assert not WatchProviderService._is_link_allowed("https://themoviedb.org.evil.com/movie/550")
    
    def test_build_cache_key(self):
        """Test cache key uses | delimiter to prevent collisions."""
        key1 = WatchProviderService._build_cache_key(123, "US")
        key2 = WatchProviderService._build_cache_key(12, "3US")
        
        assert key1 == "123|US"
        assert key2 == "12|3US"
        assert key1 != key2  # No ambiguous collision
    
    @pytest.mark.asyncio
    async def test_fetch_providers_success(self):
        """Test successful provider fetch and caching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "US": {
                    "link": "https://www.themoviedb.org/movie/550/watch",
                    "flatrate": [
                        {
                            "provider_name": "Netflix",
                            "logo_path": "/9A1JSVmSxsyaBK4SUFsYVqbAYfW.jpg"
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Clear cache before test
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            result = await WatchProviderService.fetch_providers(550, "US")
            
            assert len(result) == 1
            assert result[0]["name"] == "Netflix"
            assert result[0]["logo_url"] == "https://image.tmdb.org/t/p/original/9A1JSVmSxsyaBK4SUFsYVqbAYfW.jpg"
            assert result[0]["link"] == "https://www.themoviedb.org/movie/550/watch"
    
    @pytest.mark.asyncio
    async def test_fetch_providers_no_region_data(self):
        """Test provider fetch returns empty list when region has no data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {}
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            result = await WatchProviderService.fetch_providers(550, "XX")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_providers_rejects_bad_link(self):
        """Test provider fetch rejects non-allowlisted links."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "US": {
                    "link": "https://evil.com/movie/550",
                    "flatrate": [
                        {
                            "provider_name": "Netflix",
                            "logo_path": "/9A1JSVmSxsyaBK4SUFsYVqbAYfW.jpg"
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            result = await WatchProviderService.fetch_providers(550, "US")
            
            assert result == []  # Rejected due to bad link
    
    @pytest.mark.asyncio
    async def test_fetch_providers_network_error_not_cached(self):
        """Test network errors return empty list and are not cached."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            # First call - network error
            result1 = await WatchProviderService.fetch_providers(550, "US")
            assert result1 == []
            
            # Verify failure was not cached (cache should be empty for this key)
            cache_key = WatchProviderService._build_cache_key(550, "US")
            if hasattr(WatchProviderService, '_cache'):
                assert cache_key not in WatchProviderService._cache
    
    @pytest.mark.asyncio
    async def test_fetch_providers_max_limit(self):
        """Test provider fetch respects MAX_PROVIDERS limit."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "US": {
                    "link": "https://www.themoviedb.org/movie/550/watch",
                    "flatrate": [
                        {"provider_name": "Netflix", "logo_path": "/path1.jpg"},
                        {"provider_name": "Prime", "logo_path": "/path2.jpg"},
                        {"provider_name": "Hulu", "logo_path": "/path3.jpg"},
                        {"provider_name": "Disney+", "logo_path": "/path4.jpg"},
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            result = await WatchProviderService.fetch_providers(550, "US")
            
            assert len(result) == WatchProviderService.MAX_PROVIDERS
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_fetch_providers_fallback_to_buy(self):
        """Test provider fetch falls back to buy when flatrate unavailable."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "US": {
                    "link": "https://www.themoviedb.org/movie/550/watch",
                    "buy": [
                        {"provider_name": "iTunes", "logo_path": "/path1.jpg"}
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            if hasattr(WatchProviderService, '_cache'):
                WatchProviderService._cache.clear()
            
            result = await WatchProviderService.fetch_providers(550, "US")
            
            assert len(result) == 1
            assert result[0]["name"] == "iTunes"
