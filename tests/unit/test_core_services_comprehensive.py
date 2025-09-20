"""
Comprehensive tests for core services to achieve 80%+ coverage.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.core.services.webhook_service import WebhookService
from src.core.services.audit_logging_service import AuditLoggingService
from src.core.services.rbac_service import RBACService
from src.core.services.advanced_payment_features import AdvancedPaymentFeatures
from src.core.exceptions import (
    PaymentError, PaymentNotFoundError, ValidationError,
    AuthenticationError, AuthorizationError, DatabaseError
)
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus, Token, TokenType
from src.core.models.webhook import Webhook, WebhookStatus, WebhookEvent
from src.core.models.audit_log import AuditLog, AuditLevel


class TestPaymentService:
    """Comprehensive tests for PaymentService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_payment_repository(self):
        """Mock payment repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_123"
        mock_response.status = "captured"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_response.auth_code = "AUTH123"
        mock_response.amount = "10.00"
        
        mock_client.charge_credit_card.return_value = mock_response
        mock_client.authorize_only.return_value = mock_response
        mock_client.capture.return_value = mock_response
        mock_client.refund.return_value = mock_response
        mock_client.void_transaction.return_value = mock_response
        
        return mock_client
    
    @pytest.fixture
    def payment_service(self, mock_db_session, mock_payment_repository, mock_authorize_net_client):
        """Create PaymentService instance with mocked dependencies."""
        with patch('src.core.services.payment_service.PaymentRepository', return_value=mock_payment_repository):
            with patch('src.core.services.payment_service.AuthorizeNetClient', return_value=mock_authorize_net_client):
                return PaymentService(mock_db_session)
    
    @pytest.fixture
    def sample_payment_data(self):
        """Sample payment creation data."""
        return {
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD,
            "customer_id": "cust_123",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_123456789",
            "description": "Test payment",
            "metadata": {"order_id": "order_123", "source": "test"},
            "is_test": True
        }
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, payment_service, sample_payment_data, mock_payment_repository):
        """Test successful payment creation."""
        # Mock repository response
        created_payment = Payment(
            id=uuid.uuid4(),
            external_id="pay_test_123",
            **sample_payment_data
        )
        mock_payment_repository.create.return_value = created_payment
        
        # Test payment creation
        result = await payment_service.create_payment(sample_payment_data)
        
        assert result is not None
        assert result.amount == sample_payment_data["amount"]
        assert result.currency == sample_payment_data["currency"]
        assert result.payment_method == sample_payment_data["payment_method"]
        mock_payment_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_payment_validation_error(self, payment_service):
        """Test payment creation with validation error."""
        invalid_data = {
            "amount": Decimal("-10.00"),  # Invalid negative amount
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD
        }
        
        with pytest.raises(ValidationError):
            await payment_service.create_payment(invalid_data)
    
    @pytest.mark.asyncio
    async def test_get_payment_by_id(self, payment_service, mock_payment_repository):
        """Test getting payment by ID."""
        payment_id = uuid.uuid4()
        payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123"
        )
        
        mock_payment_repository.get_by_id.return_value = payment
        
        result = await payment_service.get_payment(payment_id)
        
        assert result is not None
        assert result.id == payment_id
        mock_payment_repository.get_by_id.assert_called_once_with(payment_id)
    
    @pytest.mark.asyncio
    async def test_get_payment_not_found(self, payment_service, mock_payment_repository):
        """Test getting non-existent payment."""
        payment_id = uuid.uuid4()
        mock_payment_repository.get_by_id.return_value = None
        
        with pytest.raises(PaymentNotFoundError):
            await payment_service.get_payment(payment_id)
    
    @pytest.mark.asyncio
    async def test_get_payment_by_external_id(self, payment_service, mock_payment_repository):
        """Test getting payment by external ID."""
        external_id = "pay_test_123"
        payment = Payment(
            id=uuid.uuid4(),
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id=external_id
        )
        
        mock_payment_repository.get_by_external_id.return_value = payment
        
        result = await payment_service.get_payment_by_external_id(external_id)
        
        assert result is not None
        assert result.external_id == external_id
        mock_payment_repository.get_by_external_id.assert_called_once_with(external_id)
    
    @pytest.mark.asyncio
    async def test_list_payments(self, payment_service, mock_payment_repository):
        """Test listing payments with pagination."""
        payments = [
            Payment(
                id=uuid.uuid4(),
                amount=Decimal("10.00"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                external_id=f"pay_test_{i}"
            )
            for i in range(5)
        ]
        
        mock_payment_repository.list_payments.return_value = {
            "payments": payments,
            "total": 5
        }
        
        result = await payment_service.list_payments(page=1, per_page=10)
        
        assert result["payments"] == payments
        assert result["total"] == 5
        mock_payment_repository.list_payments.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_payment(self, payment_service, mock_payment_repository):
        """Test updating payment."""
        payment_id = uuid.uuid4()
        update_data = {
            "description": "Updated description",
            "metadata": {"updated": True}
        }
        
        existing_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123"
        )
        
        updated_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123",
            description="Updated description",
            metadata={"updated": True}
        )
        
        mock_payment_repository.get_by_id.return_value = existing_payment
        mock_payment_repository.update.return_value = updated_payment
        
        result = await payment_service.update_payment(payment_id, update_data)
        
        assert result.description == "Updated description"
        assert result.metadata == {"updated": True}
        mock_payment_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refund_payment(self, payment_service, mock_payment_repository, mock_authorize_net_client):
        """Test payment refund."""
        payment_id = uuid.uuid4()
        refund_amount = Decimal("5.00")
        
        existing_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123",
            status=PaymentStatus.CAPTURED,
            authorize_net_transaction_id="trans_123"
        )
        
        refunded_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123",
            status=PaymentStatus.REFUNDED,
            authorize_net_transaction_id="trans_123",
            refunded_amount=refund_amount,
            refund_count=1
        )
        
        mock_payment_repository.get_by_id.return_value = existing_payment
        mock_payment_repository.update.return_value = refunded_payment
        
        result = await payment_service.refund_payment(payment_id, refund_amount)
        
        assert result.refunded_amount == refund_amount
        assert result.refund_count == 1
        mock_authorize_net_client.refund.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_payment(self, payment_service, mock_payment_repository, mock_authorize_net_client):
        """Test payment cancellation."""
        payment_id = uuid.uuid4()
        
        existing_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123",
            status=PaymentStatus.AUTHORIZED,
            authorize_net_transaction_id="trans_123"
        )
        
        cancelled_payment = Payment(
            id=payment_id,
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            external_id="pay_test_123",
            status=PaymentStatus.CANCELLED,
            authorize_net_transaction_id="trans_123"
        )
        
        mock_payment_repository.get_by_id.return_value = existing_payment
        mock_payment_repository.update.return_value = cancelled_payment
        
        result = await payment_service.cancel_payment(payment_id)
        
        assert result.status == PaymentStatus.CANCELLED
        mock_authorize_net_client.void_transaction.assert_called_once()


class TestAuthService:
    """Comprehensive tests for AuthService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_api_key_repository(self):
        """Mock API key repository."""
        return AsyncMock()
    
    @pytest.fixture
    def auth_service(self, mock_db_session, mock_api_key_repository):
        """Create AuthService instance with mocked dependencies."""
        with patch('src.core.services.auth_service.APIKeyRepository', return_value=mock_api_key_repository):
            return AuthService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, auth_service, mock_api_key_repository):
        """Test API key creation."""
        api_key_data = {
            "name": "Test API Key",
            "description": "Test key for testing",
            "permissions": ["payments:read", "payments:write"],
            "rate_limit_per_minute": 100,
            "rate_limit_per_hour": 1000,
            "rate_limit_per_day": 10000
        }
        
        created_api_key = APIKey(
            id=uuid.uuid4(),
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            **api_key_data
        )
        
        mock_api_key_repository.create.return_value = created_api_key
        
        result = await auth_service.create_api_key(api_key_data)
        
        assert result is not None
        assert result.name == api_key_data["name"]
        assert result.permissions == api_key_data["permissions"]
        mock_api_key_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_api_key_by_id(self, auth_service, mock_api_key_repository):
        """Test getting API key by ID."""
        api_key_id = uuid.uuid4()
        api_key = APIKey(
            id=api_key_id,
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            name="Test API Key"
        )
        
        mock_api_key_repository.get_by_id.return_value = api_key
        
        result = await auth_service.get_api_key_by_id(api_key_id)
        
        assert result is not None
        assert result.id == api_key_id
        mock_api_key_repository.get_by_id.assert_called_once_with(api_key_id)
    
    @pytest.mark.asyncio
    async def test_list_api_keys(self, auth_service, mock_api_key_repository):
        """Test listing API keys."""
        api_keys = [
            APIKey(
                id=uuid.uuid4(),
                key_id=f"ak_test_{i}",
                key_secret_hash="hashed_secret",
                name=f"Test API Key {i}"
            )
            for i in range(3)
        ]
        
        mock_api_key_repository.list_api_keys.return_value = api_keys
        
        result = await auth_service.list_api_keys(skip=0, limit=10)
        
        assert len(result) == 3
        mock_api_key_repository.list_api_keys.assert_called_once_with(skip=0, limit=10)
    
    @pytest.mark.asyncio
    async def test_update_api_key(self, auth_service, mock_api_key_repository):
        """Test updating API key."""
        api_key_id = uuid.uuid4()
        update_data = {
            "name": "Updated API Key",
            "description": "Updated description"
        }
        
        existing_api_key = APIKey(
            id=api_key_id,
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            name="Test API Key"
        )
        
        updated_api_key = APIKey(
            id=api_key_id,
            key_id="ak_test_123",
            key_secret_hash="hashed_secret",
            name="Updated API Key",
            description="Updated description"
        )
        
        mock_api_key_repository.get_by_id.return_value = existing_api_key
        mock_api_key_repository.update.return_value = updated_api_key
        
        result = await auth_service.update_api_key(api_key_id, update_data)
        
        assert result.name == "Updated API Key"
        assert result.description == "Updated description"
        mock_api_key_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_api_key(self, auth_service, mock_api_key_repository):
        """Test deleting API key."""
        api_key_id = uuid.uuid4()
        
        mock_api_key_repository.delete.return_value = True
        
        result = await auth_service.delete_api_key(api_key_id)
        
        assert result is True
        mock_api_key_repository.delete.assert_called_once_with(api_key_id)
    
    @pytest.mark.asyncio
    async def test_authenticate_api_key(self, auth_service, mock_api_key_repository):
        """Test API key authentication."""
        key_id = "ak_test_123"
        key_secret = "sk_test_secret"
        
        api_key = APIKey(
            id=uuid.uuid4(),
            key_id=key_id,
            key_secret_hash="hashed_secret",
            name="Test API Key",
            status=APIKeyStatus.ACTIVE
        )
        
        mock_api_key_repository.get_by_key_id.return_value = api_key
        
        with patch('src.core.services.auth_service.verify_password', return_value=True):
            result = await auth_service.authenticate_api_key(key_id, key_secret)
        
        assert result is not None
        assert result.key_id == key_id
        mock_api_key_repository.get_by_key_id.assert_called_once_with(key_id)
    
    @pytest.mark.asyncio
    async def test_authenticate_api_key_invalid(self, auth_service, mock_api_key_repository):
        """Test API key authentication with invalid credentials."""
        key_id = "ak_test_123"
        key_secret = "invalid_secret"
        
        api_key = APIKey(
            id=uuid.uuid4(),
            key_id=key_id,
            key_secret_hash="hashed_secret",
            name="Test API Key",
            status=APIKeyStatus.ACTIVE
        )
        
        mock_api_key_repository.get_by_key_id.return_value = api_key
        
        with patch('src.core.services.auth_service.verify_password', return_value=False):
            with pytest.raises(AuthenticationError):
                await auth_service.authenticate_api_key(key_id, key_secret)


class TestWebhookService:
    """Comprehensive tests for WebhookService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_webhook_repository(self):
        """Mock webhook repository."""
        return AsyncMock()
    
    @pytest.fixture
    def webhook_service(self, mock_db_session, mock_webhook_repository):
        """Create WebhookService instance with mocked dependencies."""
        with patch('src.core.services.webhook_service.WebhookRepository', return_value=mock_webhook_repository):
            return WebhookService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_create_webhook(self, webhook_service, mock_webhook_repository):
        """Test webhook creation."""
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "is_active": True,
            "secret": "webhook_secret_123",
            "metadata": {"source": "test"}
        }
        
        created_webhook = Webhook(
            id=uuid.uuid4(),
            **webhook_data
        )
        
        mock_webhook_repository.create.return_value = created_webhook
        
        result = await webhook_service.create_webhook(webhook_data)
        
        assert result is not None
        assert result.webhook_url == webhook_data["webhook_url"]
        assert result.event_type == webhook_data["event_type"]
        mock_webhook_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_webhook_by_id(self, webhook_service, mock_webhook_repository):
        """Test getting webhook by ID."""
        webhook_id = uuid.uuid4()
        webhook = Webhook(
            id=webhook_id,
            webhook_url="https://example.com/webhook",
            event_type="payment.created"
        )
        
        mock_webhook_repository.get_by_id.return_value = webhook
        
        result = await webhook_service.get_webhook_by_id(webhook_id)
        
        assert result is not None
        assert result.id == webhook_id
        mock_webhook_repository.get_by_id.assert_called_once_with(webhook_id)
    
    @pytest.mark.asyncio
    async def test_list_webhooks(self, webhook_service, mock_webhook_repository):
        """Test listing webhooks."""
        webhooks = [
            Webhook(
                id=uuid.uuid4(),
                webhook_url=f"https://example.com/webhook{i}",
                event_type="payment.created"
            )
            for i in range(3)
        ]
        
        mock_webhook_repository.list_webhooks.return_value = webhooks
        
        result = await webhook_service.list_webhooks(skip=0, limit=10)
        
        assert len(result) == 3
        mock_webhook_repository.list_webhooks.assert_called_once_with(skip=0, limit=10)
    
    @pytest.mark.asyncio
    async def test_update_webhook(self, webhook_service, mock_webhook_repository):
        """Test updating webhook."""
        webhook_id = uuid.uuid4()
        update_data = {
            "is_active": False,
            "metadata": {"updated": True}
        }
        
        existing_webhook = Webhook(
            id=webhook_id,
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            is_active=True
        )
        
        updated_webhook = Webhook(
            id=webhook_id,
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            is_active=False,
            metadata={"updated": True}
        )
        
        mock_webhook_repository.get_by_id.return_value = existing_webhook
        mock_webhook_repository.update.return_value = updated_webhook
        
        result = await webhook_service.update_webhook(webhook_id, update_data)
        
        assert result.is_active is False
        assert result.metadata == {"updated": True}
        mock_webhook_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_webhook(self, webhook_service, mock_webhook_repository):
        """Test deleting webhook."""
        webhook_id = uuid.uuid4()
        
        mock_webhook_repository.delete.return_value = True
        
        result = await webhook_service.delete_webhook(webhook_id)
        
        assert result is True
        mock_webhook_repository.delete.assert_called_once_with(webhook_id)
    
    @pytest.mark.asyncio
    async def test_send_webhook(self, webhook_service, mock_webhook_repository):
        """Test sending webhook."""
        webhook_id = uuid.uuid4()
        payload = {"event": "payment.created", "data": {"payment_id": "pay_123"}}
        
        webhook = Webhook(
            id=webhook_id,
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            secret="webhook_secret_123"
        )
        
        mock_webhook_repository.get_by_id.return_value = webhook
        
        with patch('src.core.services.webhook_service.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await webhook_service.send_webhook(webhook_id, payload)
        
        assert result is not None
        mock_webhook_repository.get_by_id.assert_called_once_with(webhook_id)


class TestAuditLoggingService:
    """Comprehensive tests for AuditLoggingService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_audit_log_repository(self):
        """Mock audit log repository."""
        return AsyncMock()
    
    @pytest.fixture
    def audit_logging_service(self, mock_db_session, mock_audit_log_repository):
        """Create AuditLoggingService instance with mocked dependencies."""
        with patch('src.core.services.audit_logging_service.AuditLogRepository', return_value=mock_audit_log_repository):
            return AuditLoggingService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_log_payment_action(self, audit_logging_service, mock_audit_log_repository):
        """Test logging payment action."""
        payment_id = uuid.uuid4()
        action = "payment_created"
        message = "Payment created successfully"
        metadata = {"amount": "10.00", "currency": "USD"}
        
        audit_log = AuditLog(
            id=uuid.uuid4(),
            payment_id=payment_id,
            action=action,
            level=AuditLevel.INFO,
            message=message,
            entity_type="payment",
            entity_id=str(payment_id),
            audit_metadata=metadata
        )
        
        mock_audit_log_repository.create.return_value = audit_log
        
        result = await audit_logging_service.log_payment_action(
            payment_id, action, message, metadata
        )
        
        assert result is not None
        assert result.payment_id == payment_id
        assert result.action == action
        assert result.message == message
        mock_audit_log_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_error(self, audit_logging_service, mock_audit_log_repository):
        """Test logging error."""
        error_message = "Payment processing failed"
        error_code = "PAYMENT_ERROR"
        metadata = {"error_type": "validation", "field": "amount"}
        
        audit_log = AuditLog(
            id=uuid.uuid4(),
            action="error_occurred",
            level=AuditLevel.ERROR,
            message=error_message,
            entity_type="payment",
            entity_id=None,
            audit_metadata=metadata
        )
        
        mock_audit_log_repository.create.return_value = audit_log
        
        result = await audit_logging_service.log_error(
            error_message, error_code, metadata
        )
        
        assert result is not None
        assert result.level == AuditLevel.ERROR
        assert result.message == error_message
        mock_audit_log_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_audit_logs(self, audit_logging_service, mock_audit_log_repository):
        """Test getting audit logs."""
        payment_id = uuid.uuid4()
        audit_logs = [
            AuditLog(
                id=uuid.uuid4(),
                payment_id=payment_id,
                action="payment_created",
                level=AuditLevel.INFO,
                message="Payment created"
            ),
            AuditLog(
                id=uuid.uuid4(),
                payment_id=payment_id,
                action="payment_updated",
                level=AuditLevel.INFO,
                message="Payment updated"
            )
        ]
        
        mock_audit_log_repository.get_by_payment_id.return_value = audit_logs
        
        result = await audit_logging_service.get_audit_logs(payment_id)
        
        assert len(result) == 2
        assert all(log.payment_id == payment_id for log in result)
        mock_audit_log_repository.get_by_payment_id.assert_called_once_with(payment_id)


class TestRBACService:
    """Comprehensive tests for RBACService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def rbac_service(self, mock_db_session):
        """Create RBACService instance."""
        return RBACService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_check_permission(self, rbac_service):
        """Test permission checking."""
        user_id = "user_123"
        permission = "payments:write"
        
        with patch.object(rbac_service, '_get_user_permissions', return_value=["payments:read", "payments:write"]):
            result = await rbac_service.check_permission(user_id, permission)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_permission_denied(self, rbac_service):
        """Test permission checking when denied."""
        user_id = "user_123"
        permission = "admin:write"
        
        with patch.object(rbac_service, '_get_user_permissions', return_value=["payments:read", "payments:write"]):
            result = await rbac_service.check_permission(user_id, permission)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_roles(self, rbac_service):
        """Test getting user roles."""
        user_id = "user_123"
        roles = ["admin", "user"]
        
        with patch.object(rbac_service, '_get_user_roles', return_value=roles):
            result = await rbac_service.get_user_roles(user_id)
        
        assert result == roles


class TestAdvancedPaymentFeatures:
    """Comprehensive tests for AdvancedPaymentFeatures."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def advanced_features(self, mock_db_session):
        """Create AdvancedPaymentFeatures instance."""
        return AdvancedPaymentFeatures(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_generate_correlation_id(self, advanced_features):
        """Test correlation ID generation."""
        correlation_id = await advanced_features.generate_correlation_id()
        
        assert correlation_id is not None
        assert isinstance(correlation_id, str)
        assert correlation_id.startswith("corr_")
    
    @pytest.mark.asyncio
    async def test_track_payment_status_change(self, advanced_features):
        """Test payment status change tracking."""
        payment_id = uuid.uuid4()
        old_status = PaymentStatus.PENDING
        new_status = PaymentStatus.AUTHORIZED
        correlation_id = "corr_123"
        
        result = await advanced_features.track_payment_status_change(
            payment_id, old_status, new_status, correlation_id
        )
        
        assert result is None  # Method doesn't return anything
    
    @pytest.mark.asyncio
    async def test_store_payment_metadata(self, advanced_features):
        """Test payment metadata storage."""
        payment_id = uuid.uuid4()
        metadata = {"source": "web", "campaign": "summer_sale"}
        
        result = await advanced_features.store_payment_metadata(payment_id, metadata)
        
        assert result is None  # Method doesn't return anything
    
    @pytest.mark.asyncio
    async def test_get_payment_status_history(self, advanced_features):
        """Test getting payment status history."""
        payment_id = uuid.uuid4()
        
        result = await advanced_features.get_payment_status_history(payment_id)
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_search_payments(self, advanced_features):
        """Test payment search."""
        search_criteria = {
            "customer_id": "cust_123",
            "status": PaymentStatus.COMPLETED,
            "date_from": datetime.utcnow() - timedelta(days=30),
            "date_to": datetime.utcnow()
        }
        
        result = await advanced_features.search_payments(search_criteria)
        
        assert isinstance(result, list)


class TestServiceErrorHandling:
    """Test service error handling and edge cases."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session that raises exceptions."""
        session = AsyncMock()
        session.commit.side_effect = Exception("Database error")
        return session
    
    @pytest.mark.asyncio
    async def test_payment_service_database_error(self, mock_db_session):
        """Test PaymentService database error handling."""
        with patch('src.core.services.payment_service.PaymentRepository') as mock_repo:
            mock_repo.return_value.create.side_effect = DatabaseError("Database connection failed")
            
            payment_service = PaymentService(mock_db_session)
            
            with pytest.raises(DatabaseError):
                await payment_service.create_payment({
                    "amount": Decimal("10.00"),
                    "currency": "USD",
                    "payment_method": PaymentMethod.CREDIT_CARD
                })
    
    @pytest.mark.asyncio
    async def test_auth_service_validation_error(self, mock_db_session):
        """Test AuthService validation error handling."""
        with patch('src.core.services.auth_service.APIKeyRepository') as mock_repo:
            mock_repo.return_value.create.side_effect = ValidationError("Invalid API key data")
            
            auth_service = AuthService(mock_db_session)
            
            with pytest.raises(ValidationError):
                await auth_service.create_api_key({
                    "name": "",  # Invalid empty name
                    "permissions": ["invalid_permission"]
                })
    
    @pytest.mark.asyncio
    async def test_webhook_service_network_error(self, mock_db_session):
        """Test WebhookService network error handling."""
        with patch('src.core.services.webhook_service.WebhookRepository') as mock_repo:
            mock_repo.return_value.get_by_id.return_value = Webhook(
                id=uuid.uuid4(),
                webhook_url="https://example.com/webhook",
                event_type="payment.created"
            )
            
            webhook_service = WebhookService(mock_db_session)
            
            with patch('src.core.services.webhook_service.httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.post.side_effect = Exception("Network error")
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                with pytest.raises(Exception):
                    await webhook_service.send_webhook(uuid.uuid4(), {"test": "data"})


class TestServiceIntegration:
    """Test service integration and complex workflows."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for integration tests."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_payment_workflow(self, mock_db_session):
        """Test complete payment workflow."""
        # Mock dependencies
        with patch('src.core.services.payment_service.PaymentRepository') as mock_payment_repo:
            with patch('src.core.services.payment_service.AuthorizeNetClient') as mock_auth_client:
                with patch('src.core.services.audit_logging_service.AuditLogRepository') as mock_audit_repo:
                    
                    # Setup mocks
                    payment_service = PaymentService(mock_db_session)
                    audit_service = AuditLoggingService(mock_db_session)
                    
                    # Test payment creation workflow
                    payment_data = {
                        "amount": Decimal("10.00"),
                        "currency": "USD",
                        "payment_method": PaymentMethod.CREDIT_CARD,
                        "customer_id": "cust_123"
                    }
                    
                    created_payment = Payment(
                        id=uuid.uuid4(),
                        external_id="pay_test_123",
                        **payment_data
                    )
                    
                    mock_payment_repo.return_value.create.return_value = created_payment
                    mock_audit_repo.return_value.create.return_value = AuditLog(
                        id=uuid.uuid4(),
                        payment_id=created_payment.id,
                        action="payment_created",
                        level=AuditLevel.INFO,
                        message="Payment created"
                    )
                    
                    # Execute workflow
                    payment = await payment_service.create_payment(payment_data)
                    await audit_service.log_payment_action(
                        payment.id, "payment_created", "Payment created successfully"
                    )
                    
                    # Verify results
                    assert payment is not None
                    assert payment.amount == payment_data["amount"]
                    mock_payment_repo.return_value.create.assert_called_once()
                    mock_audit_repo.return_value.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_workflow(self, mock_db_session):
        """Test webhook delivery workflow."""
        with patch('src.core.services.webhook_service.WebhookRepository') as mock_webhook_repo:
            with patch('src.core.services.audit_logging_service.AuditLogRepository') as mock_audit_repo:
                
                webhook_service = WebhookService(mock_db_session)
                audit_service = AuditLoggingService(mock_db_session)
                
                webhook_id = uuid.uuid4()
                webhook = Webhook(
                    id=webhook_id,
                    webhook_url="https://example.com/webhook",
                    event_type="payment.created",
                    secret="webhook_secret_123"
                )
                
                mock_webhook_repo.return_value.get_by_id.return_value = webhook
                mock_audit_repo.return_value.create.return_value = AuditLog(
                    id=uuid.uuid4(),
                    action="webhook_sent",
                    level=AuditLevel.INFO,
                    message="Webhook sent successfully"
                )
                
                with patch('src.core.services.webhook_service.httpx.AsyncClient') as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"status": "success"}
                    
                    mock_client_instance = AsyncMock()
                    mock_client_instance.post.return_value = mock_response
                    mock_client.return_value.__aenter__.return_value = mock_client_instance
                    
                    # Execute workflow
                    payload = {"event": "payment.created", "data": {"payment_id": "pay_123"}}
                    result = await webhook_service.send_webhook(webhook_id, payload)
                    await audit_service.log_payment_action(
                        None, "webhook_sent", "Webhook sent successfully"
                    )
                    
                    # Verify results
                    assert result is not None
                    mock_webhook_repo.return_value.get_by_id.assert_called_once_with(webhook_id)
                    mock_audit_repo.return_value.create.assert_called_once()
