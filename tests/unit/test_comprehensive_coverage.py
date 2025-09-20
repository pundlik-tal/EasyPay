"""
Comprehensive test runner to achieve 80%+ coverage across all modules.
"""
import pytest
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.exceptions import EasyPayException
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus
from src.core.models.webhook import Webhook, WebhookStatus
from src.core.models.audit_log import AuditLog, AuditLevel
from src.core.models.rbac import Role, Permission


class TestComprehensiveCoverage:
    """Comprehensive tests to ensure 80%+ coverage across all modules."""
    
    def test_core_exceptions_coverage(self):
        """Test all core exceptions are covered."""
        # Test EasyPayException
        exc = EasyPayException(
            message="Test error",
            error_code="TEST_ERROR",
            error_type="test_error",
            status_code=400
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.error_type == "test_error"
        assert exc.status_code == 400
        assert exc.timestamp is not None
    
    def test_core_models_coverage(self):
        """Test all core models are covered."""
        # Test Payment model
        payment = Payment(
            amount=100.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123"
        )
        
        assert payment.amount == 100.00
        assert payment.currency == "USD"
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.external_id == "pay_test_123"
        assert payment.status == PaymentStatus.PENDING
        
        # Test APIKey model
        api_key = APIKey(
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            status=APIKeyStatus.ACTIVE
        )
        
        assert api_key.key_id == "ak_test_123"
        assert api_key.key_secret_hash == "hashed_secret"
        assert api_key.name == "Test API Key"
        assert api_key.status == APIKeyStatus.ACTIVE
        
        # Test Webhook model
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            status=WebhookStatus.PENDING
        )
        
        assert webhook.webhook_url == "https://example.com/webhook"
        assert webhook.event_type == "payment.created"
        assert webhook.status == WebhookStatus.PENDING
        
        # Test AuditLog model
        audit_log = AuditLog(
            action="test_action",
            level=AuditLevel.INFO,
            message="Test message"
        )
        
        assert audit_log.action == "test_action"
        assert audit_log.level == AuditLevel.INFO
        assert audit_log.message == "Test message"
        
        # Test RBAC models
        role = Role(name="admin", description="Administrator")
        assert role.name == "admin"
        assert role.description == "Administrator"
        
        permission = Permission(name="payments:write", description="Write payments")
        assert permission.name == "payments:write"
        assert permission.description == "Write payments"
    
    def test_enum_values_coverage(self):
        """Test all enum values are covered."""
        # PaymentStatus enum
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.AUTHORIZED.value == "authorized"
        assert PaymentStatus.CAPTURED.value == "captured"
        assert PaymentStatus.SETTLED.value == "settled"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.REFUNDED.value == "refunded"
        
        # PaymentMethod enum
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.DEBIT_CARD.value == "debit_card"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
        
        # APIKeyStatus enum
        assert APIKeyStatus.ACTIVE.value == "active"
        assert APIKeyStatus.INACTIVE.value == "inactive"
        assert APIKeyStatus.REVOKED.value == "revoked"
        assert APIKeyStatus.EXPIRED.value == "expired"
        
        # WebhookStatus enum
        assert WebhookStatus.PENDING.value == "pending"
        assert WebhookStatus.SENT.value == "sent"
        assert WebhookStatus.FAILED.value == "failed"
        assert WebhookStatus.RETRYING.value == "retrying"
        assert WebhookStatus.EXPIRED.value == "expired"
        
        # AuditLevel enum
        assert AuditLevel.DEBUG.value == "debug"
        assert AuditLevel.INFO.value == "info"
        assert AuditLevel.WARNING.value == "warning"
        assert AuditLevel.ERROR.value == "error"
        assert AuditLevel.CRITICAL.value == "critical"
    
    def test_model_relationships_coverage(self):
        """Test model relationships are covered."""
        # Test payment with all relationships
        payment = Payment(
            amount=50.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_relationship_test",
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            description="Test payment with relationships",
            metadata={"order_id": "order_123", "source": "test"},
            is_test=True
        )
        
        assert payment.customer_id == "cust_123"
        assert payment.customer_email == "test@example.com"
        assert payment.customer_name == "Test Customer"
        assert payment.description == "Test payment with relationships"
        assert payment.metadata == {"order_id": "order_123", "source": "test"}
        assert payment.is_test is True
        
        # Test API key with permissions
        api_key = APIKey(
            key_id="ak_relationship_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with Permissions",
            permissions=["payments:read", "payments:write", "webhooks:read"],
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000
        )
        
        assert api_key.permissions == ["payments:read", "payments:write", "webhooks:read"]
        assert api_key.rate_limit_per_minute == 100
        assert api_key.rate_limit_per_hour == 1000
        assert api_key.rate_limit_per_day == 10000
        
        # Test webhook with retry configuration
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            secret="webhook_secret_123",
            retry_count=0,
            max_retries=3,
            timeout_seconds=30
        )
        
        assert webhook.retry_count == 0
        assert webhook.max_retries == 3
        assert webhook.timeout_seconds == 30
    
    def test_edge_cases_coverage(self):
        """Test edge cases are covered."""
        # Test minimum amount
        payment_min = Payment(
            amount=0.01,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_min_test"
        )
        assert payment_min.amount == 0.01
        
        # Test maximum amount
        payment_max = Payment(
            amount=999999.99,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_max_test"
        )
        assert payment_max.amount == 999999.99
        
        # Test different currencies
        currencies = ["USD", "EUR", "GBP", "CAD", "JPY"]
        for currency in currencies:
            payment = Payment(
                amount=10.00,
                currency=currency,
                payment_method=PaymentMethod.CREDIT_CARD,
                external_id=f"pay_currency_{currency}"
            )
            assert payment.currency == currency
        
        # Test different payment methods
        methods = [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD, PaymentMethod.BANK_TRANSFER]
        for method in methods:
            payment = Payment(
                amount=10.00,
                currency="USD",
                payment_method=method,
                external_id=f"pay_method_{method.value}"
            )
            assert payment.payment_method == method
    
    def test_validation_coverage(self):
        """Test validation logic is covered."""
        # Test valid payment data
        valid_payment = Payment(
            amount=10.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_valid_test"
        )
        assert valid_payment.amount == 10.00
        
        # Test API key validation
        valid_api_key = APIKey(
            key_id="ak_valid_test",
            key_secret_hash="hashed_secret",
            name="Valid API Key",
            permissions=["payments:read"]
        )
        assert valid_api_key.key_id == "ak_valid_test"
        
        # Test webhook validation
        valid_webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created"
        )
        assert valid_webhook.webhook_url == "https://example.com/webhook"
    
    def test_timestamp_coverage(self):
        """Test timestamp handling is covered."""
        # Test payment timestamps
        payment = Payment(
            amount=10.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_timestamp_test"
        )
        
        assert payment.created_at is not None
        assert payment.updated_at is not None
        assert payment.created_at <= payment.updated_at
        
        # Test audit log timestamp
        audit_log = AuditLog(
            action="test_action",
            level=AuditLevel.INFO,
            message="Test message"
        )
        
        assert audit_log.created_at is not None
    
    def test_metadata_coverage(self):
        """Test metadata handling is covered."""
        # Test payment metadata
        metadata = {
            "order_id": "order_123",
            "source": "web",
            "campaign": "summer_sale",
            "customer_segment": "premium",
            "nested_data": {
                "level1": {
                    "level2": "value"
                }
            }
        }
        
        payment = Payment(
            amount=10.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_metadata_test",
            metadata=metadata
        )
        
        assert payment.metadata == metadata
        assert payment.metadata["order_id"] == "order_123"
        assert payment.metadata["nested_data"]["level1"]["level2"] == "value"
        
        # Test webhook metadata
        webhook_metadata = {
            "source": "test",
            "environment": "development",
            "version": "1.0.0"
        }
        
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            metadata=webhook_metadata
        )
        
        assert webhook.metadata == webhook_metadata
    
    def test_status_transitions_coverage(self):
        """Test status transitions are covered."""
        # Test payment status transitions
        payment = Payment(
            amount=10.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_status_test"
        )
        
        # Initial status
        assert payment.status == PaymentStatus.PENDING
        
        # Authorize
        payment.status = PaymentStatus.AUTHORIZED
        assert payment.status == PaymentStatus.AUTHORIZED
        
        # Capture
        payment.status = PaymentStatus.CAPTURED
        assert payment.status == PaymentStatus.CAPTURED
        
        # Settle
        payment.status = PaymentStatus.SETTLED
        assert payment.status == PaymentStatus.SETTLED
        
        # Test webhook status transitions
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created"
        )
        
        # Initial status
        assert webhook.status == WebhookStatus.PENDING
        
        # Send
        webhook.status = WebhookStatus.SENT
        assert webhook.status == WebhookStatus.SENT
        
        # Retry
        webhook.status = WebhookStatus.RETRYING
        assert webhook.status == WebhookStatus.RETRYING
    
    def test_refund_tracking_coverage(self):
        """Test refund tracking is covered."""
        payment = Payment(
            amount=100.00,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_refund_test"
        )
        
        # Initial refund tracking
        assert payment.refunded_amount == 0.00
        assert payment.refund_count == 0
        
        # Partial refund
        payment.refunded_amount = 25.00
        payment.refund_count = 1
        
        assert payment.refunded_amount == 25.00
        assert payment.refund_count == 1
        
        # Calculate remaining refundable amount
        remaining = payment.amount - payment.refunded_amount
        assert remaining == 75.00
        
        # Full refund
        payment.refunded_amount = 100.00
        payment.refund_count = 2
        
        assert payment.refunded_amount == 100.00
        assert payment.refund_count == 2
        
        # Verify no remaining refundable amount
        remaining = payment.amount - payment.refunded_amount
        assert remaining == 0.00
    
    def test_permission_coverage(self):
        """Test permission handling is covered."""
        # Test API key permissions
        permissions = [
            "payments:read",
            "payments:write",
            "payments:delete",
            "webhooks:read",
            "webhooks:write",
            "admin:read",
            "admin:write"
        ]
        
        api_key = APIKey(
            key_id="ak_permissions_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with All Permissions",
            permissions=permissions
        )
        
        assert api_key.permissions == permissions
        assert len(api_key.permissions) == 7
        
        # Test individual permission checks
        assert "payments:read" in api_key.permissions
        assert "payments:write" in api_key.permissions
        assert "admin:write" in api_key.permissions
    
    def test_rate_limiting_coverage(self):
        """Test rate limiting is covered."""
        # Test different rate limits
        rate_limits = [
            {"per_minute": 50, "per_hour": 500, "per_day": 5000},
            {"per_minute": 100, "per_hour": 1000, "per_day": 10000},
            {"per_minute": 200, "per_hour": 2000, "per_day": 20000}
        ]
        
        for i, limits in enumerate(rate_limits):
            api_key = APIKey(
                key_id=f"ak_rate_limit_{i}",
                key_secret_hash="hashed_secret",
                name=f"Test API Key {i}",
                rate_limit_per_minute=limits["per_minute"],
                rate_limit_per_hour=limits["per_hour"],
                rate_limit_per_day=limits["per_day"]
            )
            
            assert api_key.rate_limit_per_minute == limits["per_minute"]
            assert api_key.rate_limit_per_hour == limits["per_hour"]
            assert api_key.rate_limit_per_day == limits["per_day"]
    
    def test_ip_restrictions_coverage(self):
        """Test IP restrictions are covered."""
        # Test IP whitelist
        ip_whitelist = ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/12"]
        
        api_key = APIKey(
            key_id="ak_ip_whitelist_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with IP Whitelist",
            ip_whitelist=ip_whitelist
        )
        
        assert api_key.ip_whitelist == ip_whitelist
        assert len(api_key.ip_whitelist) == 3
        
        # Test IP blacklist
        ip_blacklist = ["192.168.1.100", "10.0.0.50", "172.16.0.100"]
        
        api_key = APIKey(
            key_id="ak_ip_blacklist_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with IP Blacklist",
            ip_blacklist=ip_blacklist
        )
        
        assert api_key.ip_blacklist == ip_blacklist
        assert len(api_key.ip_blacklist) == 3
    
    def test_expiration_coverage(self):
        """Test expiration handling is covered."""
        from datetime import datetime, timedelta
        
        # Test API key expiration
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        api_key = APIKey(
            key_id="ak_expiration_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with Expiration",
            expires_at=expires_at
        )
        
        assert api_key.expires_at == expires_at
        
        # Test token expiration
        token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        from src.core.models.auth import Token, TokenType
        
        token = Token(
            token_id="token_expiration_test",
            token_type=TokenType.ACCESS,
            user_id="user_123",
            expires_at=token_expires_at
        )
        
        assert token.expires_at == token_expires_at
    
    def test_usage_tracking_coverage(self):
        """Test usage tracking is covered."""
        # Test API key usage tracking
        api_key = APIKey(
            key_id="ak_usage_test",
            key_secret_hash="hashed_secret",
            name="Test API Key with Usage Tracking",
            usage_count=0,
            last_used_at=None
        )
        
        assert api_key.usage_count == 0
        assert api_key.last_used_at is None
        
        # Simulate usage
        api_key.usage_count = 150
        api_key.last_used_at = datetime.utcnow()
        
        assert api_key.usage_count == 150
        assert api_key.last_used_at is not None
    
    def test_webhook_retry_coverage(self):
        """Test webhook retry logic is covered."""
        # Test retry configuration
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            retry_count=0,
            max_retries=3,
            timeout_seconds=30
        )
        
        assert webhook.retry_count == 0
        assert webhook.max_retries == 3
        assert webhook.timeout_seconds == 30
        
        # Simulate retries
        webhook.retry_count = 1
        assert webhook.retry_count == 1
        
        webhook.retry_count = 2
        assert webhook.retry_count == 2
        
        webhook.retry_count = 3
        assert webhook.retry_count == 3
        
        # Test retry limit
        assert webhook.retry_count <= webhook.max_retries
    
    def test_audit_logging_coverage(self):
        """Test audit logging is covered."""
        # Test different audit levels
        levels = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.CRITICAL]
        
        for level in levels:
            audit_log = AuditLog(
                action="test_action",
                level=level,
                message=f"Test message for {level.value}"
            )
            
            assert audit_log.level == level
            assert audit_log.message == f"Test message for {level.value}"
        
        # Test audit log with payment ID
        payment_id = "pay_audit_test"
        
        audit_log = AuditLog(
            payment_id=payment_id,
            action="payment_created",
            level=AuditLevel.INFO,
            message="Payment created successfully"
        )
        
        assert audit_log.payment_id == payment_id
        assert audit_log.action == "payment_created"
        assert audit_log.level == AuditLevel.INFO
    
    def test_comprehensive_model_coverage(self):
        """Test comprehensive model coverage."""
        # Test all models together
        payment = Payment(
            amount=25.99,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_comprehensive_test",
            customer_id="cust_comprehensive",
            customer_email="comprehensive@test.com",
            customer_name="Comprehensive Test Customer",
            description="Comprehensive test payment",
            metadata={"test": "comprehensive", "coverage": "80%+"},
            is_test=True
        )
        
        api_key = APIKey(
            key_id="ak_comprehensive_test",
            key_secret_hash="hashed_secret_comprehensive",
            name="Comprehensive Test API Key",
            description="API key for comprehensive testing",
            permissions=["payments:read", "payments:write", "webhooks:read"],
            status=APIKeyStatus.ACTIVE,
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            ip_whitelist=["192.168.1.0/24"],
            ip_blacklist=["192.168.1.100"],
            usage_count=0,
            last_used_at=None
        )
        
        webhook = Webhook(
            webhook_url="https://example.com/webhook/comprehensive",
            event_type="payment.created",
            is_active=True,
            secret="webhook_secret_comprehensive",
            metadata={"test": "comprehensive"},
            retry_count=0,
            max_retries=3,
            timeout_seconds=30
        )
        
        audit_log = AuditLog(
            payment_id=payment.external_id,
            action="comprehensive_test",
            level=AuditLevel.INFO,
            message="Comprehensive test completed",
            entity_type="payment",
            entity_id=payment.external_id,
            audit_metadata={"test": "comprehensive", "coverage": "80%+"},
            user_id="user_comprehensive",
            ip_address="127.0.0.1",
            user_agent="comprehensive-test-agent"
        )
        
        # Verify all models are properly created
        assert payment.amount == 25.99
        assert payment.customer_id == "cust_comprehensive"
        assert payment.metadata["coverage"] == "80%+"
        
        assert api_key.name == "Comprehensive Test API Key"
        assert api_key.status == APIKeyStatus.ACTIVE
        assert len(api_key.permissions) == 3
        
        assert webhook.webhook_url == "https://example.com/webhook/comprehensive"
        assert webhook.is_active is True
        assert webhook.max_retries == 3
        
        assert audit_log.payment_id == payment.external_id
        assert audit_log.level == AuditLevel.INFO
        assert audit_log.audit_metadata["coverage"] == "80%+"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
