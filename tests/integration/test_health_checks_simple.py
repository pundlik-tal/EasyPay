"""
EasyPay Payment Gateway - Simple Health Check Tests
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.api.v1.endpoints.health import health_check, readiness_check, liveness_check, detailed_health_check


class TestHealthCheckEndpoints:
    """Test health check endpoints directly."""
    
    @pytest.mark.integration
    async def test_basic_health_check(self):
        """Test basic health check endpoint."""
        result = await health_check()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["service"] == "EasyPay Payment Gateway"
        assert result["version"] == "0.1.0"
    
    @pytest.mark.integration
    async def test_liveness_check(self):
        """Test liveness check endpoint."""
        result = await liveness_check()
        
        assert result["status"] == "alive"
        assert "timestamp" in result
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_readiness_check_success(
        self, 
        mock_get_cache_client, 
        mock_get_db_session
    ):
        """Test readiness check when all dependencies are healthy."""
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)
        mock_get_db_session.return_value = mock_session
        
        # Mock cache client
        mock_cache_client = AsyncMock()
        mock_cache_client.ping.return_value = True
        mock_get_cache_client.return_value = mock_cache_client
        
        result = await readiness_check(mock_session)
        
        assert result["status"] == "ready"
        assert result["database"] is True
        assert result["cache"] is True
        assert "timestamp" in result
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_detailed_health_check_success(
        self, 
        mock_get_cache_client, 
        mock_get_db_session
    ):
        """Test detailed health check when all dependencies are healthy."""
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)
        mock_get_db_session.return_value = mock_session
        
        # Mock cache client
        mock_cache_client = AsyncMock()
        mock_cache_client.ping.return_value = True
        mock_get_cache_client.return_value = mock_cache_client
        
        result = await detailed_health_check(mock_session)
        
        assert result["status"] == "healthy"
        assert result["service"] == "EasyPay Payment Gateway"
        assert result["version"] == "0.1.0"
        assert "timestamp" in result
        
        # Check dependencies
        assert result["dependencies"]["database"]["status"] == "healthy"
        assert result["dependencies"]["cache"]["status"] == "healthy"
        assert "response_time_ms" in result["dependencies"]["database"]
        assert "response_time_ms" in result["dependencies"]["cache"]
        
        # Check system info
        assert "system" in result
        assert "uptime" in result["system"]
        assert "memory_usage" in result["system"]
        assert "cpu_usage" in result["system"]
