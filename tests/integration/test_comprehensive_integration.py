"""
EasyPay Payment Gateway - Comprehensive Integration Tests

This module contains comprehensive integration tests that test the interaction
between different components of the system.
"""

import pytest
import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.core.services.webhook_service import WebhookService
from src.core.repositories.payment_repository import PaymentRepository
from src.core.repositories.cached_payment_repository import CachedPaymentRepository
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.webhook import Webhook, WebhookStatus
from src.core.exceptions import (
    PaymentError, PaymentNotFoundError, ValidationError, DatabaseError,
    ExternalServiceError, AuthenticationError, AuthorizationError,
    WebhookError, CacheError
)
from src.integrations.authorize_net.client import AuthorizeNetClient
from src.infrastructure.cache_strategies import CacheStrategy
from src.infrastructure.database import get_db_session


class TestPaymentServiceIntegration:
    """Integration tests for PaymentService with database and external services."""
    
    @pytest.fixture
    async def payment_service_with_db(self, test_db_session):
        """Create payment service with database session."""
        return PaymentService(test_db_session)
    
    @pytest.fixture
    async def payment_repository(self, test_db_session):
        """Create payment repository with database session."""
        return PaymentRepository(test_db_session)
    
    @pytest.fixture
    async def cached_payment_repository(self, test_db_session, mock_cache_client):
        """Create cached payment repository."""
        return CachedPaymentRepository(test_db_session, mock_cache_client)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_payment_lifecycle_integration(self, payment_service_with_db, test_db_session):
        """Test complete payment lifecycle with database integration."""
        # Create payment
        payment_data = {
            "amount": Decimal("25.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_integration_123",
            "customer_email": "integration@example.com",
            "customer_name": "Integration Test Customer",
            "card_token": "tok_integration_123",
            "description": "Integration test payment",
            "metadata": {"test_type": "integration"},
            "is_test": True
        }
        
        payment = await payment_service_with_db.create_payment(
            type(sample_payment_create_request)(**payment_data)
        )
        
        # Verify payment was created in database
        db_payment = await test_db_session.get(Payment, payment.id)
        assert db_payment is not None
        assert db_payment.amount == Decimal("25.00")
        assert db_payment.status == PaymentStatus.PENDING
        
        # Update payment status
        await payment_service_with_db.update_payment_status(
            payment.id, PaymentStatus.AUTHORIZED
        )
        
        # Verify status update in database
        await test_db_session.refresh(db_payment)
        assert db_payment.status == PaymentStatus.AUTHORIZED
        
        # Process refund
        refund_request = PaymentRefundRequest(
            amount=Decimal("10.00"),
            reason="Partial refund for integration test",
            metadata={"refund_type": "partial"}
        )
        
        refund_result = await payment_service_with_db.refund_payment(
            payment.id, refund_request
        )
        
        # Verify refund was processed
        assert refund_result is not None
        await test_db_session.refresh(db_payment)
        assert db_payment.status == PaymentStatus.PARTIALLY_REFUNDED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_payment_repository_integration(self, payment_repository, test_db_session):
        """Test payment repository with database integration."""
        # Create multiple payments
        payments = []
        for i in range(5):
            payment_data = {
                "amount": Decimal(f"{10 + i}.00"),
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": f"cust_repo_{i}",
                "customer_email": f"repo{i}@example.com",
                "customer_name": f"Repo Test Customer {i}",
                "card_token": f"tok_repo_{i}",
                "description": f"Repository test payment {i}",
                "status": PaymentStatus.PENDING,
                "external_id": f"pay_repo_{uuid.uuid4().hex[:12]}",
                "is_test": True
            }
            payment = Payment(**payment_data)
            test_db_session.add(payment)
            payments.append(payment)
        
        await test_db_session.commit()
        
        # Test repository methods
        # Get payment by ID
        retrieved_payment = await payment_repository.get_by_id(payments[0].id)
        assert retrieved_payment is not None
        assert retrieved_payment.customer_id == "cust_repo_0"
        
        # Get payments by customer
        customer_payments = await payment_repository.get_by_customer_id("cust_repo_1")
        assert len(customer_payments) == 1
        assert customer_payments[0].customer_id == "cust_repo_1"
        
        # Search payments
        search_results = await payment_repository.search_payments(
            min_amount=Decimal("12.00"),
            max_amount=Decimal("14.00")
        )
        assert len(search_results) == 3  # payments with amounts 12, 13, 14
        
        # Update payment
        await payment_repository.update_status(payments[0].id, PaymentStatus.AUTHORIZED)
        await test_db_session.refresh(payments[0])
        assert payments[0].status == PaymentStatus.AUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cached_repository_integration(self, cached_payment_repository, test_db_session, mock_cache_client):
        """Test cached payment repository integration."""
        # Create payment
        payment_data = {
            "amount": Decimal("30.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_cache_123",
            "customer_email": "cache@example.com",
            "customer_name": "Cache Test Customer",
            "card_token": "tok_cache_123",
            "description": "Cache test payment",
            "status": PaymentStatus.PENDING,
            "external_id": f"pay_cache_{uuid.uuid4().hex[:12]}",
            "is_test": True
        }
        payment = Payment(**payment_data)
        test_db_session.add(payment)
        await test_db_session.commit()
        
        # Test cache miss (first access)
        retrieved_payment = await cached_payment_repository.get_by_id(payment.id)
        assert retrieved_payment is not None
        assert retrieved_payment.amount == Decimal("30.00")
        
        # Verify cache was set
        mock_cache_client.set.assert_called()
        
        # Test cache hit (second access)
        retrieved_payment_2 = await cached_payment_repository.get_by_id(payment.id)
        assert retrieved_payment_2 is not None
        assert retrieved_payment_2.amount == Decimal("30.00")
        
        # Verify cache was accessed
        mock_cache_client.get.assert_called()


class TestAuthServiceIntegration:
    """Integration tests for AuthService with database."""
    
    @pytest.fixture
    async def auth_service_with_db(self, test_db_session):
        """Create auth service with database session."""
        return AuthService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_api_key_lifecycle_integration(self, auth_service_with_db, test_db_session):
        """Test complete API key lifecycle with database integration."""
        # Create API key
        api_key = await auth_service_with_db.create_api_key(
            name="Integration Test Key",
            environment="sandbox",
            permissions=["payment:create", "payment:read", "payment:update"]
        )
        
        # Verify API key was created in database
        db_api_key = await test_db_session.get(APIKey, api_key.id)
        assert db_api_key is not None
        assert db_api_key.name == "Integration Test Key"
        assert db_api_key.environment == "sandbox"
        
        # Validate API key
        validation_result = await auth_service_with_db.validate_api_key(api_key.key)
        assert validation_result is True
        
        # Update API key permissions
        await auth_service_with_db.update_api_key_permissions(
            api_key.id,
            ["payment:create", "payment:read"]  # Remove update permission
        )
        
        # Verify permission update
        await test_db_session.refresh(db_api_key)
        permissions = await auth_service_with_db.get_api_key_permissions(api_key.id)
        assert len(permissions) == 2
        assert "payment:create" in permissions
        assert "payment:update" not in permissions
        
        # Revoke API key
        await auth_service_with_db.revoke_api_key(api_key.id)
        
        # Verify revocation
        await test_db_session.refresh(db_api_key)
        assert db_api_key.is_active is False
        
        # Validate revoked key
        validation_result = await auth_service_with_db.validate_api_key(api_key.key)
        assert validation_result is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_jwt_token_integration(self, auth_service_with_db, test_db_session):
        """Test JWT token generation and validation with database integration."""
        # Generate tokens
        tokens = await auth_service_with_db.generate_tokens(
            user_id="user_integration_123",
            permissions=["payment:create", "payment:read"]
        )
        
        # Verify tokens were created
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # Validate access token
        payload = await auth_service_with_db.validate_token(tokens["access_token"])
        assert payload["user_id"] == "user_integration_123"
        assert "payment:create" in payload["permissions"]
        
        # Refresh token
        new_tokens = await auth_service_with_db.refresh_token(tokens["refresh_token"])
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        
        # Verify old access token is invalidated
        with pytest.raises(AuthenticationError):
            await auth_service_with_db.validate_token(tokens["access_token"])


class TestWebhookServiceIntegration:
    """Integration tests for WebhookService with database."""
    
    @pytest.fixture
    async def webhook_service_with_db(self, test_db_session):
        """Create webhook service with database session."""
        return WebhookService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_webhook_lifecycle_integration(self, webhook_service_with_db, test_db_session):
        """Test complete webhook lifecycle with database integration."""
        # Register webhook
        webhook = await webhook_service_with_db.register_webhook(
            webhook_url="https://integration-test.example.com/webhook",
            event_type="payment.created",
            secret="integration_test_secret",
            max_retries=3,
            retry_interval=60
        )
        
        # Verify webhook was created in database
        db_webhook = await test_db_session.get(Webhook, webhook.id)
        assert db_webhook is not None
        assert db_webhook.webhook_url == "https://integration-test.example.com/webhook"
        assert db_webhook.event_type == "payment.created"
        assert db_webhook.max_retries == 3
        
        # Simulate webhook delivery
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success"}
            
            delivery_result = await webhook_service_with_db.deliver_webhook(
                webhook.id,
                {
                    "event": "payment.created",
                    "data": {
                        "payment_id": "pay_integration_123",
                        "amount": "25.00",
                        "currency": "USD"
                    }
                }
            )
            
            assert delivery_result is not None
            assert delivery_result.status == WebhookStatus.DELIVERED
        
        # Test webhook retry logic
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.json.return_value = {"error": "Internal server error"}
            
            # First delivery attempt should fail
            delivery_result = await webhook_service_with_db.deliver_webhook(
                webhook.id,
                {
                    "event": "payment.created",
                    "data": {
                        "payment_id": "pay_integration_456",
                        "amount": "30.00",
                        "currency": "USD"
                    }
                }
            )
            
            assert delivery_result.status == WebhookStatus.FAILED
            
            # Check retry attempts
            retry_attempts = await webhook_service_with_db.get_webhook_retry_attempts(webhook.id)
            assert len(retry_attempts) > 0
        
        # Update webhook configuration
        await webhook_service_with_db.update_webhook(
            webhook.id,
            webhook_url="https://updated-integration-test.example.com/webhook",
            max_retries=5
        )
        
        # Verify update
        await test_db_session.refresh(db_webhook)
        assert db_webhook.webhook_url == "https://updated-integration-test.example.com/webhook"
        assert db_webhook.max_retries == 5
        
        # Deactivate webhook
        await webhook_service_with_db.deactivate_webhook(webhook.id)
        
        # Verify deactivation
        await test_db_session.refresh(db_webhook)
        assert db_webhook.is_active is False


class TestAuthorizeNetIntegration:
    """Integration tests for Authorize.net client."""
    
    @pytest.fixture
    def authorize_net_client(self):
        """Create Authorize.net client for integration testing."""
        return AuthorizeNetClient(
            api_login_id="test_integration_login",
            transaction_key="test_integration_key",
            is_sandbox=True
        )
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_authorize_net_authentication_integration(self, authorize_net_client):
        """Test Authorize.net authentication integration."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "messages": {
                    "resultCode": "Ok",
                    "message": [{"code": "I00001", "text": "Successful."}]
                }
            }
            
            auth_result = await authorize_net_client.test_authentication()
            assert auth_result is True
            
            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "authenticateTestRequest" in str(call_args)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_authorize_net_payment_flow_integration(self, authorize_net_client):
        """Test complete Authorize.net payment flow integration."""
        from src.integrations.authorize_net.models import CreditCard, BillingAddress
        
        credit_card = CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
        
        billing_address = BillingAddress(
            first_name="Integration",
            last_name="Test",
            address="123 Integration St",
            city="Test City",
            state="CA",
            zip="12345",
            country="US"
        )
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock successful authorization
            mock_post.return_value.json.return_value = {
                "messages": {
                    "resultCode": "Ok",
                    "message": [{"code": "I00001", "text": "Successful."}]
                },
                "transactionResponse": {
                    "transId": "integration_trans_123",
                    "responseCode": "1",
                    "responseText": "Approved",
                    "authCode": "AUTH123",
                    "avsResultCode": "Y",
                    "cvvResultCode": "M",
                    "amount": "25.00"
                },
                "refId": "integration_ref_123"
            }
            
            # Test authorize only
            auth_response = await authorize_net_client.authorize_only(
                amount=Decimal("25.00"),
                credit_card=credit_card,
                billing_address=billing_address
            )
            
            assert auth_response.transaction_id == "integration_trans_123"
            assert auth_response.status == "authorizedPendingCapture"
            
            # Test capture
            capture_response = await authorize_net_client.capture(
                transaction_id="integration_trans_123",
                amount=Decimal("25.00")
            )
            
            assert capture_response.transaction_id == "integration_trans_123"
            assert capture_response.status == "capturedPendingSettlement"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_authorize_net_error_handling_integration(self, authorize_net_client):
        """Test Authorize.net error handling integration."""
        from src.integrations.authorize_net.models import CreditCard, BillingAddress
        
        credit_card = CreditCard(
            card_number="4000000000000002",  # Declined card
            expiration_date="1225",
            card_code="123"
        )
        
        billing_address = BillingAddress(
            first_name="Error",
            last_name="Test",
            address="123 Error St",
            city="Error City",
            state="CA",
            zip="12345",
            country="US"
        )
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock declined transaction
            mock_post.return_value.json.return_value = {
                "messages": {
                    "resultCode": "Error",
                    "message": [{"code": "E00027", "text": "The transaction was declined."}]
                },
                "transactionResponse": {
                    "responseCode": "2",
                    "responseText": "Declined",
                    "amount": "25.00"
                }
            }
            
            with pytest.raises(ExternalServiceError) as exc_info:
                await authorize_net_client.charge_credit_card(
                    amount=Decimal("25.00"),
                    credit_card=credit_card,
                    billing_address=billing_address
                )
            
            assert "declined" in str(exc_info.value).lower()


class TestCacheIntegration:
    """Integration tests for cache system."""
    
    @pytest.fixture
    async def cache_strategy(self):
        """Create cache strategy for integration testing."""
        return CacheStrategy()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_integration(self, cache_strategy):
        """Test cache integration with various data types."""
        # Test string caching
        await cache_strategy.set("string_key", "string_value", ttl=60)
        string_value = await cache_strategy.get("string_key")
        assert string_value == "string_value"
        
        # Test dictionary caching
        dict_data = {"payment_id": "pay_123", "amount": "25.00", "status": "pending"}
        await cache_strategy.set("dict_key", dict_data, ttl=60)
        dict_value = await cache_strategy.get("dict_key")
        assert dict_value == dict_data
        
        # Test list caching
        list_data = ["payment_1", "payment_2", "payment_3"]
        await cache_strategy.set("list_key", list_data, ttl=60)
        list_value = await cache_strategy.get("list_key")
        assert list_value == list_data
        
        # Test expiration
        await cache_strategy.set("expire_key", "expire_value", ttl=1)
        await asyncio.sleep(1.1)
        expired_value = await cache_strategy.get("expire_key")
        assert expired_value is None
        
        # Test bulk operations
        bulk_data = {f"bulk_key_{i}": f"bulk_value_{i}" for i in range(10)}
        await cache_strategy.set_many(bulk_data, ttl=60)
        
        bulk_values = await cache_strategy.get_many(list(bulk_data.keys()))
        assert len(bulk_values) == 10
        assert all(value is not None for value in bulk_values.values())
        
        # Test cache invalidation
        await cache_strategy.delete_many(list(bulk_data.keys()))
        invalidated_values = await cache_strategy.get_many(list(bulk_data.keys()))
        assert all(value is None for value in invalidated_values.values())


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_transaction_integration(self, test_db_session):
        """Test database transaction integration."""
        from src.infrastructure.db_components.transaction_manager import TransactionManager
        
        transaction_manager = TransactionManager(test_db_session)
        
        # Test successful transaction
        async with transaction_manager.begin_transaction():
            payment1 = Payment(
                amount=Decimal("10.00"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_id="cust_txn_1",
                customer_email="txn1@example.com",
                customer_name="Transaction Test 1",
                card_token="tok_txn_1",
                description="Transaction test payment 1",
                external_id=f"pay_txn_{uuid.uuid4().hex[:12]}",
                is_test=True
            )
            
            payment2 = Payment(
                amount=Decimal("20.00"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_id="cust_txn_2",
                customer_email="txn2@example.com",
                customer_name="Transaction Test 2",
                card_token="tok_txn_2",
                description="Transaction test payment 2",
                external_id=f"pay_txn_{uuid.uuid4().hex[:12]}",
                is_test=True
            )
            
            test_db_session.add(payment1)
            test_db_session.add(payment2)
        
        # Verify both payments were committed
        assert payment1.id is not None
        assert payment2.id is not None
        
        # Test transaction rollback
        try:
            async with transaction_manager.begin_transaction():
                payment3 = Payment(
                    amount=Decimal("30.00"),
                    currency="USD",
                    payment_method=PaymentMethod.CREDIT_CARD.value,
                    customer_id="cust_txn_3",
                    customer_email="txn3@example.com",
                    customer_name="Transaction Test 3",
                    card_token="tok_txn_3",
                    description="Transaction test payment 3",
                    external_id=f"pay_txn_{uuid.uuid4().hex[:12]}",
                    is_test=True
                )
                test_db_session.add(payment3)
                raise Exception("Simulated error")
        except Exception:
            pass
        
        # Verify payment3 was not committed
        payment3_check = await test_db_session.get(Payment, payment3.id)
        assert payment3_check is None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_migration_integration(self, test_db_session):
        """Test database migration integration."""
        from src.infrastructure.db_components.migration_manager import MigrationManager
        
        migration_manager = MigrationManager(test_db_session)
        
        # Test migration creation
        migration = await migration_manager.create_migration(
            name="test_integration_migration",
            description="Test migration for integration testing",
            migration_type="schema",
            sql_up="CREATE TABLE test_table (id SERIAL PRIMARY KEY, name VARCHAR(255));",
            sql_down="DROP TABLE test_table;"
        )
        
        assert migration is not None
        assert migration.name == "test_integration_migration"
        assert migration.status == "pending"
        
        # Test migration execution
        await migration_manager.execute_migration(migration.id)
        
        # Verify migration was executed
        await test_db_session.refresh(migration)
        assert migration.status == "completed"
        assert migration.executed_at is not None


class TestPerformanceIntegration:
    """Integration tests for performance-critical operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_bulk_payment_creation_integration(self, payment_service_with_db, test_db_session):
        """Test bulk payment creation performance."""
        import time
        
        # Create bulk payment requests
        payment_requests = []
        for i in range(100):
            payment_data = {
                "amount": Decimal(f"{10 + (i % 10)}.00"),
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": f"cust_bulk_{i}",
                "customer_email": f"bulk{i}@example.com",
                "customer_name": f"Bulk Test Customer {i}",
                "card_token": f"tok_bulk_{i}",
                "description": f"Bulk test payment {i}",
                "is_test": True
            }
            payment_requests.append(type(sample_payment_create_request)(**payment_data))
        
        # Measure bulk creation time
        start_time = time.time()
        
        tasks = []
        for request in payment_requests:
            task = payment_service_with_db.create_payment(request)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify performance
        assert end_time - start_time < 15.0  # Should complete within 15 seconds
        assert len(results) == 100
        
        # Verify all payments were created
        for payment in results:
            assert payment is not None
            assert payment.status == PaymentStatus.PENDING
        
        # Verify database consistency
        db_payments = await test_db_session.execute(
            "SELECT COUNT(*) FROM payments WHERE is_test = true"
        )
        count = db_payments.scalar()
        assert count >= 100  # At least 100 test payments
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_payment_operations_integration(self, payment_service_with_db, test_db_session):
        """Test concurrent payment operations."""
        # Create a test payment
        payment_data = {
            "amount": Decimal("50.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_concurrent_123",
            "customer_email": "concurrent@example.com",
            "customer_name": "Concurrent Test Customer",
            "card_token": "tok_concurrent_123",
            "description": "Concurrent test payment",
            "is_test": True
        }
        
        payment = await payment_service_with_db.create_payment(
            type(sample_payment_create_request)(**payment_data)
        )
        
        # Test concurrent status updates
        async def update_status(status):
            await payment_service_with_db.update_payment_status(payment.id, status)
            return status
        
        # Concurrent status updates
        tasks = [
            update_status(PaymentStatus.AUTHORIZED),
            update_status(PaymentStatus.CAPTURED),
            update_status(PaymentStatus.SETTLED)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify at least one update succeeded
        successful_updates = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_updates) > 0
        
        # Verify final payment state
        await test_db_session.refresh(payment)
        assert payment.status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED, PaymentStatus.SETTLED]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
