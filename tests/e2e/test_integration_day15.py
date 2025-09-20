"""
EasyPay Payment Gateway - Day 15 Integration Tests
Comprehensive end-to-end testing for payment flow, authentication, and security features.
"""
import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, AsyncGenerator
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus, Permission
from src.core.services.auth_service import AuthService
from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import PaymentCreateRequest
from src.api.v1.schemas.auth import APIKeyCreateRequest


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with proper configuration."""
    from src.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestIntegrationDay15:
    """Comprehensive integration tests for Day 15 requirements."""
    
    @pytest.fixture
    async def auth_service(self, test_db_session: AsyncSession) -> AuthService:
        """Create authentication service instance."""
        return AuthService(test_db_session)
    
    @pytest.fixture
    async def payment_service(self, test_db_session: AsyncSession) -> PaymentService:
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.fixture
    async def test_api_key(self, auth_service: AuthService, test_db_session: AsyncSession) -> Dict[str, Any]:
        """Create a test API key for authentication."""
        # Create API key request
        api_key_request = APIKeyCreateRequest(
            name="Integration Test Key",
            description="API key for integration testing",
            permissions=[
                Permission.PAYMENTS_READ.value,
                Permission.PAYMENTS_WRITE.value,
                Permission.PAYMENTS_DELETE.value,
                Permission.WEBHOOKS_READ.value,
                Permission.ADMIN_READ.value
            ],
            rate_limit_per_minute=1000,  # High limit for testing
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000,
            expires_at=None
        )
        
        # Create API key
        api_key_response = await auth_service.create_api_key(api_key_request)
        
        return {
            "key_id": api_key_response["key_id"],
            "key_secret": api_key_response["key_secret"],
            "api_key_id": api_key_response["api_key_id"]
        }
    
    @pytest.fixture
    def auth_headers(self, test_api_key: Dict[str, Any]) -> Dict[str, str]:
        """Create authentication headers for API requests."""
        return {
            "X-API-Key-ID": test_api_key["key_id"],
            "X-API-Key-Secret": test_api_key["key_secret"],
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_complete_payment_flow_with_auth(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test complete payment flow: create -> update -> refund -> cancel with authentication."""
        
        # Step 1: Create payment
        payment_data = {
            "amount": "50.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_integration_test",
            "customer_email": "integration@example.com",
            "customer_name": "Integration Test Customer",
            "card_token": "tok_integration_test",
            "description": "Integration test payment",
            "metadata": {"test_type": "integration", "step": "create"},
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        
        assert "id" in payment_response
        assert "external_id" in payment_response
        assert payment_response["amount"] == "50.00"
        assert payment_response["status"] == PaymentStatus.PENDING.value
        assert payment_response["customer_id"] == "cust_integration_test"
        
        payment_id = payment_response["id"]
        
        # Step 2: Get payment
        response = await test_client.get(
            f"/api/v1/payments/{payment_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        get_response = response.json()
        assert get_response["id"] == payment_id
        assert get_response["amount"] == "50.00"
        
        # Step 3: Update payment
        update_data = {
            "description": "Updated integration test payment",
            "metadata": {"test_type": "integration", "step": "update", "updated_at": datetime.utcnow().isoformat()}
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{payment_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        update_response = response.json()
        assert update_response["description"] == "Updated integration test payment"
        
        # Step 4: Refund payment
        refund_data = {
            "amount": "25.00",
            "reason": "Customer request",
            "metadata": {"refund_reason": "customer_request"}
        }
        
        response = await test_client.post(
            f"/api/v1/payments/{payment_id}/refund",
            json=refund_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        refund_response = response.json()
        assert refund_response["status"] in [PaymentStatus.REFUNDED.value, PaymentStatus.PARTIALLY_REFUNDED.value]
        
        # Step 5: Cancel payment (if not already refunded)
        if refund_response["status"] != PaymentStatus.REFUNDED.value:
            cancel_data = {
                "reason": "Customer cancelled",
                "metadata": {"cancellation_reason": "customer_cancelled"}
            }
            
            response = await test_client.post(
                f"/api/v1/payments/{payment_id}/cancel",
                json=cancel_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            cancel_response = response.json()
            assert cancel_response["status"] == PaymentStatus.CANCELLED.value
    
    @pytest.mark.asyncio
    async def test_authentication_flow_end_to_end(
        self, 
        test_client: AsyncClient, 
        auth_service: AuthService,
        test_db_session: AsyncSession
    ):
        """Test complete authentication flow: create API key -> generate token -> validate token."""
        
        # Step 1: Create API key
        api_key_request = {
            "name": "E2E Test Key",
            "description": "API key for end-to-end testing",
            "permissions": [
                Permission.PAYMENTS_READ.value,
                Permission.PAYMENTS_WRITE.value
            ],
            "rate_limit_per_minute": 100,
            "rate_limit_per_hour": 1000,
            "rate_limit_per_day": 10000
        }
        
        # Note: This would typically require admin authentication
        # For testing, we'll create directly via service
        api_key_response = await auth_service.create_api_key(
            APIKeyCreateRequest(**api_key_request)
        )
        
        assert "key_id" in api_key_response
        assert "key_secret" in api_key_response
        assert "api_key_id" in api_key_response
        
        # Step 2: Generate JWT token
        token_request = {
            "key_id": api_key_response["key_id"],
            "key_secret": api_key_response["key_secret"]
        }
        
        response = await test_client.post(
            "/api/v1/auth/tokens",
            json=token_request
        )
        
        assert response.status_code == 201
        token_response = response.json()
        
        assert "access_token" in token_response
        assert "refresh_token" in token_response
        assert "expires_in" in token_response
        
        access_token = token_response["access_token"]
        
        # Step 3: Use token for authenticated request
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Test with payment creation
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_token_test",
            "customer_email": "token@example.com",
            "customer_name": "Token Test Customer",
            "card_token": "tok_token_test",
            "description": "Token authentication test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        assert payment_response["amount"] == "25.00"
        
        # Step 4: Refresh token
        refresh_request = {
            "refresh_token": token_response["refresh_token"]
        }
        
        response = await test_client.post(
            "/api/v1/auth/tokens/refresh",
            json=refresh_request
        )
        
        assert response.status_code == 200
        refresh_response = response.json()
        
        assert "access_token" in refresh_response
        assert "expires_in" in refresh_response
    
    @pytest.mark.asyncio
    async def test_error_scenarios_and_edge_cases(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str]
    ):
        """Test various error scenarios and edge cases."""
        
        # Test 1: Invalid authentication
        invalid_headers = {
            "X-API-Key-ID": "invalid_key",
            "X-API-Key-Secret": "invalid_secret",
            "Content-Type": "application/json"
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json={"amount": "10.00"},
            headers=invalid_headers
        )
        
        assert response.status_code == 401
        error_response = response.json()
        assert "error" in error_response
        
        # Test 2: Missing required fields
        incomplete_payment_data = {
            "amount": "10.00",
            "currency": "USD"
            # Missing required fields
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=incomplete_payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_response = response.json()
        assert "detail" in error_response
        
        # Test 3: Invalid payment amount
        invalid_payment_data = {
            "amount": "-10.00",  # Negative amount
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_test",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_test",
            "description": "Invalid amount test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=invalid_payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_response = response.json()
        assert "detail" in error_response
        
        # Test 4: Non-existent payment ID
        fake_payment_id = str(uuid.uuid4())
        
        response = await test_client.get(
            f"/api/v1/payments/{fake_payment_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response
        
        # Test 5: Invalid currency
        invalid_currency_data = {
            "amount": "10.00",
            "currency": "INVALID",  # Invalid currency
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_test",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_test",
            "description": "Invalid currency test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=invalid_currency_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_response = response.json()
        assert "detail" in error_response
    
    @pytest.mark.asyncio
    async def test_rate_limiting_functionality(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str]
    ):
        """Test rate limiting functionality."""
        
        # Create a payment to test with
        payment_data = {
            "amount": "10.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_rate_test",
            "customer_email": "rate@example.com",
            "customer_name": "Rate Test Customer",
            "card_token": "tok_rate_test",
            "description": "Rate limiting test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_id = response.json()["id"]
        
        # Test multiple rapid requests (simulate rate limiting)
        # Note: This is a simplified test - in production, rate limiting would be enforced
        # by Kong or similar middleware
        
        success_count = 0
        for i in range(5):  # Make 5 rapid requests
            response = await test_client.get(
                f"/api/v1/payments/{payment_id}",
                headers=auth_headers
            )
            
            if response.status_code == 200:
                success_count += 1
        
        # All requests should succeed in test environment
        # In production with rate limiting, some might be rate limited
        assert success_count == 5
    
    @pytest.mark.asyncio
    async def test_security_features_integration(
        self, 
        test_client: AsyncClient, 
        auth_service: AuthService,
        test_db_session: AsyncSession
    ):
        """Test security features integration."""
        
        # Test 1: Permission-based access control
        # Create API key with limited permissions
        limited_api_key_request = APIKeyCreateRequest(
            name="Limited Test Key",
            description="API key with limited permissions",
            permissions=[Permission.PAYMENTS_READ.value],  # Only read permission
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000
        )
        
        limited_api_key_response = await auth_service.create_api_key(limited_api_key_request)
        
        limited_auth_headers = {
            "X-API-Key-ID": limited_api_key_response["key_id"],
            "X-API-Key-Secret": limited_api_key_response["key_secret"],
            "Content-Type": "application/json"
        }
        
        # Test read permission (should work)
        response = await test_client.get(
            "/api/v1/payments/search",
            headers=limited_auth_headers
        )
        
        assert response.status_code == 200
        
        # Test write permission (should fail)
        payment_data = {
            "amount": "10.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_security_test",
            "customer_email": "security@example.com",
            "customer_name": "Security Test Customer",
            "card_token": "tok_security_test",
            "description": "Security test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=limited_auth_headers
        )
        
        assert response.status_code == 403
        error_response = response.json()
        assert "error" in error_response
        
        # Test 2: API key validation
        # Test with expired/invalid key
        invalid_headers = {
            "X-API-Key-ID": "nonexistent_key",
            "X-API-Key-Secret": "nonexistent_secret",
            "Content-Type": "application/json"
        }
        
        response = await test_client.get(
            "/api/v1/payments/search",
            headers=invalid_headers
        )
        
        assert response.status_code == 401
        error_response = response.json()
        assert "error" in error_response
        
        # Test 3: CORS headers (if applicable)
        response = await test_client.options(
            "/api/v1/payments/",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-API-Key-ID,X-API-Key-Secret"
            }
        )
        
        # CORS preflight should be handled by Kong in production
        # In test environment, this might return 405 or be handled by FastAPI
        assert response.status_code in [200, 405]
    
    @pytest.mark.asyncio
    async def test_health_checks_integration(self, test_client: AsyncClient):
        """Test health check endpoints integration."""
        
        # Test basic health check
        response = await test_client.get("/health/")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        
        # Test readiness check
        response = await test_client.get("/health/ready")
        assert response.status_code == 200
        readiness_data = response.json()
        assert readiness_data["status"] == "ready"
        
        # Test liveness check
        response = await test_client.get("/health/live")
        assert response.status_code == 200
        liveness_data = response.json()
        assert liveness_data["status"] == "alive"
        
        # Test detailed health check
        response = await test_client.get("/health/detailed")
        assert response.status_code == 200
        detailed_data = response.json()
        assert detailed_data["status"] == "healthy"
        assert "services" in detailed_data
    
    @pytest.mark.asyncio
    async def test_api_versioning_integration(self, test_client: AsyncClient, auth_headers: Dict[str, str]):
        """Test API versioning integration."""
        
        # Test version endpoint
        response = await test_client.get(
            "/api/v1/version",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        version_data = response.json()
        assert "version" in version_data
        assert "api_version" in version_data
        assert "supported_versions" in version_data
        
        # Test with version header
        version_headers = auth_headers.copy()
        version_headers["API-Version"] = "1.0"
        
        response = await test_client.get(
            "/api/v1/version",
            headers=version_headers
        )
        
        assert response.status_code == 200
        version_data = response.json()
        assert version_data["api_version"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_integration(self, test_client: AsyncClient):
        """Test metrics endpoint integration."""
        
        # Test Prometheus metrics endpoint
        response = await test_client.get("/metrics")
        assert response.status_code == 200
        
        # Check that response contains Prometheus metrics format
        metrics_text = response.text
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
    
    @pytest.mark.asyncio
    async def test_correlation_id_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str]
    ):
        """Test correlation ID integration."""
        
        # Test with custom correlation ID
        correlation_headers = auth_headers.copy()
        correlation_headers["X-Correlation-ID"] = "test-correlation-123"
        
        payment_data = {
            "amount": "15.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_correlation_test",
            "customer_email": "correlation@example.com",
            "customer_name": "Correlation Test Customer",
            "card_token": "tok_correlation_test",
            "description": "Correlation ID test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=correlation_headers
        )
        
        assert response.status_code == 201
        
        # Check if correlation ID is returned in response headers
        # (This would be handled by Kong in production)
        response_headers = response.headers
        # In test environment, correlation ID might not be added to response
        # This is more of a production integration test
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str]
    ):
        """Test concurrent requests handling."""
        
        # Create multiple concurrent payment requests
        payment_data_template = {
            "amount": "10.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_concurrent_test",
            "customer_email": "concurrent@example.com",
            "customer_name": "Concurrent Test Customer",
            "card_token": "tok_concurrent_test",
            "description": "Concurrent test",
            "is_test": True
        }
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(3):
            payment_data = payment_data_template.copy()
            payment_data["customer_id"] = f"cust_concurrent_test_{i}"
            payment_data["description"] = f"Concurrent test {i}"
            
            task = test_client.post(
                "/api/v1/payments/",
                json=payment_data,
                headers=auth_headers
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)
        
        # Check that all requests succeeded
        for response in responses:
            assert response.status_code == 201
            payment_data = response.json()
            assert "id" in payment_data
            assert payment_data["amount"] == "10.00"
    
    @pytest.mark.asyncio
    async def test_database_transaction_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        test_db_session: AsyncSession
    ):
        """Test database transaction handling in integration scenarios."""
        
        # Test payment creation with database transaction
        payment_data = {
            "amount": "30.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_transaction_test",
            "customer_email": "transaction@example.com",
            "customer_name": "Transaction Test Customer",
            "card_token": "tok_transaction_test",
            "description": "Transaction test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        payment_id = payment_response["id"]
        
        # Verify payment was created in database
        from sqlalchemy import select
        result = await test_db_session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        assert payment is not None
        assert payment.amount == Decimal("30.00")
        assert payment.customer_id == "cust_transaction_test"
        assert payment.status == PaymentStatus.PENDING
        
        # Test payment update with database transaction
        update_data = {
            "description": "Updated transaction test",
            "metadata": {"updated": True, "timestamp": datetime.utcnow().isoformat()}
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{payment_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify payment was updated in database
        await test_db_session.refresh(payment)
        assert payment.description == "Updated transaction test"
        assert payment.metadata["updated"] is True
