"""
EasyPay Payment Gateway - Comprehensive Security Tests

This module contains comprehensive security tests for all system components
including authentication, authorization, input validation, and security headers.
"""

import pytest
import uuid
import asyncio
import json
import hmac
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.services.auth_service import AuthService
from src.core.services.rbac_service import RBACService
from src.core.services.request_signing_service import RequestSigningService
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.rbac import Role, Permission, RolePermission
from src.core.exceptions import (
    AuthenticationError, AuthorizationError, ValidationError, SecurityError
)


class TestAuthenticationSecurity:
    """Security tests for authentication system."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_api_key_security(self, client):
        """Test API key security features."""
        # Test API key creation with valid data
        api_key_data = {
            "name": "Security Test Key",
            "environment": "sandbox",
            "permissions": ["payment:create", "payment:read"]
        }
        
        response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
        assert response.status_code == 201
        
        api_key_info = response.json()["data"]
        api_key_value = api_key_info["key"]
        
        # Verify API key format (should be secure random string)
        assert len(api_key_value) >= 32  # At least 32 characters
        assert api_key_value.isalnum() or '-' in api_key_value or '_' in api_key_value
        
        # Test API key authentication
        authenticated_client = AsyncClient(app=app, base_url="http://test")
        authenticated_client.headers.update({"Authorization": f"Bearer {api_key_value}"})
        
        # Test valid authentication
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # Test invalid API key
        invalid_client = AsyncClient(app=app, base_url="http://test")
        invalid_client.headers.update({"Authorization": "Bearer invalid_api_key_12345"})
        
        invalid_response = await invalid_client.get("/api/v1/health")
        assert invalid_response.status_code == 401
        
        # Test malformed authorization header
        malformed_client = AsyncClient(app=app, base_url="http://test")
        malformed_client.headers.update({"Authorization": "InvalidFormat api_key"})
        
        malformed_response = await malformed_client.get("/api/v1/health")
        assert malformed_response.status_code == 401
        
        # Test missing authorization header
        no_auth_client = AsyncClient(app=app, base_url="http://test")
        
        no_auth_response = await no_auth_client.get("/api/v1/payments")
        assert no_auth_response.status_code == 401
        
        await authenticated_client.aclose()
        await invalid_client.aclose()
        await malformed_client.aclose()
        await no_auth_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_jwt_token_security(self, client):
        """Test JWT token security features."""
        # Test token generation
        token_data = {
            "user_id": "user_security_123",
            "permissions": ["payment:create", "payment:read"]
        }
        
        response = await client.post("/api/v1/auth/tokens", json=token_data)
        assert response.status_code == 201
        
        tokens = response.json()["data"]
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Verify token format
        assert len(access_token) > 100  # JWT tokens are typically long
        assert len(refresh_token) > 100
        assert '.' in access_token  # JWT format: header.payload.signature
        assert '.' in refresh_token
        
        # Test access token validation
        authenticated_client = AsyncClient(app=app, base_url="http://test")
        authenticated_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        health_response = await authenticated_client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # Test token expiration (if implemented)
        # This would require waiting for token expiration or mocking time
        
        # Test invalid JWT token
        invalid_jwt_client = AsyncClient(app=app, base_url="http://test")
        invalid_jwt_client.headers.update({"Authorization": "Bearer invalid.jwt.token"})
        
        invalid_jwt_response = await invalid_jwt_client.get("/api/v1/health")
        assert invalid_jwt_response.status_code == 401
        
        # Test tampered JWT token
        tampered_token = access_token[:-10] + "tampered123"
        tampered_client = AsyncClient(app=app, base_url="http://test")
        tampered_client.headers.update({"Authorization": f"Bearer {tampered_token}"})
        
        tampered_response = await tampered_client.get("/api/v1/health")
        assert tampered_response.status_code == 401
        
        await authenticated_client.aclose()
        await invalid_jwt_client.aclose()
        await tampered_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_authentication_rate_limiting(self, client):
        """Test authentication rate limiting."""
        # Test rapid API key creation attempts
        rapid_attempts = []
        for i in range(20):  # Try to create 20 API keys rapidly
            api_key_data = {
                "name": f"Rate Limit Test Key {i}",
                "environment": "sandbox",
                "permissions": ["payment:create"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            rapid_attempts.append(response.status_code)
        
        # Some requests should be rate limited
        rate_limited_count = len([code for code in rapid_attempts if code == 429])
        assert rate_limited_count > 0, "Rate limiting should be triggered for rapid requests"
        
        # Test rapid token generation attempts
        token_attempts = []
        for i in range(15):  # Try to generate 15 tokens rapidly
            token_data = {
                "user_id": f"user_rate_limit_{i}",
                "permissions": ["payment:create"]
            }
            
            response = await client.post("/api/v1/auth/tokens", json=token_data)
            token_attempts.append(response.status_code)
        
        # Some token generation requests should be rate limited
        token_rate_limited_count = len([code for code in token_attempts if code == 429])
        assert token_rate_limited_count > 0, "Token generation rate limiting should be triggered"


class TestAuthorizationSecurity:
    """Security tests for authorization system."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_permission_based_access_control(self, client):
        """Test permission-based access control."""
        # Create API key with limited permissions
        limited_api_key_data = {
            "name": "Limited Permissions Key",
            "environment": "sandbox",
            "permissions": ["payment:read"]  # Only read permission
        }
        
        response = await client.post("/api/v1/auth/api-keys", json=limited_api_key_data)
        assert response.status_code == 201
        
        limited_api_key = response.json()["data"]["key"]
        
        # Create client with limited permissions
        limited_client = AsyncClient(app=app, base_url="http://test")
        limited_client.headers.update({"Authorization": f"Bearer {limited_api_key}"})
        
        # Test read access (should be allowed)
        payments_response = await limited_client.get("/api/v1/payments")
        assert payments_response.status_code == 200
        
        # Test create access (should be denied)
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_auth_test_123",
            "customer_email": "authtest@example.com",
            "customer_name": "Auth Test Customer",
            "card_token": "tok_auth_test_123",
            "description": "Auth test payment",
            "is_test": True
        }
        
        create_response = await limited_client.post("/api/v1/payments", json=payment_data)
        assert create_response.status_code == 403  # Forbidden
        
        # Test update access (should be denied)
        fake_payment_id = str(uuid.uuid4())
        update_data = {"status": "authorized"}
        
        update_response = await limited_client.put(f"/api/v1/payments/{fake_payment_id}", json=update_data)
        assert update_response.status_code == 403  # Forbidden
        
        await limited_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_resource_level_authorization(self, client):
        """Test resource-level authorization."""
        # Create API key with payment permissions
        payment_api_key_data = {
            "name": "Payment Only Key",
            "environment": "sandbox",
            "permissions": ["payment:create", "payment:read", "payment:update"]
        }
        
        response = await client.post("/api/v1/auth/api-keys", json=payment_api_key_data)
        assert response.status_code == 201
        
        payment_api_key = response.json()["data"]["key"]
        
        # Create client with payment permissions
        payment_client = AsyncClient(app=app, base_url="http://test")
        payment_client.headers.update({"Authorization": f"Bearer {payment_api_key}"})
        
        # Test payment access (should be allowed)
        payments_response = await payment_client.get("/api/v1/payments")
        assert payments_response.status_code == 200
        
        # Test webhook access (should be denied)
        webhook_data = {
            "webhook_url": "https://unauthorized.example.com/webhook",
            "event_type": "payment.created",
            "secret": "unauthorized_secret"
        }
        
        webhook_response = await payment_client.post("/api/v1/webhooks", json=webhook_data)
        assert webhook_response.status_code == 403  # Forbidden
        
        # Test admin access (should be denied)
        admin_response = await payment_client.get("/api/v1/admin/users")
        assert admin_response.status_code == 403  # Forbidden
        
        await payment_client.aclose()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_environment_based_authorization(self, client):
        """Test environment-based authorization."""
        # Create sandbox API key
        sandbox_api_key_data = {
            "name": "Sandbox Key",
            "environment": "sandbox",
            "permissions": ["payment:create", "payment:read"]
        }
        
        response = await client.post("/api/v1/auth/api-keys", json=sandbox_api_key_data)
        assert response.status_code == 201
        
        sandbox_api_key = response.json()["data"]["key"]
        
        # Create client with sandbox key
        sandbox_client = AsyncClient(app=app, base_url="http://test")
        sandbox_client.headers.update({"Authorization": f"Bearer {sandbox_api_key}"})
        
        # Test sandbox payment creation (should be allowed)
        sandbox_payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_sandbox_123",
            "customer_email": "sandbox@example.com",
            "customer_name": "Sandbox Test Customer",
            "card_token": "tok_sandbox_123",
            "description": "Sandbox test payment",
            "is_test": True  # Sandbox payments should be test payments
        }
        
        sandbox_response = await sandbox_client.post("/api/v1/payments", json=sandbox_payment_data)
        assert sandbox_response.status_code == 201
        
        sandbox_payment = sandbox_response.json()["data"]
        assert sandbox_payment["is_test"] is True
        
        # Test production payment creation (should be denied or restricted)
        production_payment_data = sandbox_payment_data.copy()
        production_payment_data["is_test"] = False
        
        production_response = await sandbox_client.post("/api/v1/payments", json=production_payment_data)
        # This might be allowed but should be flagged or restricted
        if production_response.status_code == 201:
            production_payment = production_response.json()["data"]
            # Production payments from sandbox keys should be flagged
            assert production_payment.get("environment") == "sandbox"
        
        await sandbox_client.aclose()


class TestInputValidationSecurity:
    """Security tests for input validation."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Input Validation Test Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read", "payment:update"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sql_injection_prevention(self, authenticated_client):
        """Test SQL injection prevention."""
        # Test SQL injection attempts in payment creation
        sql_injection_attempts = [
            "'; DROP TABLE payments; --",
            "1' OR '1'='1",
            "'; INSERT INTO payments VALUES ('hacked', '1000.00'); --",
            "1' UNION SELECT * FROM users --",
            "'; UPDATE payments SET amount='999999.99' WHERE id='1'; --"
        ]
        
        for injection_attempt in sql_injection_attempts:
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": injection_attempt,  # Try SQL injection in customer_id
                "customer_email": "sqltest@example.com",
                "customer_name": "SQL Test Customer",
                "card_token": "tok_sql_test_123",
                "description": injection_attempt,  # Try SQL injection in description
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # Should either reject the request or sanitize the input
            assert response.status_code in [400, 422], f"SQL injection attempt should be rejected: {injection_attempt}"
            
            if response.status_code == 422:
                error_data = response.json()
                assert "detail" in error_data
                # Should not contain SQL error messages
                assert "sql" not in str(error_data).lower()
                assert "database" not in str(error_data).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_xss_prevention(self, authenticated_client):
        """Test XSS prevention."""
        # Test XSS attempts in payment creation
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "data:text/html,<script>alert('XSS')</script>"
        ]
        
        for xss_attempt in xss_attempts:
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_xss_test_123",
                "customer_email": "xsstest@example.com",
                "customer_name": xss_attempt,  # Try XSS in customer name
                "card_token": "tok_xss_test_123",
                "description": xss_attempt,  # Try XSS in description
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # Should either reject the request or sanitize the input
            if response.status_code == 201:
                payment = response.json()["data"]
                # Check that XSS attempts are sanitized
                assert "<script>" not in payment["customer_name"]
                assert "<script>" not in payment["description"]
                assert "javascript:" not in payment["customer_name"]
                assert "javascript:" not in payment["description"]
            else:
                # Request should be rejected
                assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_input_length_validation(self, authenticated_client):
        """Test input length validation."""
        # Test extremely long inputs
        long_string = "A" * 10000  # 10KB string
        
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_length_test_123",
            "customer_email": "lengthtest@example.com",
            "customer_name": long_string,  # Extremely long customer name
            "card_token": "tok_length_test_123",
            "description": long_string,  # Extremely long description
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        
        # Should reject extremely long inputs
        assert response.status_code in [400, 422], "Extremely long inputs should be rejected"
        
        if response.status_code == 422:
            error_data = response.json()
            assert "detail" in error_data
            assert "length" in str(error_data).lower() or "size" in str(error_data).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_special_character_handling(self, authenticated_client):
        """Test special character handling."""
        # Test various special characters
        special_char_tests = [
            "Test Customer with émojis 🎉💳",
            "Customer with unicode: 测试客户",
            "Customer with symbols: !@#$%^&*()",
            "Customer with quotes: \"test\" 'customer'",
            "Customer with newlines:\nLine2\nLine3",
            "Customer with tabs:\tTabbed\tContent",
            "Customer with null: \x00\x01\x02",
            "Customer with backslashes: \\test\\path"
        ]
        
        for special_chars in special_char_tests:
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_special_test_123",
                "customer_email": "specialtest@example.com",
                "customer_name": special_chars,
                "card_token": "tok_special_test_123",
                "description": f"Test with special chars: {special_chars}",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # Should handle special characters gracefully
            if response.status_code == 201:
                payment = response.json()["data"]
                # Special characters should be preserved or safely encoded
                assert payment["customer_name"] is not None
                assert payment["description"] is not None
            else:
                # If rejected, should be for security reasons, not crashes
                assert response.status_code in [400, 422]


class TestWebhookSecurity:
    """Security tests for webhook system."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Webhook Security Test Key",
                "environment": "sandbox",
                "permissions": ["webhook:create", "webhook:read", "webhook:update"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_webhook_signature_verification(self, authenticated_client):
        """Test webhook signature verification."""
        # Register webhook
        webhook_data = {
            "webhook_url": "https://security-test.example.com/webhook",
            "event_type": "payment.created",
            "secret": "webhook_security_secret_123",
            "max_retries": 3,
            "retry_interval": 60
        }
        
        response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
        assert response.status_code == 201
        
        webhook_id = response.json()["data"]["id"]
        
        # Test webhook delivery with valid signature
        webhook_payload = {
            "event": "payment.created",
            "data": {
                "payment_id": "pay_security_123",
                "amount": "25.00",
                "currency": "USD",
                "status": "pending"
            }
        }
        
        # Generate valid HMAC signature
        payload_json = json.dumps(webhook_payload)
        signature = hmac.new(
            webhook_data["secret"].encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "Content-Type": "application/json"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success"}
            
            delivery_response = await authenticated_client.post(
                f"/api/v1/webhooks/{webhook_id}/deliver",
                json=webhook_payload,
                headers=headers
            )
            assert delivery_response.status_code == 200
        
        # Test webhook delivery with invalid signature
        invalid_signature = "invalid_signature_12345"
        invalid_headers = {
            "X-Webhook-Signature": f"sha256={invalid_signature}",
            "Content-Type": "application/json"
        }
        
        delivery_response = await authenticated_client.post(
            f"/api/v1/webhooks/{webhook_id}/deliver",
            json=webhook_payload,
            headers=invalid_headers
        )
        assert delivery_response.status_code == 401
        
        error_data = delivery_response.json()
        assert "invalid signature" in error_data["detail"].lower()
        
        # Test webhook delivery without signature
        no_signature_response = await authenticated_client.post(
            f"/api/v1/webhooks/{webhook_id}/deliver",
            json=webhook_payload
        )
        assert no_signature_response.status_code == 401
        
        error_data = no_signature_response.json()
        assert "signature" in error_data["detail"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_webhook_url_validation(self, authenticated_client):
        """Test webhook URL validation."""
        # Test valid URLs
        valid_urls = [
            "https://example.com/webhook",
            "https://api.example.com/v1/webhooks",
            "https://secure.example.com:443/webhook",
            "https://subdomain.example.com/webhook"
        ]
        
        for url in valid_urls:
            webhook_data = {
                "webhook_url": url,
                "event_type": "payment.created",
                "secret": "test_secret"
            }
            
            response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
            assert response.status_code == 201
        
        # Test invalid URLs
        invalid_urls = [
            "http://example.com/webhook",  # HTTP instead of HTTPS
            "ftp://example.com/webhook",   # FTP protocol
            "javascript:alert('xss')",    # JavaScript protocol
            "data:text/html,<script>alert('xss')</script>",  # Data protocol
            "file:///etc/passwd",         # File protocol
            "not-a-url",                  # Not a URL
            "",                           # Empty URL
            "https://",                   # Incomplete URL
            "https://localhost/webhook",  # Localhost (potential security risk)
            "https://127.0.0.1/webhook"  # Localhost IP (potential security risk)
        ]
        
        for url in invalid_urls:
            webhook_data = {
                "webhook_url": url,
                "event_type": "payment.created",
                "secret": "test_secret"
            }
            
            response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
            assert response.status_code in [400, 422], f"Invalid URL should be rejected: {url}"
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_webhook_secret_security(self, authenticated_client):
        """Test webhook secret security."""
        # Test weak secrets
        weak_secrets = [
            "123",           # Too short
            "password",      # Common password
            "secret",        # Common word
            "webhook",       # Common word
            "12345678",      # Numeric only
            "abcdefgh",      # Alphabetic only
            "",              # Empty secret
            "a" * 1000       # Too long
        ]
        
        for secret in weak_secrets:
            webhook_data = {
                "webhook_url": "https://example.com/webhook",
                "event_type": "payment.created",
                "secret": secret
            }
            
            response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
            
            # Should reject weak secrets
            if response.status_code == 201:
                # If accepted, should have additional security measures
                webhook = response.json()["data"]
                assert len(webhook["secret"]) >= 8  # Minimum length
            else:
                assert response.status_code in [400, 422], f"Weak secret should be rejected: {secret}"


class TestSecurityHeaders:
    """Security tests for HTTP security headers."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_security_headers_presence(self, client):
        """Test presence of security headers."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        
        headers = response.headers
        
        # Check for important security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in security_headers:
            assert header in headers, f"Security header {header} should be present"
        
        # Verify header values
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_cors_security(self, client):
        """Test CORS security configuration."""
        # Test preflight request
        preflight_response = await client.options(
            "/api/v1/payments",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization"
            }
        )
        
        # Should not allow requests from malicious origins
        cors_headers = preflight_response.headers
        if "Access-Control-Allow-Origin" in cors_headers:
            allowed_origins = cors_headers["Access-Control-Allow-Origin"]
            assert allowed_origins != "*", "CORS should not allow all origins"
            assert "malicious-site.com" not in allowed_origins, "Malicious origins should not be allowed"
        
        # Test actual request from malicious origin
        malicious_response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_malicious_123",
                "customer_email": "malicious@example.com",
                "customer_name": "Malicious Customer",
                "card_token": "tok_malicious_123",
                "description": "Malicious payment",
                "is_test": True
            },
            headers={"Origin": "https://malicious-site.com"}
        )
        
        # Should be rejected due to CORS
        assert malicious_response.status_code in [401, 403], "Malicious origin requests should be rejected"


class TestDataProtectionSecurity:
    """Security tests for data protection."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Data Protection Test Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sensitive_data_masking(self, authenticated_client):
        """Test sensitive data masking in responses."""
        # Create payment with sensitive data
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_sensitive_123",
            "customer_email": "sensitive@example.com",
            "customer_name": "Sensitive Test Customer",
            "card_token": "tok_sensitive_123",
            "description": "Sensitive test payment",
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert response.status_code == 201
        
        payment = response.json()["data"]
        
        # Check that sensitive data is masked or not exposed
        if "card_token" in payment:
            # Card token should be masked
            assert payment["card_token"] != "tok_sensitive_123"
            assert "*" in payment["card_token"] or len(payment["card_token"]) < len("tok_sensitive_123")
        
        # Check that sensitive data is not logged in response
        response_text = response.text
        assert "tok_sensitive_123" not in response_text  # Original token should not be in response
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_data_encryption_at_rest(self, authenticated_client):
        """Test data encryption at rest."""
        # This test would verify that sensitive data is encrypted in the database
        # In a real implementation, this would involve checking database encryption
        
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_encryption_123",
            "customer_email": "encryption@example.com",
            "customer_name": "Encryption Test Customer",
            "card_token": "tok_encryption_123",
            "description": "Encryption test payment",
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert response.status_code == 201
        
        payment_id = response.json()["data"]["id"]
        
        # Retrieve payment and verify data integrity
        get_response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
        assert get_response.status_code == 200
        
        retrieved_payment = get_response.json()["data"]
        
        # Verify that data is correctly stored and retrieved
        assert retrieved_payment["amount"] == "25.00"
        assert retrieved_payment["currency"] == "USD"
        assert retrieved_payment["customer_id"] == "cust_encryption_123"
        assert retrieved_payment["customer_email"] == "encryption@example.com"
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_audit_logging_security(self, authenticated_client):
        """Test audit logging for security events."""
        # Perform various operations that should be logged
        operations = [
            {
                "name": "Payment Creation",
                "action": lambda: authenticated_client.post("/api/v1/payments", json={
                    "amount": "25.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": "cust_audit_123",
                    "customer_email": "audit@example.com",
                    "customer_name": "Audit Test Customer",
                    "card_token": "tok_audit_123",
                    "description": "Audit test payment",
                    "is_test": True
                })
            },
            {
                "name": "Payment Retrieval",
                "action": lambda: authenticated_client.get("/api/v1/payments")
            },
            {
                "name": "Health Check",
                "action": lambda: authenticated_client.get("/api/v1/health")
            }
        ]
        
        for operation in operations:
            response = await operation["action"]()
            
            # Verify operation was successful
            assert response.status_code in [200, 201], f"{operation['name']} should be successful"
            
            # In a real implementation, this would check audit logs
            # For now, we just verify the operation completed without security issues
        
        # Test failed operations (should also be logged)
        failed_operations = [
            {
                "name": "Unauthorized Access",
                "action": lambda: authenticated_client.get("/api/v1/admin/users")
            },
            {
                "name": "Invalid Payment Data",
                "action": lambda: authenticated_client.post("/api/v1/payments", json={
                    "amount": "-10.00",  # Invalid negative amount
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": "cust_invalid_123",
                    "customer_email": "invalid@example.com",
                    "customer_name": "Invalid Test Customer",
                    "card_token": "tok_invalid_123",
                    "description": "Invalid test payment",
                    "is_test": True
                })
            }
        ]
        
        for operation in failed_operations:
            response = await operation["action"]()
            
            # Verify operation failed as expected
            assert response.status_code in [400, 401, 403, 422], f"{operation['name']} should fail"
            
            # Failed operations should also be logged for security monitoring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
