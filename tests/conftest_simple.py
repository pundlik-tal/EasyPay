"""
EasyPay Payment Gateway - Simple Test Configuration
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
        "payment_method": "credit_card",
        "customer_id": "cust_123",
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "card_token": "tok_123456789",
        "description": "Test payment",
        "metadata": {"order_id": "order_123", "source": "test"},
        "is_test": True
    }


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


# Test data factories
class PaymentFactory:
    """Factory for creating test payment data."""
    
    @staticmethod
    def create_payment_data(**overrides) -> Dict[str, Any]:
        """Create payment data with optional overrides."""
        data = {
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": "credit_card",
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
