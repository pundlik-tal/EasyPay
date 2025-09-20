"""
EasyPay Payment Gateway - Test Configuration
"""
import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

# from src.main import app  # Commented out to avoid circular import during testing
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.audit_log import AuditLog
from src.core.models.webhook import Webhook
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest
)
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
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


# @pytest.fixture
# async def test_client() -> AsyncGenerator[AsyncClient, None]:
#     """Create a test HTTP client."""
#     async with AsyncClient(app=app, base_url="http://test") as client:
#         yield client


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
def sample_audit_log_data() -> Dict[str, Any]:
    """Sample audit log data."""
    return {
        "payment_id": uuid.uuid4(),
        "action": "payment_created",
        "level": "info",
        "message": "Test payment created",
        "entity_type": "payment",
        "entity_id": str(uuid.uuid4()),
        "audit_metadata": {"test": True},
        "user_id": None,
        "ip_address": "127.0.0.1",
        "user_agent": "test-agent"
    }


@pytest.fixture
def sample_webhook_data() -> Dict[str, Any]:
    """Sample webhook data."""
    return {
        "webhook_url": "https://example.com/webhook",
        "event_type": "payment.created",
        "is_active": True,
        "secret": "webhook_secret_123",
        "metadata": {"source": "test"}
    }


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
