"""
EasyPay Payment Gateway - Health Check Integration Tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.infrastructure.database import get_db_session
from src.infrastructure.cache import get_cache_client


@pytest.fixture
async def test_client() -> AsyncClient:
    """Create a test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value.fetchone.return_value = (1,)
    return mock_session


@pytest.fixture
def mock_cache_client():
    """Mock cache client."""
    mock_cache = AsyncMock()
    mock_cache.ping.return_value = True
    return mock_cache


class TestHealthCheckEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.integration
    async def test_basic_health_check(self, test_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await test_client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "EasyPay Payment Gateway"
        assert data["version"] == "0.1.0"
    
    @pytest.mark.integration
    async def test_liveness_check(self, test_client: AsyncClient):
        """Test liveness check endpoint."""
        response = await test_client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert "timestamp" in data
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_readiness_check_success(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session,
        mock_cache_client
    ):
        """Test readiness check when all dependencies are healthy."""
        mock_get_db_session.return_value = mock_db_session
        mock_get_cache_client.return_value = mock_cache_client
        
        response = await test_client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert data["database"] is True
        assert data["cache"] is True
        assert "timestamp" in data
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    async def test_readiness_check_database_failure(
        self, 
        mock_get_db_session,
        test_client: AsyncClient
    ):
        """Test readiness check when database is not available."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database connection failed")
        mock_get_db_session.return_value = mock_session
        
        response = await test_client.get("/health/ready")
        
        assert response.status_code == 503
        data = response.json()
        
        assert "Database not ready" in data["detail"]
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_readiness_check_cache_failure(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session
    ):
        """Test readiness check when cache is not available."""
        mock_get_db_session.return_value = mock_db_session
        
        mock_cache = AsyncMock()
        mock_cache.ping.side_effect = Exception("Cache connection failed")
        mock_get_cache_client.return_value = mock_cache
        
        response = await test_client.get("/health/ready")
        
        assert response.status_code == 503
        data = response.json()
        
        assert "Cache not ready" in data["detail"]
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_detailed_health_check_success(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session,
        mock_cache_client
    ):
        """Test detailed health check when all dependencies are healthy."""
        mock_get_db_session.return_value = mock_db_session
        mock_get_cache_client.return_value = mock_cache_client
        
        response = await test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "EasyPay Payment Gateway"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        
        # Check dependencies
        assert data["dependencies"]["database"]["status"] == "healthy"
        assert data["dependencies"]["cache"]["status"] == "healthy"
        assert "response_time_ms" in data["dependencies"]["database"]
        assert "response_time_ms" in data["dependencies"]["cache"]
        
        # Check system info
        assert "system" in data
        assert "uptime" in data["system"]
        assert "memory_usage" in data["system"]
        assert "cpu_usage" in data["system"]
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_detailed_health_check_database_failure(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_cache_client
    ):
        """Test detailed health check when database fails."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database connection failed")
        mock_get_db_session.return_value = mock_session
        mock_get_cache_client.return_value = mock_cache_client
        
        response = await test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"]["status"] == "unhealthy"
        assert "error" in data["dependencies"]["database"]
        assert data["dependencies"]["cache"]["status"] == "healthy"
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_detailed_health_check_cache_failure(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session
    ):
        """Test detailed health check when cache fails."""
        mock_get_db_session.return_value = mock_db_session
        
        mock_cache = AsyncMock()
        mock_cache.ping.side_effect = Exception("Cache connection failed")
        mock_get_cache_client.return_value = mock_cache
        
        response = await test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"]["status"] == "healthy"
        assert data["dependencies"]["cache"]["status"] == "unhealthy"
        assert "error" in data["dependencies"]["cache"]
    
    @pytest.mark.integration
    async def test_root_endpoint(self, test_client: AsyncClient):
        """Test root endpoint."""
        response = await test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "EasyPay Payment Gateway"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
    
    @pytest.mark.integration
    async def test_metrics_endpoint(self, test_client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await test_client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Check that metrics content is returned
        content = response.text
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content


class TestHealthCheckPerformance:
    """Test health check performance."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_health_check_response_time(self, test_client: AsyncClient):
        """Test that health checks respond within acceptable time."""
        import time
        
        start_time = time.time()
        response = await test_client.get("/health/")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
    
    @pytest.mark.integration
    @pytest.mark.slow
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_readiness_check_response_time(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session,
        mock_cache_client
    ):
        """Test that readiness checks respond within acceptable time."""
        mock_get_db_session.return_value = mock_db_session
        mock_get_cache_client.return_value = mock_cache_client
        
        import time
        
        start_time = time.time()
        response = await test_client.get("/health/ready")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds


class TestHealthCheckConcurrency:
    """Test health check concurrency."""
    
    @pytest.mark.integration
    async def test_concurrent_health_checks(self, test_client: AsyncClient):
        """Test multiple concurrent health check requests."""
        import asyncio
        
        async def make_request():
            return await test_client.get("/health/")
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    @pytest.mark.integration
    @patch('src.infrastructure.database.get_db_session')
    @patch('src.infrastructure.cache.get_cache_client')
    async def test_concurrent_readiness_checks(
        self, 
        mock_get_cache_client, 
        mock_get_db_session,
        test_client: AsyncClient,
        mock_db_session,
        mock_cache_client
    ):
        """Test multiple concurrent readiness check requests."""
        mock_get_db_session.return_value = mock_db_session
        mock_get_cache_client.return_value = mock_cache_client
        
        import asyncio
        
        async def make_request():
            return await test_client.get("/health/ready")
        
        # Make 5 concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] is True
            assert data["cache"] is True
