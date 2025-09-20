"""
EasyPay Payment Gateway - Extended Authorize.net Client Tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    CreditCard,
    BillingAddress,
    TransactionRequest,
    TransactionResponse
)
from src.integrations.authorize_net.exceptions import (
    AuthorizeNetError,
    AuthenticationError,
    ValidationError,
    TransactionError,
    NetworkError
)


class TestAuthorizeNetClientExtended:
    """Extended tests for Authorize.net client."""
    
    @pytest.fixture
    def client(self):
        """Create Authorize.net client instance."""
        return AuthorizeNetClient(
            api_login_id="test_login",
            transaction_key="test_key",
            sandbox=True
        )
    
    @pytest.fixture
    def sample_credit_card(self):
        """Sample credit card for testing."""
        return CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
    
    @pytest.fixture
    def sample_billing_address(self):
        """Sample billing address for testing."""
        return BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
    
    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.api_login_id == "test_login"
        assert client.transaction_key == "test_key"
        assert client.sandbox is True
        assert client.base_url is not None
    
    def test_client_initialization_production(self):
        """Test client initialization for production."""
        client = AuthorizeNetClient(
            api_login_id="prod_login",
            transaction_key="prod_key",
            sandbox=False
        )
        assert client.sandbox is False
        assert "sandbox" not in client.base_url
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_test_authentication_success(self, mock_client_class, client):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            }
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.test_authentication()
        assert result is True
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_test_authentication_failure(self, mock_client_class, client):
        """Test failed authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Authentication failed."}]
            }
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.test_authentication()
        assert result is False
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_charge_credit_card_success(self, mock_client_class, client, sample_credit_card, sample_billing_address):
        """Test successful credit card charge."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved",
                "authCode": "AUTH123",
                "avsResultCode": "Y",
                "cvvResultCode": "M",
                "amount": "10.00"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.charge_credit_card(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address
        )
        
        assert result is not None
        assert result.transaction_id == "test_trans_123"
        assert result.status == "approved"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_charge_credit_card_declined(self, mock_client_class, client, sample_credit_card, sample_billing_address):
        """Test declined credit card charge."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "2",
                "responseText": "Declined",
                "amount": "10.00"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.charge_credit_card(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address
        )
        
        assert result is not None
        assert result.status == "declined"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_authorize_only(self, mock_client_class, client, sample_credit_card, sample_billing_address):
        """Test authorize only transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved",
                "authCode": "AUTH123",
                "amount": "10.00"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.authorize_only(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address
        )
        
        assert result is not None
        assert result.status == "authorized_pending_capture"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_capture(self, mock_client_class, client):
        """Test capture transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved",
                "amount": "10.00"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.capture(
            transaction_id="test_trans_123",
            amount=Decimal("10.00")
        )
        
        assert result is not None
        assert result.status == "captured"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_refund(self, mock_client_class, client):
        """Test refund transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved",
                "amount": "5.00"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.refund(
            transaction_id="test_trans_123",
            amount=Decimal("5.00")
        )
        
        assert result is not None
        assert result.status == "refunded"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_void_transaction(self, mock_client_class, client):
        """Test void transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            },
            "refId": "ref_123"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await client.void_transaction("test_trans_123")
        
        assert result is not None
        assert result.status == "voided"
    
    @patch('src.integrations.authorize_net.client.httpx.AsyncClient')
    async def test_network_error(self, mock_client_class, client, sample_credit_card, sample_billing_address):
        """Test network error handling."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(NetworkError):
            await client.charge_credit_card(
                amount=Decimal("10.00"),
                credit_card=sample_credit_card,
                billing_address=sample_billing_address
            )
    
    def test_validate_amount(self, client):
        """Test amount validation."""
        # Valid amounts
        assert client._validate_amount(Decimal("10.00")) is True
        assert client._validate_amount(Decimal("0.01")) is True
        assert client._validate_amount(Decimal("999999.99")) is True
        
        # Invalid amounts
        with pytest.raises(ValidationError):
            client._validate_amount(Decimal("0.00"))
        
        with pytest.raises(ValidationError):
            client._validate_amount(Decimal("-10.00"))
        
        with pytest.raises(ValidationError):
            client._validate_amount(Decimal("1000000.00"))
    
    def test_validate_credit_card(self, client):
        """Test credit card validation."""
        # Valid credit card
        valid_card = CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
        assert client._validate_credit_card(valid_card) is True
        
        # Invalid credit card
        invalid_card = CreditCard(
            card_number="1234567890123456",
            expiration_date="1225",
            card_code="123"
        )
        with pytest.raises(ValidationError):
            client._validate_credit_card(invalid_card)
    
    def test_validate_billing_address(self, client):
        """Test billing address validation."""
        # Valid billing address
        valid_address = BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
        assert client._validate_billing_address(valid_address) is True
        
        # Invalid billing address (missing required fields)
        invalid_address = BillingAddress(
            first_name="",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
        with pytest.raises(ValidationError):
            client._validate_billing_address(invalid_address)
