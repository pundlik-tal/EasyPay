"""
EasyPay Payment Gateway - Authorize.net Client Unit Tests
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import HTTPError, Response

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    AuthorizeNetCredentials,
    CreditCard,
    BillingAddress,
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
    """Test cases for AuthorizeNetClient."""
    
    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return AuthorizeNetCredentials(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True,
            api_url="https://apitest.authorize.net/xml/v1/request.api"
        )
    
    @pytest.fixture
    def client(self, credentials):
        """Create test client."""
        return AuthorizeNetClient(credentials)
    
    @pytest.fixture
    def credit_card(self):
        """Create test credit card."""
        return CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
    
    @pytest.fixture
    def billing_address(self):
        """Create test billing address."""
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
    def mock_response(self):
        """Create mock HTTP response."""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = {
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
        return response
    
    @pytest.fixture
    def mock_error_response(self):
        """Create mock error HTTP response."""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Authentication failed."}]
            }
        }
        return response
    
    def test_client_initialization_with_credentials(self, credentials):
        """Test client initialization with provided credentials."""
        client = AuthorizeNetClient(credentials)
        
        assert client.credentials == credentials
        assert client.api_url == credentials.api_url
        assert client.client is not None
    
    @patch('src.integrations.authorize_net.client.settings')
    def test_client_initialization_with_settings(self, mock_settings):
        """Test client initialization with settings."""
        mock_settings.AUTHORIZE_NET_API_LOGIN_ID = "settings_login_id"
        mock_settings.AUTHORIZE_NET_TRANSACTION_KEY = "settings_transaction_key"
        mock_settings.AUTHORIZE_NET_SANDBOX = True
        mock_settings.get_authorize_net_url.return_value = "https://apitest.authorize.net/xml/v1/request.api"
        
        client = AuthorizeNetClient()
        
        assert client.credentials.api_login_id == "settings_login_id"
        assert client.credentials.transaction_key == "settings_transaction_key"
        assert client.credentials.sandbox is True
    
    def test_get_api_url_sandbox(self):
        """Test API URL generation for sandbox."""
        client = AuthorizeNetClient()
        url = client._get_api_url(sandbox=True)
        
        assert url == "https://apitest.authorize.net/xml/v1/request.api"
    
    def test_get_api_url_production(self):
        """Test API URL generation for production."""
        client = AuthorizeNetClient()
        url = client._get_api_url(sandbox=False)
        
        assert url == "https://api.authorize.net/xml/v1/request.api"
    
    @pytest.mark.asyncio
    async def test_test_authentication_success(self, client, mock_response):
        """Test successful authentication."""
        with patch.object(client.client, 'post', return_value=mock_response):
            result = await client.test_authentication()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_authentication_failure(self, client, mock_error_response):
        """Test authentication failure."""
        with patch.object(client.client, 'post', return_value=mock_error_response):
            with pytest.raises(AuthorizeNetAuthenticationError, match="Authentication test failed"):
                await client.test_authentication()
    
    @pytest.mark.asyncio
    async def test_test_authentication_network_error(self, client):
        """Test authentication with network error."""
        with patch.object(client.client, 'post', side_effect=HTTPError("Network error")):
            with pytest.raises(AuthorizeNetAuthenticationError):
                await client.test_authentication()
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_success(self, client, credit_card, billing_address, mock_response):
        """Test successful credit card charge."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.charge_credit_card(
                amount="10.00",
                credit_card=credit_card,
                billing_address=billing_address
            )
            
            assert response.transaction_id == "test_trans_123"
            assert response.status == TransactionStatus.CAPTURED
            assert response.response_code == "1"
            assert response.response_text == "Approved"
            assert response.auth_code == "AUTH123"
            assert response.amount == "10.00"
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_with_order_info(self, client, credit_card, billing_address, mock_response):
        """Test credit card charge with order information."""
        order_info = {"invoiceNumber": "INV123", "description": "Test order"}
        
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.charge_credit_card(
                amount="10.00",
                credit_card=credit_card,
                billing_address=billing_address,
                order_info=order_info
            )
            
            assert response.transaction_id == "test_trans_123"
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_failure(self, client, credit_card, billing_address, mock_error_response):
        """Test credit card charge failure."""
        with patch.object(client.client, 'post', return_value=mock_error_response):
            with pytest.raises(AuthorizeNetTransactionError, match="Authentication failed"):
                await client.charge_credit_card(
                    amount="10.00",
                    credit_card=credit_card,
                    billing_address=billing_address
                )
    
    @pytest.mark.asyncio
    async def test_authorize_only_success(self, client, credit_card, billing_address, mock_response):
        """Test successful authorization only."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.authorize_only(
                amount="10.00",
                credit_card=credit_card,
                billing_address=billing_address
            )
            
            assert response.transaction_id == "test_trans_123"
            assert response.status == TransactionStatus.CAPTURED
            assert response.response_code == "1"
    
    @pytest.mark.asyncio
    async def test_capture_success(self, client, mock_response):
        """Test successful capture."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.capture("test_trans_123", amount="10.00")
            
            assert response.transaction_id == "test_trans_123"
            assert response.status == TransactionStatus.CAPTURED
    
    @pytest.mark.asyncio
    async def test_capture_without_amount(self, client, mock_response):
        """Test capture without specifying amount."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.capture("test_trans_123")
            
            assert response.transaction_id == "test_trans_123"
    
    @pytest.mark.asyncio
    async def test_refund_success(self, client, credit_card, mock_response):
        """Test successful refund."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.refund(
                transaction_id="test_trans_123",
                amount="5.00",
                credit_card=credit_card
            )
            
            assert response.transaction_id == "test_trans_123"
            assert response.status == TransactionStatus.CAPTURED
    
    @pytest.mark.asyncio
    async def test_void_transaction_success(self, client, mock_response):
        """Test successful void transaction."""
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client.void_transaction("test_trans_123")
            
            assert response.transaction_id == "test_trans_123"
            assert response.status == TransactionStatus.CAPTURED
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_response):
        """Test successful HTTP request."""
        request_data = {"test": "data"}
        
        with patch.object(client.client, 'post', return_value=mock_response):
            response = await client._make_request(request_data)
            
            assert response["messages"]["resultCode"] == "Ok"
            assert response["transactionResponse"]["transId"] == "test_trans_123"
    
    @pytest.mark.asyncio
    async def test_make_request_http_error(self, client):
        """Test HTTP request with error."""
        request_data = {"test": "data"}
        
        with patch.object(client.client, 'post', side_effect=HTTPError("HTTP error")):
            with pytest.raises(AuthorizeNetNetworkError, match="Network error"):
                await client._make_request(request_data)
    
    @pytest.mark.asyncio
    async def test_make_request_json_decode_error(self, client):
        """Test HTTP request with JSON decode error."""
        request_data = {"test": "data"}
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with patch.object(client.client, 'post', return_value=mock_response):
            with pytest.raises(AuthorizeNetNetworkError, match="Invalid response format"):
                await client._make_request(request_data)
    
    def test_parse_transaction_response_success(self, client):
        """Test successful transaction response parsing."""
        response_data = {
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
        
        response = client._parse_transaction_response(response_data)
        
        assert response.transaction_id == "test_trans_123"
        assert response.status == TransactionStatus.CAPTURED
        assert response.response_code == "1"
        assert response.response_text == "Approved"
        assert response.auth_code == "AUTH123"
        assert response.avs_response == "Y"
        assert response.cvv_response == "M"
        assert response.amount == "10.00"
        assert response.ref_id == "ref_123"
    
    def test_parse_transaction_response_declined(self, client):
        """Test transaction response parsing for declined transaction."""
        response_data = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            },
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "2",  # Declined
                "responseText": "Declined",
                "amount": "10.00"
            },
            "refId": "ref_123"
        }
        
        response = client._parse_transaction_response(response_data)
        
        assert response.transaction_id == "test_trans_123"
        assert response.status == TransactionStatus.DECLINED
        assert response.response_code == "2"
        assert response.response_text == "Declined"
    
    def test_parse_transaction_response_error(self, client):
        """Test transaction response parsing for error."""
        response_data = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": "E00001", "text": "Authentication failed."}]
            }
        }
        
        with pytest.raises(AuthorizeNetTransactionError, match="Authentication failed"):
            client._parse_transaction_response(response_data)
    
    def test_parse_transaction_response_no_messages(self, client):
        """Test transaction response parsing with no messages."""
        response_data = {
            "transactionResponse": {
                "transId": "test_trans_123",
                "responseCode": "1",
                "responseText": "Approved"
            }
        }
        
        with pytest.raises(AuthorizeNetTransactionError, match="Error parsing response"):
            client._parse_transaction_response(response_data)
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self, credentials):
        """Test client as context manager."""
        async with AuthorizeNetClient(credentials) as client:
            assert client is not None
            assert isinstance(client, AuthorizeNetClient)
    
    @pytest.mark.asyncio
    async def test_client_close(self, client):
        """Test client close method."""
        with patch.object(client.client, 'aclose') as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestAuthorizeNetClientEdgeCases:
    """Test edge cases for AuthorizeNetClient."""
    
    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return AuthorizeNetCredentials(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
        )
    
    @pytest.fixture
    def client(self, credentials):
        """Create test client."""
        return AuthorizeNetClient(credentials)
    
    def test_parse_transaction_response_empty_message_list(self, client):
        """Test parsing response with empty message list."""
        response_data = {
            "messages": {
                "resultCode": "Error",
                "message": []
            }
        }
        
        with pytest.raises(AuthorizeNetTransactionError, match="Transaction failed"):
            client._parse_transaction_response(response_data)
    
    def test_parse_transaction_response_missing_transaction_response(self, client):
        """Test parsing response without transaction response."""
        response_data = {
            "messages": {
                "resultCode": "Ok",
                "message": [{"code": "I00001", "text": "Successful."}]
            }
        }
        
        with pytest.raises(AuthorizeNetTransactionError, match="Error parsing response"):
            client._parse_transaction_response(response_data)
    
    @pytest.mark.asyncio
    async def test_make_request_unexpected_error(self, client):
        """Test HTTP request with unexpected error."""
        request_data = {"test": "data"}
        
        with patch.object(client.client, 'post', side_effect=Exception("Unexpected error")):
            with pytest.raises(AuthorizeNetNetworkError, match="Unexpected network error"):
                await client._make_request(request_data)
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_unexpected_error(self, client):
        """Test credit card charge with unexpected error."""
        credit_card = CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
        billing_address = BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
        
        with patch.object(client.client, 'post', side_effect=Exception("Unexpected error")):
            with pytest.raises(AuthorizeNetTransactionError, match="Credit card charge failed"):
                await client.charge_credit_card(
                    amount="10.00",
                    credit_card=credit_card,
                    billing_address=billing_address
                )
