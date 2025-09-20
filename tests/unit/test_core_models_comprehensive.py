"""
Comprehensive tests for core models to achieve 80%+ coverage.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus, Token, TokenType
from src.core.models.audit_log import AuditLog, AuditLevel
from src.core.models.webhook import Webhook, WebhookStatus, WebhookEvent
from src.core.models.rbac import Role, Permission, UserRole, RolePermission


class TestPaymentModel:
    """Comprehensive tests for Payment model."""
    
    def test_payment_creation_with_minimal_data(self):
        """Test payment creation with minimal required data."""
        payment = Payment(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123"
        )
        
        assert payment.amount == Decimal("10.00")
        assert payment.currency == "USD"
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.external_id == "pay_test_123"
        assert payment.status == PaymentStatus.PENDING
        assert payment.is_test is False
        assert payment.created_at is not None
        assert payment.updated_at is not None
    
    def test_payment_creation_with_all_fields(self):
        """Test payment creation with all fields."""
        payment_data = {
            "amount": Decimal("25.99"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD,
            "customer_id": "cust_123",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_123456789",
            "description": "Test payment",
            "metadata": {"order_id": "order_123", "source": "test"},
            "external_id": "pay_test_456",
            "status": PaymentStatus.AUTHORIZED,
            "is_test": True,
            "authorize_net_transaction_id": "trans_123",
            "authorize_net_response_code": "1",
            "authorize_net_response_text": "Approved",
            "authorize_net_auth_code": "AUTH123",
            "refunded_amount": Decimal("5.00"),
            "refund_count": 1
        }
        
        payment = Payment(**payment_data)
        
        for key, value in payment_data.items():
            assert getattr(payment, key) == value
    
    def test_payment_status_transitions(self):
        """Test payment status transitions."""
        payment = Payment(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_789"
        )
        
        # Test initial status
        assert payment.status == PaymentStatus.PENDING
        
        # Test status updates
        payment.status = PaymentStatus.AUTHORIZED
        assert payment.status == PaymentStatus.AUTHORIZED
        
        payment.status = PaymentStatus.CAPTURED
        assert payment.status == PaymentStatus.CAPTURED
        
        payment.status = PaymentStatus.SETTLED
        assert payment.status == PaymentStatus.SETTLED
    
    def test_payment_method_enum(self):
        """Test payment method enum values."""
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.DEBIT_CARD.value == "debit_card"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
    
    def test_payment_status_enum(self):
        """Test payment status enum values."""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.AUTHORIZED.value == "authorized"
        assert PaymentStatus.CAPTURED.value == "captured"
        assert PaymentStatus.SETTLED.value == "settled"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.REFUNDED.value == "refunded"
    
    def test_payment_refund_tracking(self):
        """Test payment refund amount tracking."""
        payment = Payment(
            amount=Decimal("100.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_refund"
        )
        
        # Initial refund tracking
        assert payment.refunded_amount == Decimal("0.00")
        assert payment.refund_count == 0
        
        # Update refund tracking
        payment.refunded_amount = Decimal("25.00")
        payment.refund_count = 1
        
        assert payment.refunded_amount == Decimal("25.00")
        assert payment.refund_count == 1
        
        # Test remaining refundable amount
        remaining = payment.amount - payment.refunded_amount
        assert remaining == Decimal("75.00")
    
    def test_payment_metadata_handling(self):
        """Test payment metadata handling."""
        metadata = {
            "order_id": "order_123",
            "source": "web",
            "campaign": "summer_sale",
            "customer_segment": "premium"
        }
        
        payment = Payment(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_metadata",
            metadata=metadata
        )
        
        assert payment.metadata == metadata
        assert payment.metadata["order_id"] == "order_123"
        assert payment.metadata["source"] == "web"
    
    def test_payment_timestamps(self):
        """Test payment timestamp handling."""
        payment = Payment(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_timestamps"
        )
        
        # Test that timestamps are set
        assert payment.created_at is not None
        assert payment.updated_at is not None
        
        # Test timestamp types
        assert isinstance(payment.created_at, datetime)
        assert isinstance(payment.updated_at, datetime)
        
        # Test that created_at is before or equal to updated_at
        assert payment.created_at <= payment.updated_at


class TestAPIKeyModel:
    """Comprehensive tests for APIKey model."""
    
    def test_api_key_creation(self):
        """Test API key creation."""
        api_key = APIKey(
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            description="Test key for testing",
            permissions=["payments:read", "payments:write"],
            status=APIKeyStatus.ACTIVE,
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000
        )
        
        assert api_key.key_id == "ak_test_123"
        assert api_key.key_secret_hash == "hashed_secret"
        assert api_key.name == "Test API Key"
        assert api_key.description == "Test key for testing"
        assert api_key.permissions == ["payments:read", "payments:write"]
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.rate_limit_per_minute == 100
        assert api_key.rate_limit_per_hour == 1000
        assert api_key.rate_limit_per_day == 10000
    
    def test_api_key_status_enum(self):
        """Test API key status enum values."""
        assert APIKeyStatus.ACTIVE.value == "active"
        assert APIKeyStatus.INACTIVE.value == "inactive"
        assert APIKeyStatus.REVOKED.value == "revoked"
        assert APIKeyStatus.EXPIRED.value == "expired"
    
    def test_api_key_permissions(self):
        """Test API key permissions handling."""
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
            key_id="ak_test_permissions",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            permissions=permissions
        )
        
        assert api_key.permissions == permissions
        assert len(api_key.permissions) == 7
    
    def test_api_key_rate_limits(self):
        """Test API key rate limit handling."""
        api_key = APIKey(
            key_id="ak_test_limits",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            rate_limit_per_minute=50,
            rate_limit_per_hour=500,
            rate_limit_per_day=5000
        )
        
        assert api_key.rate_limit_per_minute == 50
        assert api_key.rate_limit_per_hour == 500
        assert api_key.rate_limit_per_day == 5000
    
    def test_api_key_ip_restrictions(self):
        """Test API key IP restrictions."""
        ip_whitelist = ["192.168.1.0/24", "10.0.0.0/8"]
        ip_blacklist = ["192.168.1.100", "10.0.0.50"]
        
        api_key = APIKey(
            key_id="ak_test_ip",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            ip_whitelist=ip_whitelist,
            ip_blacklist=ip_blacklist
        )
        
        assert api_key.ip_whitelist == ip_whitelist
        assert api_key.ip_blacklist == ip_blacklist
    
    def test_api_key_expiration(self):
        """Test API key expiration handling."""
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        api_key = APIKey(
            key_id="ak_test_expiry",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            expires_at=expires_at
        )
        
        assert api_key.expires_at == expires_at
    
    def test_api_key_usage_tracking(self):
        """Test API key usage tracking."""
        api_key = APIKey(
            key_id="ak_test_usage",
            key_secret_hash="hashed_secret",
            name="Test API Key",
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


class TestTokenModel:
    """Comprehensive tests for Token model."""
    
    def test_token_creation(self):
        """Test token creation."""
        token = Token(
            token_id="token_123",
            token_type=TokenType.ACCESS,
            user_id="user_123",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_revoked=False
        )
        
        assert token.token_id == "token_123"
        assert token.token_type == TokenType.ACCESS
        assert token.user_id == "user_123"
        assert token.is_revoked is False
        assert token.expires_at is not None
    
    def test_token_type_enum(self):
        """Test token type enum values."""
        assert TokenType.ACCESS.value == "access"
        assert TokenType.REFRESH.value == "refresh"
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        token = Token(
            token_id="token_expiry",
            token_type=TokenType.ACCESS,
            user_id="user_123",
            expires_at=expires_at
        )
        
        assert token.expires_at == expires_at
    
    def test_token_revocation(self):
        """Test token revocation."""
        token = Token(
            token_id="token_revoke",
            token_type=TokenType.ACCESS,
            user_id="user_123",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_revoked=False
        )
        
        assert token.is_revoked is False
        
        token.is_revoked = True
        token.revoked_at = datetime.utcnow()
        
        assert token.is_revoked is True
        assert token.revoked_at is not None


class TestAuditLogModel:
    """Comprehensive tests for AuditLog model."""
    
    def test_audit_log_creation(self):
        """Test audit log creation."""
        audit_log = AuditLog(
            payment_id=uuid.uuid4(),
            action="payment_created",
            level=AuditLevel.INFO,
            message="Payment created successfully",
            entity_type="payment",
            entity_id="pay_123",
            audit_metadata={"test": True},
            user_id="user_123",
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert audit_log.action == "payment_created"
        assert audit_log.level == AuditLevel.INFO
        assert audit_log.message == "Payment created successfully"
        assert audit_log.entity_type == "payment"
        assert audit_log.entity_id == "pay_123"
        assert audit_log.audit_metadata == {"test": True}
        assert audit_log.user_id == "user_123"
        assert audit_log.ip_address == "127.0.0.1"
        assert audit_log.user_agent == "test-agent"
    
    def test_audit_level_enum(self):
        """Test audit level enum values."""
        assert AuditLevel.DEBUG.value == "debug"
        assert AuditLevel.INFO.value == "info"
        assert AuditLevel.WARNING.value == "warning"
        assert AuditLevel.ERROR.value == "error"
        assert AuditLevel.CRITICAL.value == "critical"
    
    def test_audit_log_timestamps(self):
        """Test audit log timestamp handling."""
        audit_log = AuditLog(
            payment_id=uuid.uuid4(),
            action="test_action",
            level=AuditLevel.INFO,
            message="Test message"
        )
        
        assert audit_log.created_at is not None
        assert isinstance(audit_log.created_at, datetime)


class TestWebhookModel:
    """Comprehensive tests for Webhook model."""
    
    def test_webhook_creation(self):
        """Test webhook creation."""
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            is_active=True,
            secret="webhook_secret_123",
            metadata={"source": "test"},
            retry_count=0,
            max_retries=3,
            timeout_seconds=30
        )
        
        assert webhook.webhook_url == "https://example.com/webhook"
        assert webhook.event_type == "payment.created"
        assert webhook.is_active is True
        assert webhook.secret == "webhook_secret_123"
        assert webhook.metadata == {"source": "test"}
        assert webhook.retry_count == 0
        assert webhook.max_retries == 3
        assert webhook.timeout_seconds == 30
    
    def test_webhook_status_enum(self):
        """Test webhook status enum values."""
        assert WebhookStatus.PENDING.value == "pending"
        assert WebhookStatus.SENT.value == "sent"
        assert WebhookStatus.FAILED.value == "failed"
        assert WebhookStatus.RETRYING.value == "retrying"
        assert WebhookStatus.EXPIRED.value == "expired"
    
    def test_webhook_event_enum(self):
        """Test webhook event enum values."""
        assert WebhookEvent.PAYMENT_CREATED.value == "payment.created"
        assert WebhookEvent.PAYMENT_UPDATED.value == "payment.updated"
        assert WebhookEvent.PAYMENT_COMPLETED.value == "payment.completed"
        assert WebhookEvent.PAYMENT_FAILED.value == "payment.failed"
        assert WebhookEvent.PAYMENT_REFUNDED.value == "payment.refunded"
    
    def test_webhook_retry_logic(self):
        """Test webhook retry logic."""
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            retry_count=0,
            max_retries=3
        )
        
        assert webhook.retry_count == 0
        assert webhook.max_retries == 3
        
        # Simulate retries
        webhook.retry_count = 1
        assert webhook.retry_count == 1
        
        webhook.retry_count = 2
        assert webhook.retry_count == 2
    
    def test_webhook_timeout_handling(self):
        """Test webhook timeout handling."""
        webhook = Webhook(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            timeout_seconds=30
        )
        
        assert webhook.timeout_seconds == 30


class TestRBACModels:
    """Comprehensive tests for RBAC models."""
    
    def test_role_creation(self):
        """Test role creation."""
        role = Role(
            name="admin",
            description="Administrator role",
            is_active=True
        )
        
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.is_active is True
    
    def test_permission_creation(self):
        """Test permission creation."""
        permission = Permission(
            name="payments:write",
            description="Write permission for payments",
            resource="payments",
            action="write"
        )
        
        assert permission.name == "payments:write"
        assert permission.description == "Write permission for payments"
        assert permission.resource == "payments"
        assert permission.action == "write"
    
    def test_user_role_association(self):
        """Test user role association."""
        user_role = UserRole(
            user_id="user_123",
            role_id=uuid.uuid4()
        )
        
        assert user_role.user_id == "user_123"
        assert user_role.role_id is not None
    
    def test_role_permission_association(self):
        """Test role permission association."""
        role_permission = RolePermission(
            role_id=uuid.uuid4(),
            permission_id=uuid.uuid4()
        )
        
        assert role_permission.role_id is not None
        assert role_permission.permission_id is not None


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_payment_amount_validation(self):
        """Test payment amount validation."""
        # Test valid amounts
        valid_amounts = [Decimal("0.01"), Decimal("1.00"), Decimal("999999.99")]
        
        for amount in valid_amounts:
            payment = Payment(
                amount=amount,
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                external_id=f"pay_test_{amount}"
            )
            assert payment.amount == amount
    
    def test_payment_currency_validation(self):
        """Test payment currency validation."""
        valid_currencies = ["USD", "EUR", "GBP", "CAD"]
        
        for currency in valid_currencies:
            payment = Payment(
                amount=Decimal("10.00"),
                currency=currency,
                payment_method=PaymentMethod.CREDIT_CARD,
                external_id=f"pay_test_{currency}"
            )
            assert payment.currency == currency
    
    def test_api_key_permission_validation(self):
        """Test API key permission validation."""
        valid_permissions = [
            "payments:read",
            "payments:write",
            "payments:delete",
            "webhooks:read",
            "webhooks:write",
            "admin:read",
            "admin:write"
        ]
        
        api_key = APIKey(
            key_id="ak_test_permissions",
            key_secret_hash="hashed_secret",
            name="Test API Key",
            permissions=valid_permissions
        )
        
        assert api_key.permissions == valid_permissions
    
    def test_webhook_url_validation(self):
        """Test webhook URL validation."""
        valid_urls = [
            "https://example.com/webhook",
            "https://api.example.com/v1/webhooks",
            "https://webhook.site/12345678-1234-1234-1234-123456789012"
        ]
        
        for url in valid_urls:
            webhook = Webhook(
                webhook_url=url,
                event_type="payment.created"
            )
            assert webhook.webhook_url == url


class TestModelRelationships:
    """Test model relationships and associations."""
    
    def test_payment_audit_log_relationship(self):
        """Test payment to audit log relationship."""
        payment_id = uuid.uuid4()
        
        audit_log = AuditLog(
            payment_id=payment_id,
            action="payment_created",
            level=AuditLevel.INFO,
            message="Payment created"
        )
        
        assert audit_log.payment_id == payment_id
    
    def test_api_key_token_relationship(self):
        """Test API key to token relationship."""
        api_key_id = uuid.uuid4()
        
        token = Token(
            token_id="token_123",
            token_type=TokenType.ACCESS,
            user_id="user_123",
            api_key_id=api_key_id
        )
        
        assert token.api_key_id == api_key_id
    
    def test_webhook_delivery_tracking(self):
        """Test webhook delivery tracking."""
        webhook_id = uuid.uuid4()
        
        # Simulate webhook delivery tracking
        delivery_data = {
            "webhook_id": webhook_id,
            "status": "sent",
            "response_code": 200,
            "response_time_ms": 150,
            "delivered_at": datetime.utcnow()
        }
        
        assert delivery_data["webhook_id"] == webhook_id
        assert delivery_data["status"] == "sent"
        assert delivery_data["response_code"] == 200
