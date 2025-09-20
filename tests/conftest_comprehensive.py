"""
Comprehensive test configuration for achieving 80%+ coverage.
"""
import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

# Import all models for comprehensive testing
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus, Token, TokenType
from src.core.models.audit_log import AuditLog, AuditLevel
from src.core.models.webhook import Webhook, WebhookStatus, WebhookEvent
from src.core.models.rbac import Role, Permission, UserRole, RolePermission

# Import schemas for comprehensive testing
from src.api.v1.schemas.payment import (
    PaymentCreateRequest, PaymentUpdateRequest, PaymentRefundRequest, PaymentCancelRequest
)
from src.api.v1.schemas.auth import (
    APIKeyCreateRequest, APIKeyUpdateRequest, TokenRequest
)
from src.api.v1.schemas.webhook import (
    WebhookCreateRequest, WebhookUpdateRequest
)

# Import exceptions for comprehensive testing
from src.core.exceptions import (
    PaymentError, PaymentNotFoundError, ValidationError,
    AuthenticationError, AuthorizationError, DatabaseError,
    ExternalServiceError, EasyPayException
)

# Import integration models
from src.integrations.authorize_net.models import CreditCard, BillingAddress


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Payment.metadata.create_all)
        await conn.run_sync(AuditLog.metadata.create_all)
        await conn.run_sync(Webhook.metadata.create_all)
        await conn.run_sync(APIKey.metadata.create_all)
        await conn.run_sync(Token.metadata.create_all)
        await conn.run_sync(Role.metadata.create_all)
        await conn.run_sync(Permission.metadata.create_all)
        await conn.run_sync(UserRole.metadata.create_all)
        await conn.run_sync(RolePermission.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_payment_data() -> Dict[str, Any]:
    """Sample payment creation data."""
    return {
        "amount": Decimal("10.00"),
        "currency": "USD",
        "payment_method": PaymentMethod.CREDIT_CARD.value,
        "customer_id": "cust_123",
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "card_token": "tok_123456789",
        "description": "Test payment",
        "metadata": {"order_id": "order_123", "source": "test"},
        "is_test": True
    }


@pytest.fixture
def sample_payment_create_request(sample_payment_data) -> PaymentCreateRequest:
    """Sample payment create request."""
    return PaymentCreateRequest(**sample_payment_data)


@pytest.fixture
def sample_payment_update_request() -> PaymentUpdateRequest:
    """Sample payment update request."""
    return PaymentUpdateRequest(
        description="Updated description",
        metadata={"updated": True, "timestamp": datetime.utcnow().isoformat()}
    )


@pytest.fixture
def sample_payment_refund_request() -> PaymentRefundRequest:
    """Sample payment refund request."""
    return PaymentRefundRequest(
        amount=Decimal("5.00"),
        reason="Customer request",
        metadata={"refund_reason": "customer_request"}
    )


@pytest.fixture
def sample_payment_cancel_request() -> PaymentCancelRequest:
    """Sample payment cancel request."""
    return PaymentCancelRequest(
        reason="Customer cancelled",
        metadata={"cancellation_reason": "customer_cancelled"}
    )


@pytest.fixture
def sample_api_key_data() -> Dict[str, Any]:
    """Sample API key creation data."""
    return {
        "name": "Test API Key",
        "description": "API key for testing",
        "permissions": ["payments:read", "payments:write"],
        "rate_limit_per_minute": 100,
        "rate_limit_per_hour": 1000,
        "rate_limit_per_day": 10000
    }


@pytest.fixture
def sample_api_key_create_request(sample_api_key_data) -> APIKeyCreateRequest:
    """Sample API key create request."""
    return APIKeyCreateRequest(**sample_api_key_data)


@pytest.fixture
def sample_api_key_update_request() -> APIKeyUpdateRequest:
    """Sample API key update request."""
    return APIKeyUpdateRequest(
        name="Updated API Key",
        description="Updated description"
    )


@pytest.fixture
def sample_token_request() -> TokenRequest:
    """Sample token request."""
    return TokenRequest(
        key_id="ak_test_123",
        key_secret="sk_test_secret"
    )


@pytest.fixture
def sample_webhook_data() -> Dict[str, Any]:
    """Sample webhook creation data."""
    return {
        "webhook_url": "https://example.com/webhook",
        "event_type": "payment.created",
        "is_active": True,
        "secret": "webhook_secret_123",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_webhook_create_request(sample_webhook_data) -> WebhookCreateRequest:
    """Sample webhook create request."""
    return WebhookCreateRequest(**sample_webhook_data)


@pytest.fixture
def sample_webhook_update_request() -> WebhookUpdateRequest:
    """Sample webhook update request."""
    return WebhookUpdateRequest(
        is_active=False,
        metadata={"updated": True}
    )


@pytest.fixture
def sample_credit_card() -> CreditCard:
    """Sample credit card data."""
    return CreditCard(
        card_number="4111111111111111",
        expiration_date="1225",
        card_code="123"
    )


@pytest.fixture
def sample_billing_address() -> BillingAddress:
    """Sample billing address data."""
    return BillingAddress(
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        city="Anytown",
        state="CA",
        zip="12345",
        country="US"
    )


@pytest.fixture
async def sample_payment(test_db_session: AsyncSession, sample_payment_data) -> Payment:
    """Create a sample payment in the database."""
    payment_data = sample_payment_data.copy()
    payment_data["external_id"] = f"pay_{uuid.uuid4().hex[:12]}"
    payment_data["status"] = PaymentStatus.PENDING
    
    payment = Payment(**payment_data)
    test_db_session.add(payment)
    await test_db_session.commit()
    await test_db_session.refresh(payment)
    return payment


@pytest.fixture
async def sample_api_key(test_db_session: AsyncSession, sample_api_key_data) -> APIKey:
    """Create a sample API key in the database."""
    api_key_data = sample_api_key_data.copy()
    api_key_data["key_id"] = f"ak_{uuid.uuid4().hex[:12]}"
    api_key_data["key_secret_hash"] = "hashed_secret"
    api_key_data["status"] = APIKeyStatus.ACTIVE
    
    api_key = APIKey(**api_key_data)
    test_db_session.add(api_key)
    await test_db_session.commit()
    await test_db_session.refresh(api_key)
    return api_key


@pytest.fixture
async def sample_webhook(test_db_session: AsyncSession, sample_webhook_data) -> Webhook:
    """Create a sample webhook in the database."""
    webhook_data = sample_webhook_data.copy()
    webhook_data["status"] = WebhookStatus.PENDING
    
    webhook = Webhook(**webhook_data)
    test_db_session.add(webhook)
    await test_db_session.commit()
    await test_db_session.refresh(webhook)
    return webhook


@pytest.fixture
async def sample_audit_log(test_db_session: AsyncSession) -> AuditLog:
    """Create a sample audit log in the database."""
    audit_log_data = {
        "payment_id": uuid.uuid4(),
        "action": "payment_created",
        "level": AuditLevel.INFO,
        "message": "Test payment created",
        "entity_type": "payment",
        "entity_id": str(uuid.uuid4()),
        "audit_metadata": {"test": True},
        "user_id": None,
        "ip_address": "127.0.0.1",
        "user_agent": "test-agent"
    }
    
    audit_log = AuditLog(**audit_log_data)
    test_db_session.add(audit_log)
    await test_db_session.commit()
    await test_db_session.refresh(audit_log)
    return audit_log


@pytest.fixture
def mock_authorize_net_client():
    """Mock Authorize.net client."""
    mock_client = AsyncMock()
    
    # Mock successful responses
    mock_response = MagicMock()
    mock_response.transaction_id = "test_trans_123"
    mock_response.status = "captured"
    mock_response.response_code = "1"
    mock_response.response_text = "Approved"
    mock_response.auth_code = "AUTH123"
    mock_response.amount = "10.00"
    
    mock_client.test_authentication.return_value = True
    mock_client.charge_credit_card.return_value = mock_response
    mock_client.authorize_only.return_value = mock_response
    mock_client.capture.return_value = mock_response
    mock_client.refund.return_value = mock_response
    mock_client.void_transaction.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_cache_client():
    """Mock cache client."""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    mock_cache.exists.return_value = False
    return mock_cache


@pytest.fixture
def mock_advanced_features():
    """Mock advanced payment features."""
    mock_features = AsyncMock()
    
    # Mock correlation manager
    mock_correlation_manager = MagicMock()
    mock_correlation_manager.generate_correlation_id.return_value = f"corr_{uuid.uuid4().hex[:12]}"
    mock_features.correlation_manager = mock_correlation_manager
    
    # Mock other methods
    mock_features.track_payment_status_change.return_value = None
    mock_features.store_payment_metadata.return_value = None
    mock_features.update_payment_metadata.return_value = None
    mock_features.get_payment_status_history.return_value = []
    mock_features.get_payment_metadata.return_value = {}
    mock_features.search_payments.return_value = []
    mock_features.get_circuit_breaker_metrics.return_value = {}
    
    return mock_features


@pytest.fixture
def mock_payment_repository():
    """Mock payment repository."""
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Payment(
        id=uuid.uuid4(),
        amount=Decimal("10.00"),
        currency="USD",
        payment_method=PaymentMethod.CREDIT_CARD,
        external_id="pay_test_123"
    )
    mock_repo.get_by_id.return_value = None
    mock_repo.get_by_external_id.return_value = None
    mock_repo.list_payments.return_value = {"payments": [], "total": 0}
    mock_repo.update.return_value = None
    mock_repo.delete.return_value = True
    return mock_repo


@pytest.fixture
def mock_api_key_repository():
    """Mock API key repository."""
    mock_repo = AsyncMock()
    mock_repo.create.return_value = APIKey(
        id=uuid.uuid4(),
        key_id="ak_test_123",
        key_secret_hash="hashed_secret",
        name="Test API Key"
    )
    mock_repo.get_by_id.return_value = None
    mock_repo.get_by_key_id.return_value = None
    mock_repo.list_api_keys.return_value = []
    mock_repo.update.return_value = None
    mock_repo.delete.return_value = True
    return mock_repo


@pytest.fixture
def mock_webhook_repository():
    """Mock webhook repository."""
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Webhook(
        id=uuid.uuid4(),
        webhook_url="https://example.com/webhook",
        event_type="payment.created"
    )
    mock_repo.get_by_id.return_value = None
    mock_repo.list_webhooks.return_value = []
    mock_repo.update.return_value = None
    mock_repo.delete.return_value = True
    return mock_repo


@pytest.fixture
def mock_audit_log_repository():
    """Mock audit log repository."""
    mock_repo = AsyncMock()
    mock_repo.create.return_value = AuditLog(
        id=uuid.uuid4(),
        action="test_action",
        level=AuditLevel.INFO,
        message="Test message"
    )
    mock_repo.get_by_payment_id.return_value = []
    return mock_repo


# Test data factories
class PaymentFactory:
    """Factory for creating test payment data."""
    
    @staticmethod
    def create_payment_data(**overrides) -> Dict[str, Any]:
        """Create payment data with optional overrides."""
        data = {
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": f"cust_{uuid.uuid4().hex[:8]}",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": f"tok_{uuid.uuid4().hex[:12]}",
            "description": "Test payment",
            "metadata": {"test": True},
            "is_test": True
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_payment_with_status(status: PaymentStatus, **overrides) -> Dict[str, Any]:
        """Create payment data with specific status."""
        data = PaymentFactory.create_payment_data(**overrides)
        data["status"] = status
        return data


class APIKeyFactory:
    """Factory for creating test API key data."""
    
    @staticmethod
    def create_api_key_data(**overrides) -> Dict[str, Any]:
        """Create API key data with optional overrides."""
        data = {
            "name": f"Test API Key {uuid.uuid4().hex[:8]}",
            "description": "Test API key",
            "permissions": ["payments:read", "payments:write"],
            "rate_limit_per_minute": 100,
            "rate_limit_per_hour": 1000,
            "rate_limit_per_day": 10000
        }
        data.update(overrides)
        return data


class WebhookFactory:
    """Factory for creating test webhook data."""
    
    @staticmethod
    def create_webhook_data(**overrides) -> Dict[str, Any]:
        """Create webhook data with optional overrides."""
        data = {
            "webhook_url": f"https://example.com/webhook/{uuid.uuid4().hex[:8]}",
            "event_type": "payment.created",
            "is_active": True,
            "secret": f"webhook_secret_{uuid.uuid4().hex[:12]}",
            "metadata": {"test": True}
        }
        data.update(overrides)
        return data


class AuthorizeNetResponseFactory:
    """Factory for creating test Authorize.net responses."""
    
    @staticmethod
    def create_success_response(**overrides) -> Dict[str, Any]:
        """Create a successful transaction response."""
        response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": f"test_trans_{uuid.uuid4().hex[:12]}",
                "responseCode": "1",
                "responseText": "Approved",
                "authCode": f"AUTH{uuid.uuid4().hex[:6]}",
                "avsResultCode": "Y",
                "cvvResultCode": "M",
                "amount": "10.00"
            },
            "refId": f"ref_{uuid.uuid4().hex[:8]}"
        }
        response.update(overrides)
        return response
    
    @staticmethod
    def create_error_response(error_code: str = "E00001", error_text: str = "Error", **overrides) -> Dict[str, Any]:
        """Create an error transaction response."""
        response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": error_code, "text": error_text}]
            }
        }
        response.update(overrides)
        return response


# Test utilities
class TestUtils:
    """Utility functions for tests."""
    
    @staticmethod
    def assert_payment_response(response_data: Dict[str, Any], expected_data: Dict[str, Any]):
        """Assert payment response matches expected data."""
        for key, expected_value in expected_data.items():
            if key in response_data:
                assert response_data[key] == expected_value, f"Expected {key}={expected_value}, got {response_data[key]}"
    
    @staticmethod
    def assert_error_response(response_data: Dict[str, Any], expected_status: int, expected_message: str = None):
        """Assert error response format."""
        assert "detail" in response_data
        if expected_message:
            assert expected_message in response_data["detail"]
    
    @staticmethod
    def create_test_payment_id() -> str:
        """Create a test payment ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def create_test_external_id() -> str:
        """Create a test external ID."""
        return f"pay_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def create_test_api_key_id() -> str:
        """Create a test API key ID."""
        return f"ak_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def create_test_webhook_id() -> str:
        """Create a test webhook ID."""
        return f"webhook_{uuid.uuid4().hex[:12]}"


# Comprehensive test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "coverage: mark test as coverage-focused"
    )


# Coverage collection configuration
@pytest.fixture(autouse=True)
def coverage_collection():
    """Automatically collect coverage for all tests."""
    pass
