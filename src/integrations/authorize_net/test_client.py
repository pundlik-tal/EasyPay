"""
EasyPay Payment Gateway - Authorize.net Client Tests
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from httpx import Response

from .client import AuthorizeNetClient
from .models import CreditCard, BillingAddress, AuthorizeNetCredentials
from .exceptions import AuthorizeNetAuthenticationError, AuthorizeNetTransactionError


@pytest.fixture
def credentials():
    """Test credentials."""
    return AuthorizeNetCredentials(
        api_login_id="test_login_id",
        transaction_key="test_transaction_key",
        sandbox=True
    )


@pytest.fixture
def credit_card():
    """Test credit card."""
    return CreditCard(
        card_number="4111111111111111",
        expiration_date="1225",
        card_code="123"
    )


@pytest.fixture
def billing_address():
    """Test billing address."""
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
def client(credentials):
    """Test client."""
    return AuthorizeNetClient(credentials)


@pytest.mark.asyncio
async def test_authentication_success(client):
    """Test successful authentication."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.test_authentication()
        assert result is True


@pytest.mark.asyncio
async def test_authentication_failure(client):
    """Test authentication failure."""
    mock_response = {
        "messages": {
            "resultCode": "Error",
            "message": [{"code": "E00007", "text": "User authentication failed."}]
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        with pytest.raises(AuthorizeNetAuthenticationError):
            await client.test_authentication()


@pytest.mark.asyncio
async def test_charge_credit_card_success(client, credit_card, billing_address):
    """Test successful credit card charge."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "1",
            "responseText": "This transaction has been approved.",
            "transId": "1234567890",
            "authCode": "ABC123",
            "avsResultCode": "Y",
            "cvvResultCode": "M",
            "amount": "10.00"
        },
        "refId": "test_ref"
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.charge_credit_card(
            amount="10.00",
            credit_card=credit_card,
            billing_address=billing_address,
            ref_id="test_ref"
        )
        
        assert result.transaction_id == "1234567890"
        assert result.status.value == "captured"
        assert result.response_code == "1"
        assert result.auth_code == "ABC123"


@pytest.mark.asyncio
async def test_charge_credit_card_declined(client, credit_card, billing_address):
    """Test declined credit card charge."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "2",
            "responseText": "This transaction has been declined.",
            "transId": "1234567890",
            "amount": "10.00"
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.charge_credit_card(
            amount="10.00",
            credit_card=credit_card,
            billing_address=billing_address
        )
        
        assert result.transaction_id == "1234567890"
        assert result.status.value == "declined"
        assert result.response_code == "2"


@pytest.mark.asyncio
async def test_authorize_only_success(client, credit_card, billing_address):
    """Test successful authorization only."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "1",
            "responseText": "This transaction has been approved.",
            "transId": "1234567890",
            "authCode": "ABC123",
            "amount": "10.00"
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.authorize_only(
            amount="10.00",
            credit_card=credit_card,
            billing_address=billing_address
        )
        
        assert result.transaction_id == "1234567890"
        assert result.status.value == "captured"
        assert result.response_code == "1"


@pytest.mark.asyncio
async def test_capture_success(client):
    """Test successful capture."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "1",
            "responseText": "This transaction has been approved.",
            "transId": "1234567891",
            "amount": "10.00"
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.capture(
            transaction_id="1234567890",
            amount="10.00"
        )
        
        assert result.transaction_id == "1234567891"
        assert result.status.value == "captured"
        assert result.response_code == "1"


@pytest.mark.asyncio
async def test_refund_success(client, credit_card):
    """Test successful refund."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "1",
            "responseText": "This transaction has been approved.",
            "transId": "1234567892",
            "amount": "5.00"
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.refund(
            transaction_id="1234567890",
            amount="5.00",
            credit_card=credit_card
        )
        
        assert result.transaction_id == "1234567892"
        assert result.status.value == "captured"
        assert result.response_code == "1"


@pytest.mark.asyncio
async def test_void_success(client):
    """Test successful void."""
    mock_response = {
        "messages": {
            "resultCode": "Ok",
            "message": [{"code": "I00001", "text": "Successful."}]
        },
        "transactionResponse": {
            "responseCode": "1",
            "responseText": "This transaction has been approved.",
            "transId": "1234567893"
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        result = await client.void_transaction(
            transaction_id="1234567890"
        )
        
        assert result.transaction_id == "1234567893"
        assert result.status.value == "captured"
        assert result.response_code == "1"


@pytest.mark.asyncio
async def test_transaction_error(client, credit_card, billing_address):
    """Test transaction error response."""
    mock_response = {
        "messages": {
            "resultCode": "Error",
            "message": [{"code": "E00027", "text": "The transaction was unsuccessful."}]
        }
    }
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None
        
        with pytest.raises(AuthorizeNetTransactionError) as exc_info:
            await client.charge_credit_card(
                amount="10.00",
                credit_card=credit_card,
                billing_address=billing_address
            )
        
        assert "E00027" in str(exc_info.value)


@pytest.mark.asyncio
async def test_network_error(client, credit_card, billing_address):
    """Test network error handling."""
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):  # Should raise AuthorizeNetNetworkError
            await client.charge_credit_card(
                amount="10.00",
                credit_card=credit_card,
                billing_address=billing_address
            )


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    credentials = AuthorizeNetCredentials(
        api_login_id="test_login_id",
        transaction_key="test_transaction_key",
        sandbox=True
    )
    
    async with AuthorizeNetClient(credentials) as client:
        assert client is not None
        # Client should be properly closed when exiting context
