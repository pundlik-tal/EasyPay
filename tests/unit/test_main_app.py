"""
EasyPay Payment Gateway - Main Application Tests
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Mock the problematic imports before importing main
with patch('src.infrastructure.database.init_database'), \
     patch('src.infrastructure.cache.init_cache'), \
     patch('src.infrastructure.monitoring.setup_logging'):
    from src.main import app


class TestMainApp:
    """Test main application functionality."""
    
    def test_app_creation(self):
        """Test that the FastAPI app is created correctly."""
        assert isinstance(app, FastAPI)
        assert app.title == "EasyPay Payment Gateway"
        assert app.version == "0.1.0"
    
    def test_app_routes(self):
        """Test that all routes are registered."""
        routes = [route.path for route in app.routes]
        
        # Check that key routes exist
        assert "/health" in str(routes)
        assert "/api/v1/payments" in str(routes)
        assert "/metrics" in str(routes)
        assert "/" in str(routes)
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "EasyPay Payment Gateway"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        client = TestClient(app)
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Check that metrics content is returned
        content = response.text
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
    
    def test_docs_endpoint(self):
        """Test that docs endpoint is accessible."""
        client = TestClient(app)
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_endpoint(self):
        """Test OpenAPI schema endpoint."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["info"]["title"] == "EasyPay Payment Gateway"
        assert data["info"]["version"] == "0.1.0"
        assert "paths" in data
    
    @patch('src.infrastructure.database.init_database')
    @patch('src.infrastructure.cache.init_cache')
    async def test_lifespan_startup(self, mock_init_cache, mock_init_database):
        """Test application lifespan startup."""
        from src.main import lifespan
        
        # Mock the async context manager
        mock_init_database.return_value = AsyncMock()
        mock_init_cache.return_value = AsyncMock()
        
        # Test startup
        async with lifespan(app):
            pass
        
        # Verify initialization was called
        mock_init_database.assert_called_once()
        mock_init_cache.assert_called_once()
    
    def test_cors_middleware(self):
        """Test that CORS middleware is configured."""
        # Check that CORS middleware is in the middleware stack
        middleware_types = [type(middleware).__name__ for middleware in app.user_middleware]
        assert "CORSMiddleware" in middleware_types
    
    def test_trusted_host_middleware(self):
        """Test that TrustedHostMiddleware is configured."""
        # Check that TrustedHostMiddleware is in the middleware stack
        middleware_types = [type(middleware).__name__ for middleware in app.user_middleware]
        assert "TrustedHostMiddleware" in middleware_types
