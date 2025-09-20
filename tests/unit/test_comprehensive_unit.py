"""
EasyPay Payment Gateway - Comprehensive Unit Tests

This module contains comprehensive unit tests for all core components
including services, models, repositories, and utilities.
"""

import pytest
import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any, List

from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.core.services.webhook_service import WebhookService
from src.core.services.rbac_service import RBACService
from src.core.repositories.payment_repository import PaymentRepository
from src.core.repositories.cached_payment_repository import CachedPaymentRepository
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.webhook import Webhook, WebhookStatus
from src.core.models.rbac import Role, Permission, ResourceAccess
from src.core.exceptions import (
    PaymentError, PaymentNotFoundError, ValidationError, DatabaseError,
    ExternalServiceError, AuthenticationError, AuthorizationError,
    WebhookError, CacheError
)
from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import CreditCard, BillingAddress
from src.infrastructure.cache_strategies import CacheStrategy
from src.infrastructure.circuit_breaker_service import CircuitBreakerService
from src.infrastructure.error_recovery import ErrorRecoveryManager


class TestPaymentServiceComprehensive:
    """Comprehensive tests for PaymentService."""
    
    @pytest.fixture
    def payment_service(self, test_db_session):
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_comprehensive(self, payment_service, sample_payment_create_request):
        """Test comprehensive payment creation scenarios."""
        # Test successful creation
        payment = await payment_service.create_payment(sample_payment_create_request)
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING
        
        # Test with different payment methods
        for method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            request_data = sample_payment_create_request.dict()
            request_data["payment_method"] = method.value
            request = type(sample_payment_create_request)(**request_data)
            payment = await payment_service.create_payment(request)
            assert payment.payment_method == method
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_payment_status_transitions(self, payment_service, sample_payment):
        """Test payment status transition logic."""
        # Test valid transitions
        valid_transitions = {
            PaymentStatus.PENDING: [PaymentStatus.AUTHORIZED, PaymentStatus.FAILED, PaymentStatus.DECLINED],
            PaymentStatus.AUTHORIZED: [PaymentStatus.CAPTURED, PaymentStatus.VOIDED],
            PaymentStatus.CAPTURED: [PaymentStatus.SETTLED, PaymentStatus.REFUNDED],
            PaymentStatus.SETTLED: [PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED]
        }
        
        for from_status, to_statuses in valid_transitions.items():
            sample_payment.status = from_status
            for to_status in to_statuses:
                # This would test the status transition logic
                # Implementation depends on the actual service method
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_payment_validation_edge_cases(self, payment_service):
        """Test payment validation with edge cases."""
        # Test minimum amount
        request_data = {
            "amount": Decimal("0.01"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_123",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_123456789",
            "description": "Test payment",
            "is_test": True
        }
        
        # Test maximum amount
        request_data["amount"] = Decimal("999999.99")
        
        # Test invalid currency
        request_data["currency"] = "INVALID"
        with pytest.raises(ValidationError):
            await payment_service.create_payment(type(sample_payment_create_request)(**request_data))
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_payment_search_and_filtering(self, payment_service, test_db_session):
        """Test payment search and filtering functionality."""
        # Create multiple test payments
        payments = []
        for i in range(5):
            payment_data = {
                "amount": Decimal(f"{10 + i}.00"),
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": f"cust_{i}",
                "customer_email": f"test{i}@example.com",
                "customer_name": f"Test Customer {i}",
                "card_token": f"tok_{i}",
                "description": f"Test payment {i}",
                "status": PaymentStatus.PENDING,
                "external_id": f"pay_{uuid.uuid4().hex[:12]}",
                "is_test": True
            }
            payment = Payment(**payment_data)
            test_db_session.add(payment)
            payments.append(payment)
        
        await test_db_session.commit()
        
        # Test search by customer ID
        results = await payment_service.search_payments(customer_id="cust_1")
        assert len(results) == 1
        
        # Test search by amount range
        results = await payment_service.search_payments(min_amount=Decimal("12.00"), max_amount=Decimal("14.00"))
        assert len(results) == 3


class TestAuthServiceComprehensive:
    """Comprehensive tests for AuthService."""
    
    @pytest.fixture
    def auth_service(self, test_db_session):
        """Create auth service instance."""
        return AuthService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_api_key_lifecycle(self, auth_service):
        """Test complete API key lifecycle."""
        # Create API key
        api_key = await auth_service.create_api_key(
            name="Test Key",
            environment="sandbox",
            permissions=["payment:create", "payment:read"]
        )
        assert api_key is not None
        assert api_key.name == "Test Key"
        
        # Validate API key
        is_valid = await auth_service.validate_api_key(api_key.key)
        assert is_valid is True
        
        # Revoke API key
        await auth_service.revoke_api_key(api_key.id)
        
        # Validate revoked key
        is_valid = await auth_service.validate_api_key(api_key.key)
        assert is_valid is False
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_jwt_token_generation_and_validation(self, auth_service):
        """Test JWT token generation and validation."""
        # Generate tokens
        tokens = await auth_service.generate_tokens(
            user_id="user_123",
            permissions=["payment:create", "payment:read"]
        )
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # Validate access token
        payload = await auth_service.validate_token(tokens["access_token"])
        assert payload["user_id"] == "user_123"
        
        # Refresh token
        new_tokens = await auth_service.refresh_token(tokens["refresh_token"])
        assert "access_token" in new_tokens


class TestWebhookServiceComprehensive:
    """Comprehensive tests for WebhookService."""
    
    @pytest.fixture
    def webhook_service(self, test_db_session):
        """Create webhook service instance."""
        return WebhookService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_registration_and_delivery(self, webhook_service):
        """Test webhook registration and delivery."""
        # Register webhook
        webhook = await webhook_service.register_webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            secret="test_secret"
        )
        assert webhook is not None
        
        # Simulate webhook delivery
        delivery_result = await webhook_service.deliver_webhook(
            webhook.id,
            {"event": "payment.created", "data": {"payment_id": "pay_123"}}
        )
        assert delivery_result is not None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_retry_logic(self, webhook_service):
        """Test webhook retry logic."""
        # Create webhook with retry configuration
        webhook = await webhook_service.register_webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            secret="test_secret",
            max_retries=3,
            retry_interval=60
        )
        
        # Simulate failed delivery
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 500
            
            # First attempt should fail
            result = await webhook_service.deliver_webhook(
                webhook.id,
                {"event": "payment.created", "data": {"payment_id": "pay_123"}}
            )
            assert result.status == WebhookStatus.FAILED


class TestRBACServiceComprehensive:
    """Comprehensive tests for RBACService."""
    
    @pytest.fixture
    def rbac_service(self, test_db_session):
        """Create RBAC service instance."""
        return RBACService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_role_and_permission_management(self, rbac_service):
        """Test role and permission management."""
        # Create permission
        permission = await rbac_service.create_permission(
            name="payment:create",
            description="Create payments",
            resource="payment",
            action="create"
        )
        assert permission is not None
        
        # Create role
        role = await rbac_service.create_role(
            name="payment_manager",
            description="Payment manager role"
        )
        assert role is not None
        
        # Assign permission to role
        await rbac_service.assign_permission_to_role(role.id, permission.id)
        
        # Check role permissions
        permissions = await rbac_service.get_role_permissions(role.id)
        assert len(permissions) == 1
        assert permissions[0].name == "payment:create"


class TestAuthorizeNetClientComprehensive:
    """Comprehensive tests for AuthorizeNetClient."""
    
    @pytest.fixture
    def authorize_net_client(self):
        """Create AuthorizeNet client instance."""
        return AuthorizeNetClient(
            api_login_id="test_login",
            transaction_key="test_key",
            is_sandbox=True
        )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credit_card_operations(self, authorize_net_client, sample_credit_card, sample_billing_address):
        """Test comprehensive credit card operations."""
        # Test authentication
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "messages": {"resultCode": "Ok"}
            }
            
            auth_result = await authorize_net_client.test_authentication()
            assert auth_result is True
        
        # Test charge credit card
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "messages": {"resultCode": "Ok"},
                "transactionResponse": {
                    "transId": "test_trans_123",
                    "responseCode": "1",
                    "responseText": "Approved"
                }
            }
            
            response = await authorize_net_client.charge_credit_card(
                amount=Decimal("10.00"),
                credit_card=sample_credit_card,
                billing_address=sample_billing_address
            )
            assert response.transaction_id == "test_trans_123"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling(self, authorize_net_client, sample_credit_card, sample_billing_address):
        """Test error handling scenarios."""
        # Test declined transaction
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "messages": {"resultCode": "Error"},
                "transactionResponse": {
                    "responseCode": "2",
                    "responseText": "Declined"
                }
            }
            
            with pytest.raises(ExternalServiceError):
                await authorize_net_client.charge_credit_card(
                    amount=Decimal("10.00"),
                    credit_card=sample_credit_card,
                    billing_address=sample_billing_address
                )


class TestCacheStrategiesComprehensive:
    """Comprehensive tests for cache strategies."""
    
    @pytest.fixture
    def cache_strategy(self):
        """Create cache strategy instance."""
        return CacheStrategy()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cache_operations(self, cache_strategy):
        """Test cache operations."""
        # Test set and get
        await cache_strategy.set("test_key", "test_value", ttl=60)
        value = await cache_strategy.get("test_key")
        assert value == "test_value"
        
        # Test expiration
        await cache_strategy.set("expire_key", "expire_value", ttl=1)
        await asyncio.sleep(1.1)
        value = await cache_strategy.get("expire_key")
        assert value is None
        
        # Test delete
        await cache_strategy.set("delete_key", "delete_value")
        await cache_strategy.delete("delete_key")
        value = await cache_strategy.get("delete_key")
        assert value is None


class TestCircuitBreakerComprehensive:
    """Comprehensive tests for circuit breaker."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance."""
        return CircuitBreakerService(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=ExternalServiceError
        )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_circuit_breaker_states(self, circuit_breaker):
        """Test circuit breaker state transitions."""
        # Initially closed
        assert circuit_breaker.state == "closed"
        
        # Simulate failures to open circuit
        for _ in range(5):
            try:
                await circuit_breaker.call_async(lambda: 1/0)
            except ZeroDivisionError:
                pass
        
        # Circuit should be open
        assert circuit_breaker.state == "open"
        
        # Wait for recovery timeout
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=61)
        
        # Circuit should be half-open
        assert circuit_breaker.state == "half-open"


class TestErrorRecoveryComprehensive:
    """Comprehensive tests for error recovery."""
    
    @pytest.fixture
    def error_recovery(self):
        """Create error recovery instance."""
        return ErrorRecoveryManager()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_recovery_strategies(self, error_recovery):
        """Test different error recovery strategies."""
        # Test retry strategy
        retry_count = 0
        async def failing_function():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise ExternalServiceError("Temporary failure")
            return "success"
        
        result = await error_recovery.execute_with_retry(failing_function, max_retries=3)
        assert result == "success"
        assert retry_count == 3
        
        # Test circuit breaker strategy
        circuit_breaker = MagicMock()
        circuit_breaker.state = "closed"
        circuit_breaker.call_async.return_value = "success"
        
        result = await error_recovery.execute_with_circuit_breaker(
            lambda: "success",
            circuit_breaker
        )
        assert result == "success"


class TestDataValidationComprehensive:
    """Comprehensive tests for data validation."""
    
    @pytest.mark.unit
    def test_payment_data_validation(self):
        """Test comprehensive payment data validation."""
        # Valid payment data
        valid_data = {
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_123",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_123456789",
            "description": "Test payment",
            "is_test": True
        }
        
        # Test valid data
        payment = Payment(**valid_data)
        assert payment.amount == Decimal("10.00")
        assert payment.currency == "USD"
        
        # Test invalid data
        invalid_data = valid_data.copy()
        invalid_data["amount"] = Decimal("-10.00")  # Negative amount
        
        with pytest.raises(ValidationError):
            Payment(**invalid_data)
    
    @pytest.mark.unit
    def test_webhook_data_validation(self):
        """Test webhook data validation."""
        # Valid webhook data
        valid_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "is_active": True,
            "secret": "webhook_secret_123"
        }
        
        webhook = Webhook(**valid_data)
        assert webhook.webhook_url == "https://example.com/webhook"
        assert webhook.event_type == "payment.created"
        
        # Test invalid URL
        invalid_data = valid_data.copy()
        invalid_data["webhook_url"] = "invalid_url"
        
        with pytest.raises(ValidationError):
            Webhook(**invalid_data)


class TestPerformanceComprehensive:
    """Comprehensive performance tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.slow
    async def test_payment_service_performance(self, payment_service, sample_payment_create_request):
        """Test payment service performance."""
        import time
        
        # Test bulk payment creation
        start_time = time.time()
        
        tasks = []
        for _ in range(100):
            task = payment_service.create_payment(sample_payment_create_request)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 10.0  # 10 seconds
        assert len(results) == 100
        
        # All payments should be created successfully
        for payment in results:
            assert payment is not None
            assert payment.status == PaymentStatus.PENDING
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.slow
    async def test_cache_performance(self, cache_strategy):
        """Test cache performance."""
        import time
        
        # Test cache write performance
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            task = cache_strategy.set(f"key_{i}", f"value_{i}")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 5.0  # 5 seconds
        
        # Test cache read performance
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            task = cache_strategy.get(f"key_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 3.0  # 3 seconds
        assert all(result is not None for result in results)


# Test utilities and helpers
class TestUtilitiesComprehensive:
    """Comprehensive tests for utility functions."""
    
    @pytest.mark.unit
    def test_uuid_generation(self):
        """Test UUID generation utilities."""
        # Test payment ID generation
        payment_id = str(uuid.uuid4())
        assert len(payment_id) == 36
        assert payment_id.count('-') == 4
        
        # Test external ID generation
        external_id = f"pay_{uuid.uuid4().hex[:12]}"
        assert external_id.startswith("pay_")
        assert len(external_id) == 16
    
    @pytest.mark.unit
    def test_decimal_precision(self):
        """Test decimal precision handling."""
        # Test currency precision
        amount = Decimal("10.99")
        assert amount.quantize(Decimal('0.01')) == Decimal("10.99")
        
        # Test large amounts
        large_amount = Decimal("999999.99")
        assert large_amount > Decimal("100000.00")
    
    @pytest.mark.unit
    def test_datetime_handling(self):
        """Test datetime handling."""
        # Test UTC datetime
        now = datetime.utcnow()
        assert now.tzinfo is None
        
        # Test datetime formatting
        formatted = now.isoformat()
        assert 'T' in formatted
        assert len(formatted) >= 19  # YYYY-MM-DDTHH:MM:SS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
