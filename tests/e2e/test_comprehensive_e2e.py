"""
EasyPay Payment Gateway - Comprehensive End-to-End Tests

This module contains comprehensive end-to-end tests that test the complete
application flow from API requests to database operations.
"""

import pytest
import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.main import app
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.webhook import Webhook, WebhookStatus
from src.core.exceptions import (
    PaymentError, PaymentNotFoundError, ValidationError, DatabaseError,
    ExternalServiceError, AuthenticationError, AuthorizationError,
    WebhookError, CacheError
)


class TestPaymentE2E:
    """End-to-end tests for payment operations."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    async def authenticated_client(self, client):
        """Create authenticated test client."""
        # Create API key for authentication
        api_key_data = {
            "name": "E2E Test Key",
            "environment": "sandbox",
            "permissions": ["payment:create", "payment:read", "payment:update", "payment:refund"]
        }
        
        response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
        assert response.status_code == 201
        api_key = response.json()["data"]["key"]
        
        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {api_key}"})
        return client
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_payment_flow_e2e(self, authenticated_client):
        """Test complete payment flow from creation to settlement."""
        # Step 1: Create payment
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_e2e_123",
            "customer_email": "e2e@example.com",
            "customer_name": "E2E Test Customer",
            "card_token": "tok_e2e_123",
            "description": "E2E test payment",
            "metadata": {"test_type": "e2e", "flow": "complete"},
            "is_test": True
        }
        
        create_response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert create_response.status_code == 201
        
        payment = create_response.json()["data"]
        payment_id = payment["id"]
        assert payment["amount"] == "25.00"
        assert payment["status"] == "pending"
        assert payment["customer_id"] == "cust_e2e_123"
        
        # Step 2: Get payment details
        get_response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
        assert get_response.status_code == 200
        
        payment_details = get_response.json()["data"]
        assert payment_details["id"] == payment_id
        assert payment_details["amount"] == "25.00"
        
        # Step 3: Update payment status (simulate authorization)
        update_data = {
            "status": "authorized",
            "metadata": {"authorized_at": datetime.utcnow().isoformat()}
        }
        
        update_response = await authenticated_client.put(f"/api/v1/payments/{payment_id}", json=update_data)
        assert update_response.status_code == 200
        
        updated_payment = update_response.json()["data"]
        assert updated_payment["status"] == "authorized"
        
        # Step 4: Process capture
        capture_data = {
            "amount": "25.00",
            "metadata": {"captured_at": datetime.utcnow().isoformat()}
        }
        
        capture_response = await authenticated_client.post(f"/api/v1/payments/{payment_id}/capture", json=capture_data)
        assert capture_response.status_code == 200
        
        captured_payment = capture_response.json()["data"]
        assert captured_payment["status"] == "captured"
        
        # Step 5: Process partial refund
        refund_data = {
            "amount": "10.00",
            "reason": "Customer requested partial refund",
            "metadata": {"refund_type": "partial", "refunded_at": datetime.utcnow().isoformat()}
        }
        
        refund_response = await authenticated_client.post(f"/api/v1/payments/{payment_id}/refund", json=refund_data)
        assert refund_response.status_code == 200
        
        refunded_payment = refund_response.json()["data"]
        assert refunded_payment["status"] == "partially_refunded"
        
        # Step 6: Verify final payment state
        final_response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
        assert final_response.status_code == 200
        
        final_payment = final_response.json()["data"]
        assert final_payment["status"] == "partially_refunded"
        assert final_payment["refunded_amount"] == "10.00"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_payment_search_and_filtering_e2e(self, authenticated_client):
        """Test payment search and filtering functionality."""
        # Create multiple test payments
        payments = []
        for i in range(5):
            payment_data = {
                "amount": f"{10 + i}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_search_{i}",
                "customer_email": f"search{i}@example.com",
                "customer_name": f"Search Test Customer {i}",
                "card_token": f"tok_search_{i}",
                "description": f"Search test payment {i}",
                "metadata": {"search_test": True, "index": i},
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            assert response.status_code == 201
            payments.append(response.json()["data"])
        
        # Test search by customer ID
        search_response = await authenticated_client.get("/api/v1/payments/search?customer_id=cust_search_1")
        assert search_response.status_code == 200
        
        search_results = search_response.json()["data"]
        assert len(search_results) == 1
        assert search_results[0]["customer_id"] == "cust_search_1"
        
        # Test search by amount range
        search_response = await authenticated_client.get("/api/v1/payments/search?min_amount=12.00&max_amount=14.00")
        assert search_response.status_code == 200
        
        search_results = search_response.json()["data"]
        assert len(search_results) == 3  # payments with amounts 12, 13, 14
        
        # Test search by status
        search_response = await authenticated_client.get("/api/v1/payments/search?status=pending")
        assert search_response.status_code == 200
        
        search_results = search_response.json()["data"]
        assert len(search_results) >= 5  # All created payments should be pending
        
        # Test search with multiple filters
        search_response = await authenticated_client.get("/api/v1/payments/search?min_amount=12.00&max_amount=14.00&status=pending")
        assert search_response.status_code == 200
        
        search_results = search_response.json()["data"]
        assert len(search_results) == 3
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_payment_error_handling_e2e(self, authenticated_client):
        """Test payment error handling scenarios."""
        # Test invalid payment data
        invalid_payment_data = {
            "amount": "-10.00",  # Negative amount
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_error_123",
            "customer_email": "error@example.com",
            "customer_name": "Error Test Customer",
            "card_token": "tok_error_123",
            "description": "Error test payment",
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=invalid_payment_data)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "detail" in error_data
        
        # Test payment not found
        fake_payment_id = str(uuid.uuid4())
        response = await authenticated_client.get(f"/api/v1/payments/{fake_payment_id}")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()
        
        # Test invalid refund amount
        # First create a valid payment
        payment_data = {
            "amount": "20.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_error_456",
            "customer_email": "error2@example.com",
            "customer_name": "Error Test Customer 2",
            "card_token": "tok_error_456",
            "description": "Error test payment 2",
            "is_test": True
        }
        
        create_response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert create_response.status_code == 201
        
        payment_id = create_response.json()["data"]["id"]
        
        # Try to refund more than the payment amount
        invalid_refund_data = {
            "amount": "50.00",  # More than payment amount
            "reason": "Invalid refund amount"
        }
        
        refund_response = await authenticated_client.post(f"/api/v1/payments/{payment_id}/refund", json=invalid_refund_data)
        assert refund_response.status_code == 422  # Validation error


class TestAuthenticationE2E:
    """End-to-end tests for authentication operations."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_api_key_lifecycle_e2e(self, client):
        """Test complete API key lifecycle."""
        # Step 1: Create API key
        api_key_data = {
            "name": "E2E API Key Test",
            "environment": "sandbox",
            "permissions": ["payment:create", "payment:read", "payment:update"]
        }
        
        create_response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
        assert create_response.status_code == 201
        
        api_key_info = create_response.json()["data"]
        api_key_id = api_key_info["id"]
        api_key_value = api_key_info["key"]
        
        assert api_key_info["name"] == "E2E API Key Test"
        assert api_key_info["environment"] == "sandbox"
        assert api_key_info["is_active"] is True
        
        # Step 2: Test API key authentication
        authenticated_client = AsyncClient(app=app, base_url="http://test")
        authenticated_client.headers.update({"Authorization": f"Bearer {api_key_value}"})
        
        # Test authenticated request
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # Step 3: Get API key details
        get_response = await client.get(f"/api/v1/auth/api-keys/{api_key_id}")
        assert get_response.status_code == 200
        
        api_key_details = get_response.json()["data"]
        assert api_key_details["id"] == api_key_id
        assert api_key_details["name"] == "E2E API Key Test"
        
        # Step 4: Update API key permissions
        update_data = {
            "permissions": ["payment:create", "payment:read"]  # Remove update permission
        }
        
        update_response = await client.put(f"/api/v1/auth/api-keys/{api_key_id}", json=update_data)
        assert update_response.status_code == 200
        
        updated_api_key = update_response.json()["data"]
        assert len(updated_api_key["permissions"]) == 2
        assert "payment:create" in updated_api_key["permissions"]
        assert "payment:update" not in updated_api_key["permissions"]
        
        # Step 5: Revoke API key
        revoke_response = await client.delete(f"/api/v1/auth/api-keys/{api_key_id}")
        assert revoke_response.status_code == 200
        
        # Step 6: Test revoked API key
        revoked_response = await authenticated_client.get("/api/v1/health")
        assert revoked_response.status_code == 401  # Unauthorized
        
        await authenticated_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_token_lifecycle_e2e(self, client):
        """Test JWT token lifecycle."""
        # Step 1: Generate tokens
        token_data = {
            "user_id": "user_e2e_123",
            "permissions": ["payment:create", "payment:read", "payment:update"]
        }
        
        generate_response = await client.post("/api/v1/auth/tokens", json=token_data)
        assert generate_response.status_code == 201
        
        tokens = generate_response.json()["data"]
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Step 2: Test access token
        authenticated_client = AsyncClient(app=app, base_url="http://test")
        authenticated_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        # Test authenticated request
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # Step 3: Refresh token
        refresh_data = {"refresh_token": refresh_token}
        
        refresh_response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        new_tokens = refresh_response.json()["data"]
        new_access_token = new_tokens["access_token"]
        
        assert "access_token" in new_tokens
        assert new_access_token != access_token  # Should be different
        
        # Step 4: Test new access token
        authenticated_client.headers.update({"Authorization": f"Bearer {new_access_token}"})
        
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # Step 5: Test old access token (should be invalid)
        authenticated_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 401  # Unauthorized
        
        await authenticated_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_authentication_error_handling_e2e(self, client):
        """Test authentication error handling."""
        # Test invalid API key
        invalid_client = AsyncClient(app=app, base_url="http://test")
        invalid_client.headers.update({"Authorization": "Bearer invalid_api_key"})
        
        response = await invalid_client.get("/api/v1/health")
        assert response.status_code == 401
        
        error_data = response.json()
        assert "detail" in error_data
        assert "invalid" in error_data["detail"].lower()
        
        # Test missing authorization header
        no_auth_client = AsyncClient(app=app, base_url="http://test")
        
        response = await no_auth_client.get("/api/v1/payments")
        assert response.status_code == 401
        
        error_data = response.json()
        assert "detail" in error_data
        assert "missing" in error_data["detail"].lower() or "required" in error_data["detail"].lower()
        
        # Test invalid JWT token
        invalid_jwt_client = AsyncClient(app=app, base_url="http://test")
        invalid_jwt_client.headers.update({"Authorization": "Bearer invalid.jwt.token"})
        
        response = await invalid_jwt_client.get("/api/v1/health")
        assert response.status_code == 401
        
        await invalid_client.aclose()
        await no_auth_client.aclose()
        await invalid_jwt_client.aclose()


class TestWebhookE2E:
    """End-to-end tests for webhook operations."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "E2E Webhook Test Key",
                "environment": "sandbox",
                "permissions": ["webhook:create", "webhook:read", "webhook:update", "webhook:delete"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_webhook_lifecycle_e2e(self, authenticated_client):
        """Test complete webhook lifecycle."""
        # Step 1: Register webhook
        webhook_data = {
            "webhook_url": "https://e2e-test.example.com/webhook",
            "event_type": "payment.created",
            "secret": "e2e_webhook_secret",
            "max_retries": 3,
            "retry_interval": 60,
            "is_active": True,
            "metadata": {"test_type": "e2e"}
        }
        
        register_response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
        assert register_response.status_code == 201
        
        webhook = register_response.json()["data"]
        webhook_id = webhook["id"]
        
        assert webhook["webhook_url"] == "https://e2e-test.example.com/webhook"
        assert webhook["event_type"] == "payment.created"
        assert webhook["max_retries"] == 3
        assert webhook["is_active"] is True
        
        # Step 2: Get webhook details
        get_response = await authenticated_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        
        webhook_details = get_response.json()["data"]
        assert webhook_details["id"] == webhook_id
        assert webhook_details["webhook_url"] == "https://e2e-test.example.com/webhook"
        
        # Step 3: Update webhook configuration
        update_data = {
            "webhook_url": "https://updated-e2e-test.example.com/webhook",
            "max_retries": 5,
            "retry_interval": 120
        }
        
        update_response = await authenticated_client.put(f"/api/v1/webhooks/{webhook_id}", json=update_data)
        assert update_response.status_code == 200
        
        updated_webhook = update_response.json()["data"]
        assert updated_webhook["webhook_url"] == "https://updated-e2e-test.example.com/webhook"
        assert updated_webhook["max_retries"] == 5
        assert updated_webhook["retry_interval"] == 120
        
        # Step 4: Test webhook delivery
        delivery_data = {
            "event": "payment.created",
            "data": {
                "payment_id": "pay_e2e_123",
                "amount": "25.00",
                "currency": "USD",
                "status": "pending"
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success"}
            
            delivery_response = await authenticated_client.post(f"/api/v1/webhooks/{webhook_id}/deliver", json=delivery_data)
            assert delivery_response.status_code == 200
            
            delivery_result = delivery_response.json()["data"]
            assert delivery_result["status"] == "delivered"
        
        # Step 5: Get webhook delivery history
        history_response = await authenticated_client.get(f"/api/v1/webhooks/{webhook_id}/deliveries")
        assert history_response.status_code == 200
        
        history = history_response.json()["data"]
        assert len(history) >= 1
        assert history[0]["status"] == "delivered"
        
        # Step 6: Deactivate webhook
        deactivate_response = await authenticated_client.delete(f"/api/v1/webhooks/{webhook_id}")
        assert deactivate_response.status_code == 200
        
        # Step 7: Verify webhook is deactivated
        get_response = await authenticated_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        
        deactivated_webhook = get_response.json()["data"]
        assert deactivated_webhook["is_active"] is False
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_webhook_retry_logic_e2e(self, authenticated_client):
        """Test webhook retry logic."""
        # Register webhook
        webhook_data = {
            "webhook_url": "https://retry-test.example.com/webhook",
            "event_type": "payment.created",
            "secret": "retry_webhook_secret",
            "max_retries": 3,
            "retry_interval": 60
        }
        
        register_response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
        assert register_response.status_code == 201
        
        webhook_id = register_response.json()["data"]["id"]
        
        # Test webhook delivery with failure
        delivery_data = {
            "event": "payment.created",
            "data": {
                "payment_id": "pay_retry_123",
                "amount": "30.00",
                "currency": "USD",
                "status": "pending"
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.json.return_value = {"error": "Internal server error"}
            
            delivery_response = await authenticated_client.post(f"/api/v1/webhooks/{webhook_id}/deliver", json=delivery_data)
            assert delivery_response.status_code == 200
            
            delivery_result = delivery_response.json()["data"]
            assert delivery_result["status"] == "failed"
        
        # Check retry attempts
        retry_response = await authenticated_client.get(f"/api/v1/webhooks/{webhook_id}/retries")
        assert retry_response.status_code == 200
        
        retries = retry_response.json()["data"]
        assert len(retries) >= 1
        assert retries[0]["status"] == "failed"


class TestAuthorizeNetWebhookE2E:
    """End-to-end tests for Authorize.net webhook processing."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_authorize_net_webhook_processing_e2e(self, client):
        """Test Authorize.net webhook processing."""
        # Test webhook endpoint
        webhook_data = {
            "notificationId": "webhook_e2e_123",
            "eventType": "net.authorize.payment.authcapture.created",
            "eventDate": datetime.utcnow().isoformat(),
            "webhookId": "webhook_e2e_456",
            "payload": {
                "merchantCustomerId": "cust_e2e_123",
                "id": "pay_e2e_123",
                "amount": "25.00",
                "currencyCode": "USD",
                "status": "capturedPendingSettlement"
            }
        }
        
        # Generate HMAC signature
        import hmac
        import hashlib
        import json
        
        webhook_secret = "test_webhook_secret"
        payload_json = json.dumps(webhook_data)
        signature = hmac.new(
            webhook_secret.encode(),
            payload_json.encode(),
            hashlib.sha512
        ).hexdigest()
        
        headers = {
            "X-ANET-Signature": f"sha512={signature}",
            "Content-Type": "application/json"
        }
        
        response = await client.post(
            "/api/v1/webhooks/authorize-net",
            json=webhook_data,
            headers=headers
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["status"] == "success"
        assert result["message"] == "Webhook processed successfully"
        
        # Test invalid signature
        invalid_headers = {
            "X-ANET-Signature": "sha512=invalid_signature",
            "Content-Type": "application/json"
        }
        
        response = await client.post(
            "/api/v1/webhooks/authorize-net",
            json=webhook_data,
            headers=invalid_headers
        )
        assert response.status_code == 401
        
        error_data = response.json()
        assert "invalid signature" in error_data["detail"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_webhook_replay_e2e(self, client):
        """Test webhook replay functionality."""
        # Test webhook replay endpoint
        replay_data = {
            "webhook_id": "webhook_replay_123",
            "event_type": "payment.created",
            "payload": {
                "payment_id": "pay_replay_123",
                "amount": "35.00",
                "currency": "USD",
                "status": "pending"
            }
        }
        
        response = await client.post("/api/v1/webhooks/replay", json=replay_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["status"] == "success"
        assert result["message"] == "Webhook replayed successfully"


class TestPerformanceE2E:
    """End-to-end performance tests."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "E2E Performance Test Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_concurrent_payment_creation_e2e(self, authenticated_client):
        """Test concurrent payment creation performance."""
        import time
        
        # Create multiple payment requests
        payment_requests = []
        for i in range(50):  # Reduced for E2E testing
            payment_data = {
                "amount": f"{10 + (i % 10)}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_perf_{i}",
                "customer_email": f"perf{i}@example.com",
                "customer_name": f"Performance Test Customer {i}",
                "card_token": f"tok_perf_{i}",
                "description": f"Performance test payment {i}",
                "is_test": True
            }
            payment_requests.append(payment_data)
        
        # Measure concurrent creation time
        start_time = time.time()
        
        tasks = []
        for payment_data in payment_requests:
            task = authenticated_client.post("/api/v1/payments", json=payment_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify performance
        assert end_time - start_time < 30.0  # Should complete within 30 seconds
        
        # Verify all payments were created successfully
        successful_responses = [r for r in responses if r.status_code == 201]
        assert len(successful_responses) == 50
        
        # Verify payment data
        for response in successful_responses:
            payment = response.json()["data"]
            assert payment["status"] == "pending"
            assert payment["is_test"] is True
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_api_response_times_e2e(self, authenticated_client):
        """Test API response times."""
        import time
        
        # Test health endpoint response time
        start_time = time.time()
        response = await authenticated_client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second
        
        # Test payment creation response time
        payment_data = {
            "amount": "15.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_response_time_123",
            "customer_email": "responsetime@example.com",
            "customer_name": "Response Time Test Customer",
            "card_token": "tok_response_time_123",
            "description": "Response time test payment",
            "is_test": True
        }
        
        start_time = time.time()
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert end_time - start_time < 2.0  # Should respond within 2 seconds
        
        # Test payment retrieval response time
        payment_id = response.json()["data"]["id"]
        
        start_time = time.time()
        response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
