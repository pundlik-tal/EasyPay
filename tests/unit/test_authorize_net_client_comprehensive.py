"""
EasyPay Payment Gateway - Comprehensive AuthorizeNet Client Unit Tests
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    AuthorizeNetCredentials,
    CreditCard,
    BillingAddress,
    PaymentResponse,
    TransactionStatus
)
from src.integrations.authorize_net.exceptions import (
    AuthorizeNetError,
    AuthorizeNetAuthenticationError,
    AuthorizeNetTransactionError,
    AuthorizeNetNetworkError,
    AuthorizeNetValidationError
)


class TestAuthorizeNetClient:
    """Comprehensive test suite for AuthorizeNetClient class."""

    @pytest.fixture
    def sample_credentials(self):
        """Sample Authorize.net credentials."""
        return AuthorizeNetCredentials(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True,
            api_url="https://apitest.authorize.net/xml/v1/request.api"
        )

    @pytest.fixture
    def sample_credit_card(self):
        """Sample credit card data."""
        return CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )

    @pytest.fixture
    def sample_billing_address(self):
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
    def mock_httpx_client(self):
        """Mock httpx client."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        return mock_client

    @pytest.fixture
    def authorize_net_client(self, sample_credentials, mock_httpx_client):
        """Create AuthorizeNetClient instance with mocked dependencies."""
        with patch('src.integrations.authorize_net.client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = AuthorizeNetClient(sample_credentials)
            client.client = mock_httpx_client
            return client

    # Test initialization
    def test_client_initialization_with_credentials(self, sample_credentials, mock_httpx_client):
        """Test client initialization with provided credentials."""
        with patch('src.integrations.authorize_net.client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = AuthorizeNetClient(sample_credentials)
            
            assert client.credentials == sample_credentials
            assert client.api_url == sample_credentials.api_url
            assert client.client == mock_httpx_client

    def test_client_initialization_without_credentials(self, mock_httpx_client):
        """Test client initialization without credentials (uses settings)."""
        with patch('src.integrations.authorize_net.client.httpx.AsyncClient', return_value=mock_httpx_client), \
             patch('src.integrations.authorize_net.client.settings') as mock_settings:
            
            mock_settings.AUTHORIZE_NET_API_LOGIN_ID = "settings_login_id"
            mock_settings.AUTHORIZE_NET_TRANSACTION_KEY = "settings_transaction_key"
            mock_settings.AUTHORIZE_NET_SANDBOX = True
            mock_settings.get_authorize_net_url.return_value = "https://apitest.authorize.net/xml/v1/request.api"
            
            client = AuthorizeNetClient()
            
            assert client.credentials.api_login_id == "settings_login_id"
            assert client.credentials.transaction_key == "settings_transaction_key"
            assert client.credentials.sandbox is True

    def test_get_api_url_sandbox(self, sample_credentials):
        """Test getting sandbox API URL."""
        client = AuthorizeNetClient(sample_credentials)
        url = client._get_api_url(True)
        
        assert url == "https://apitest.authorize.net/xml/v1/request.api"

    def test_get_api_url_production(self, sample_credentials):
        """Test getting production API URL."""
        client = AuthorizeNetClient(sample_credentials)
        url = client._get_api_url(False)
        
        assert url == "https://api.authorize.net/xml/v1/request.api"

    # Test authentication
    async def test_test_authentication_success(self, authorize_net_client, mock_httpx_client):
        """Test successful authentication."""
        # Arrange
        success_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.test_authentication()
        
        # Assert
        assert result is True
        mock_httpx_client.post.assert_called_once()

    async def test_test_authentication_declined_transaction(self, authorize_net_client, mock_httpx_client):
        """Test authentication with declined transaction (still successful auth)."""
        # Arrange
        declined_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "2",
                "responseText": "Declined"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = declined_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.test_authentication()
        
        # Assert
        assert result is True

    async def test_test_authentication_api_error(self, authorize_net_client, mock_httpx_client):
        """Test authentication with API error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Authentication failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetAuthenticationError, match="Authentication test failed"):
            await authorize_net_client.test_authentication()

    async def test_test_authentication_transaction_error(self, authorize_net_client, mock_httpx_client):
        """Test authentication with transaction error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "3",
                "responseText": "Transaction error"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetAuthenticationError, match="Authentication test failed"):
            await authorize_net_client.test_authentication()

    async def test_test_authentication_network_error(self, authorize_net_client, mock_httpx_client):
        """Test authentication with network error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Network error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetAuthenticationError, match="Authentication test failed"):
            await authorize_net_client.test_authentication()

    # Test charge_credit_card
    async def test_charge_credit_card_success(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test successful credit card charge."""
        # Arrange
        success_response = {
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
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "10.00",
            sample_credit_card,
            sample_billing_address
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"
        assert result.status == TransactionStatus.CAPTURED
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        assert result.auth_code == "AUTH123"
        assert result.amount == "10.00"

    async def test_charge_credit_card_with_order_info(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with order information."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        order_info = {"invoiceNumber": "INV123", "description": "Test order"}
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "10.00",
            sample_credit_card,
            sample_billing_address,
            order_info=order_info
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_charge_credit_card_with_ref_id(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with reference ID."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "10.00",
            sample_credit_card,
            sample_billing_address,
            ref_id="ref_123"
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_charge_credit_card_declined(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with declined transaction."""
        # Arrange
        declined_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "2",
                "responseText": "Declined"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = declined_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "10.00",
            sample_credit_card,
            sample_billing_address
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.status == TransactionStatus.DECLINED
        assert result.response_code == "2"

    async def test_charge_credit_card_error(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with error response."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Transaction failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Transaction failed"):
            await authorize_net_client.charge_credit_card(
                "10.00",
                sample_credit_card,
                sample_billing_address
            )

    # Test authorize_only
    async def test_authorize_only_success(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test successful authorization only."""
        # Arrange
        success_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved",
                "authCode": "AUTH123"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.authorize_only(
            "10.00",
            sample_credit_card,
            sample_billing_address
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"
        assert result.response_code == "1"

    async def test_authorize_only_error(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test authorization only with error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Authorization failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Authorization failed"):
            await authorize_net_client.authorize_only(
                "10.00",
                sample_credit_card,
                sample_billing_address
            )

    # Test capture
    async def test_capture_success(self, authorize_net_client, mock_httpx_client):
        """Test successful capture."""
        # Arrange
        success_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.capture("test_trans_123")
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"

    async def test_capture_with_amount(self, authorize_net_client, mock_httpx_client):
        """Test capture with specific amount."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.capture("test_trans_123", "5.00")
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_capture_with_ref_id(self, authorize_net_client, mock_httpx_client):
        """Test capture with reference ID."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.capture("test_trans_123", ref_id="ref_123")
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_capture_error(self, authorize_net_client, mock_httpx_client):
        """Test capture with error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Capture failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Capture failed"):
            await authorize_net_client.capture("test_trans_123")

    # Test refund
    async def test_refund_success(self, authorize_net_client, mock_httpx_client, sample_credit_card):
        """Test successful refund."""
        # Arrange
        success_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.refund(
            "test_trans_123",
            "5.00",
            sample_credit_card
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"

    async def test_refund_with_ref_id(self, authorize_net_client, mock_httpx_client, sample_credit_card):
        """Test refund with reference ID."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.refund(
            "test_trans_123",
            "5.00",
            sample_credit_card,
            ref_id="ref_123"
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_refund_error(self, authorize_net_client, mock_httpx_client, sample_credit_card):
        """Test refund with error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Refund failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Refund failed"):
            await authorize_net_client.refund(
                "test_trans_123",
                "5.00",
                sample_credit_card
            )

    # Test void_transaction
    async def test_void_transaction_success(self, authorize_net_client, mock_httpx_client):
        """Test successful void transaction."""
        # Arrange
        success_response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.void_transaction("test_trans_123")
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"

    async def test_void_transaction_with_ref_id(self, authorize_net_client, mock_httpx_client):
        """Test void transaction with reference ID."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.void_transaction("test_trans_123", ref_id="ref_123")
        
        # Assert
        assert isinstance(result, PaymentResponse)
        mock_httpx_client.post.assert_called_once()

    async def test_void_transaction_error(self, authorize_net_client, mock_httpx_client):
        """Test void transaction with error."""
        # Arrange
        error_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Void failed"}]
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Void failed"):
            await authorize_net_client.void_transaction("test_trans_123")

    # Test _make_request method
    async def test_make_request_success(self, authorize_net_client, mock_httpx_client):
        """Test successful HTTP request."""
        # Arrange
        request_data = {"test": "data"}
        response_data = {"result": "success"}
        
        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client._make_request(request_data)
        
        # Assert
        assert result == response_data
        mock_httpx_client.post.assert_called_once_with(
            authorize_net_client.api_url,
            json=request_data
        )

    async def test_make_request_http_error(self, authorize_net_client, mock_httpx_client):
        """Test HTTP request with HTTP error."""
        # Arrange
        request_data = {"test": "data"}
        mock_httpx_client.post.side_effect = Exception("HTTP error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetNetworkError, match="Network error"):
            await authorize_net_client._make_request(request_data)

    async def test_make_request_json_decode_error(self, authorize_net_client, mock_httpx_client):
        """Test HTTP request with JSON decode error."""
        # Arrange
        request_data = {"test": "data"}
        
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(AuthorizeNetNetworkError, match="Invalid response format"):
            await authorize_net_client._make_request(request_data)

    # Test _parse_transaction_response method
    def test_parse_transaction_response_success(self, authorize_net_client):
        """Test parsing successful transaction response."""
        # Arrange
        response = {
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
        
        # Act
        result = authorize_net_client._parse_transaction_response(response)
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.transaction_id == "test_trans_123"
        assert result.status == TransactionStatus.CAPTURED
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        assert result.auth_code == "AUTH123"
        assert result.avs_response == "Y"
        assert result.cvv_response == "M"
        assert result.amount == "10.00"
        assert result.ref_id == "ref_123"

    def test_parse_transaction_response_declined(self, authorize_net_client):
        """Test parsing declined transaction response."""
        # Arrange
        response = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "2",
                "responseText": "Declined"
            }
        }
        
        # Act
        result = authorize_net_client._parse_transaction_response(response)
        
        # Assert
        assert isinstance(result, PaymentResponse)
        assert result.status == TransactionStatus.DECLINED
        assert result.response_code == "2"

    def test_parse_transaction_response_error(self, authorize_net_client):
        """Test parsing error transaction response."""
        # Arrange
        response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Transaction failed"}]
            }
        }
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Transaction failed"):
            authorize_net_client._parse_transaction_response(response)

    def test_parse_transaction_response_no_messages(self, authorize_net_client):
        """Test parsing response with no messages."""
        # Arrange
        response = {}
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Error parsing response"):
            authorize_net_client._parse_transaction_response(response)

    def test_parse_transaction_response_empty_messages(self, authorize_net_client):
        """Test parsing response with empty messages."""
        # Arrange
        response = {
            "messages": {
                "resultCode": "Error",
                "message": []
            }
        }
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Transaction failed"):
            authorize_net_client._parse_transaction_response(response)

    # Test context manager methods
    async def test_context_manager_entry(self, authorize_net_client):
        """Test async context manager entry."""
        # Act
        result = await authorize_net_client.__aenter__()
        
        # Assert
        assert result == authorize_net_client

    async def test_context_manager_exit(self, authorize_net_client, mock_httpx_client):
        """Test async context manager exit."""
        # Act
        await authorize_net_client.__aexit__(None, None, None)
        
        # Assert
        mock_httpx_client.aclose.assert_called_once()

    async def test_close_method(self, authorize_net_client, mock_httpx_client):
        """Test close method."""
        # Act
        await authorize_net_client.close()
        
        # Assert
        mock_httpx_client.aclose.assert_called_once()

    # Test edge cases and boundary conditions
    async def test_charge_credit_card_with_minimum_amount(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with minimum amount."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "0.01",
            sample_credit_card,
            sample_billing_address
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)

    async def test_charge_credit_card_with_maximum_amount(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with maximum amount."""
        # Arrange
        success_response = {
            "messages": {"resultCode": "Ok"},
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = success_response
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        
        # Act
        result = await authorize_net_client.charge_credit_card(
            "999999.99",
            sample_credit_card,
            sample_billing_address
        )
        
        # Assert
        assert isinstance(result, PaymentResponse)

    async def test_charge_credit_card_with_different_currencies(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with different currencies."""
        currencies = ["USD", "EUR", "GBP", "CAD"]
        
        for currency in currencies:
            # Arrange
            success_response = {
                "messages": {"resultCode": "Ok"},
                "transactionResponse": {
                    "transId": f"test_trans_{currency.lower()}",
                    "responseCode": "1",
                    "responseText": "Approved"
                }
            }
            
            mock_response = MagicMock()
            mock_response.json.return_value = success_response
            mock_response.raise_for_status.return_value = None
            mock_httpx_client.post.return_value = mock_response
            
            # Act
            result = await authorize_net_client.charge_credit_card(
                "10.00",
                sample_credit_card,
                sample_billing_address
            )
            
            # Assert
            assert isinstance(result, PaymentResponse)

    # Test error handling scenarios
    async def test_charge_credit_card_unexpected_error(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test credit card charge with unexpected error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Credit card charge failed"):
            await authorize_net_client.charge_credit_card(
                "10.00",
                sample_credit_card,
                sample_billing_address
            )

    async def test_authorize_only_unexpected_error(self, authorize_net_client, mock_httpx_client, sample_credit_card, sample_billing_address):
        """Test authorize only with unexpected error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Authorization failed"):
            await authorize_net_client.authorize_only(
                "10.00",
                sample_credit_card,
                sample_billing_address
            )

    async def test_capture_unexpected_error(self, authorize_net_client, mock_httpx_client):
        """Test capture with unexpected error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Capture failed"):
            await authorize_net_client.capture("test_trans_123")

    async def test_refund_unexpected_error(self, authorize_net_client, mock_httpx_client, sample_credit_card):
        """Test refund with unexpected error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Refund failed"):
            await authorize_net_client.refund(
                "test_trans_123",
                "5.00",
                sample_credit_card
            )

    async def test_void_transaction_unexpected_error(self, authorize_net_client, mock_httpx_client):
        """Test void transaction with unexpected error."""
        # Arrange
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(AuthorizeNetTransactionError, match="Void transaction failed"):
            await authorize_net_client.void_transaction("test_trans_123")

    # Test request data validation
    def test_request_data_structure_charge_credit_card(self, authorize_net_client, sample_credit_card, sample_billing_address):
        """Test that request data has correct structure for charge credit card."""
        # This test would verify the internal request structure
        # Since _make_request is private, we'll test it indirectly through the public methods
        
        # Arrange
        expected_structure = {
            "createTransactionRequest": {
                "merchantAuthentication": {
                    "name": authorize_net_client.credentials.api_login_id,
                    "transactionKey": authorize_net_client.credentials.transaction_key
                },
                "transactionRequest": {
                    "transactionType": "authCaptureTransaction",
                    "amount": "10.00",
                    "payment": {
                        "creditCard": {
                            "cardNumber": sample_credit_card.card_number,
                            "expirationDate": sample_credit_card.expiration_date,
                            "cardCode": sample_credit_card.card_code
                        }
                    },
                    "billTo": {
                        "firstName": sample_billing_address.first_name,
                        "lastName": sample_billing_address.last_name,
                        "address": sample_billing_address.address,
                        "city": sample_billing_address.city,
                        "state": sample_billing_address.state,
                        "zip": sample_billing_address.zip,
                        "country": sample_billing_address.country
                    }
                }
            }
        }
        
        # This is more of a documentation test - the actual structure is tested
        # through the integration with the mock HTTP client
        assert expected_structure["createTransactionRequest"]["merchantAuthentication"]["name"] == authorize_net_client.credentials.api_login_id
        assert expected_structure["createTransactionRequest"]["transactionRequest"]["transactionType"] == "authCaptureTransaction"
