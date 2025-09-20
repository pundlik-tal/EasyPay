"""
Comprehensive tests for integrations to achieve 80%+ coverage.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any, List

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    CreditCard, BillingAddress, TransactionRequest, TransactionResponse
)
from src.integrations.authorize_net.exceptions import (
    AuthorizeNetError, AuthorizeNetConnectionError, AuthorizeNetValidationError
)
from src.integrations.authorize_net.webhook_handler import AuthorizeNetWebhookHandler
from src.integrations.webhooks.webhook_handler import WebhookHandler
from src.core.exceptions import (
    PaymentError, ExternalServiceError, ValidationError
)


class TestAuthorizeNetClient:
    """Comprehensive tests for AuthorizeNet client."""
    
    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            mock_client = AsyncMock()
            mock_auth.return_value = mock_client
            return mock_client
    
    @pytest.fixture
    def authorize_net_client(self, mock_authorize_net_client):
        """Create AuthorizeNet client instance."""
        return AuthorizeNetClient(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
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
    def sample_transaction_request(self, sample_credit_card, sample_billing_address):
        """Sample transaction request."""
        return TransactionRequest(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address,
            customer_id="cust_123",
            order_id="order_123"
        )
    
    def test_client_initialization(self, authorize_net_client):
        """Test client initialization."""
        assert authorize_net_client.api_login_id == "test_login_id"
        assert authorize_net_client.transaction_key == "test_transaction_key"
        assert authorize_net_client.sandbox is True
        assert authorize_net_client.base_url is not None
    
    def test_client_initialization_production(self):
        """Test client initialization for production."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            client = AuthorizeNetClient(
                api_login_id="prod_login_id",
                transaction_key="prod_transaction_key",
                sandbox=False
            )
            
            assert client.sandbox is False
            assert "sandbox" not in client.base_url.lower()
    
    @pytest.mark.asyncio
    async def test_test_authentication_success(self, authorize_net_client, mock_authorize_net_client):
        """Test successful authentication."""
        mock_authorize_net_client.test_authentication.return_value = True
        
        result = await authorize_net_client.test_authentication()
        
        assert result is True
        mock_authorize_net_client.test_authentication.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_authentication_failure(self, authorize_net_client, mock_authorize_net_client):
        """Test authentication failure."""
        mock_authorize_net_client.test_authentication.return_value = False
        
        result = await authorize_net_client.test_authentication()
        
        assert result is False
        mock_authorize_net_client.test_authentication.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_success(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test successful credit card charge."""
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_123"
        mock_response.status = "captured"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_response.auth_code = "AUTH123"
        mock_response.amount = "10.00"
        
        mock_authorize_net_client.charge_credit_card.return_value = mock_response
        
        result = await authorize_net_client.charge_credit_card(sample_transaction_request)
        
        assert result is not None
        assert result.transaction_id == "test_trans_123"
        assert result.status == "captured"
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        assert result.auth_code == "AUTH123"
        assert result.amount == "10.00"
        mock_authorize_net_client.charge_credit_card.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_charge_credit_card_failure(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test credit card charge failure."""
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_456"
        mock_response.status = "declined"
        mock_response.response_code = "2"
        mock_response.response_text = "Declined"
        mock_response.auth_code = None
        mock_response.amount = "10.00"
        
        mock_authorize_net_client.charge_credit_card.return_value = mock_response
        
        result = await authorize_net_client.charge_credit_card(sample_transaction_request)
        
        assert result is not None
        assert result.transaction_id == "test_trans_456"
        assert result.status == "declined"
        assert result.response_code == "2"
        assert result.response_text == "Declined"
        assert result.auth_code is None
    
    @pytest.mark.asyncio
    async def test_authorize_only_success(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test successful authorization only."""
        mock_response = MagicMock()
        mock_response.transaction_id = "test_auth_123"
        mock_response.status = "authorizedPendingCapture"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_response.auth_code = "AUTH123"
        mock_response.amount = "10.00"
        
        mock_authorize_net_client.authorize_only.return_value = mock_response
        
        result = await authorize_net_client.authorize_only(sample_transaction_request)
        
        assert result is not None
        assert result.transaction_id == "test_auth_123"
        assert result.status == "authorizedPendingCapture"
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        mock_authorize_net_client.authorize_only.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_capture_success(self, authorize_net_client, mock_authorize_net_client):
        """Test successful capture."""
        transaction_id = "test_auth_123"
        amount = Decimal("10.00")
        
        mock_response = MagicMock()
        mock_response.transaction_id = transaction_id
        mock_response.status = "capturedPendingSettlement"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_response.amount = "10.00"
        
        mock_authorize_net_client.capture.return_value = mock_response
        
        result = await authorize_net_client.capture(transaction_id, amount)
        
        assert result is not None
        assert result.transaction_id == transaction_id
        assert result.status == "capturedPendingSettlement"
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        mock_authorize_net_client.capture.assert_called_once_with(transaction_id, amount)
    
    @pytest.mark.asyncio
    async def test_refund_success(self, authorize_net_client, mock_authorize_net_client):
        """Test successful refund."""
        transaction_id = "test_trans_123"
        amount = Decimal("5.00")
        
        mock_response = MagicMock()
        mock_response.transaction_id = transaction_id
        mock_response.status = "refundPendingSettlement"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_response.amount = "5.00"
        
        mock_authorize_net_client.refund.return_value = mock_response
        
        result = await authorize_net_client.refund(transaction_id, amount)
        
        assert result is not None
        assert result.transaction_id == transaction_id
        assert result.status == "refundPendingSettlement"
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        assert result.amount == "5.00"
        mock_authorize_net_client.refund.assert_called_once_with(transaction_id, amount)
    
    @pytest.mark.asyncio
    async def test_void_transaction_success(self, authorize_net_client, mock_authorize_net_client):
        """Test successful void transaction."""
        transaction_id = "test_trans_123"
        
        mock_response = MagicMock()
        mock_response.transaction_id = transaction_id
        mock_response.status = "voided"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        
        mock_authorize_net_client.void_transaction.return_value = mock_response
        
        result = await authorize_net_client.void_transaction(transaction_id)
        
        assert result is not None
        assert result.transaction_id == transaction_id
        assert result.status == "voided"
        assert result.response_code == "1"
        assert result.response_text == "Approved"
        mock_authorize_net_client.void_transaction.assert_called_once_with(transaction_id)
    
    @pytest.mark.asyncio
    async def test_connection_error(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test connection error handling."""
        mock_authorize_net_client.charge_credit_card.side_effect = AuthorizeNetConnectionError("Connection failed")
        
        with pytest.raises(AuthorizeNetConnectionError):
            await authorize_net_client.charge_credit_card(sample_transaction_request)
    
    @pytest.mark.asyncio
    async def test_validation_error(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test validation error handling."""
        mock_authorize_net_client.charge_credit_card.side_effect = AuthorizeNetValidationError("Invalid card number")
        
        with pytest.raises(AuthorizeNetValidationError):
            await authorize_net_client.charge_credit_card(sample_transaction_request)
    
    @pytest.mark.asyncio
    async def test_general_error(self, authorize_net_client, mock_authorize_net_client, sample_transaction_request):
        """Test general error handling."""
        mock_authorize_net_client.charge_credit_card.side_effect = AuthorizeNetError("General error")
        
        with pytest.raises(AuthorizeNetError):
            await authorize_net_client.charge_credit_card(sample_transaction_request)


class TestAuthorizeNetModels:
    """Comprehensive tests for Authorize.net models."""
    
    def test_credit_card_creation(self):
        """Test credit card model creation."""
        card = CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
        
        assert card.card_number == "4111111111111111"
        assert card.expiration_date == "1225"
        assert card.card_code == "123"
    
    def test_credit_card_validation(self):
        """Test credit card validation."""
        # Test valid card number
        card = CreditCard(
            card_number="4111111111111111",
            expiration_date="1225",
            card_code="123"
        )
        
        assert card.card_number == "4111111111111111"
        
        # Test invalid card number format
        with pytest.raises(ValidationError):
            CreditCard(
                card_number="invalid_card",
                expiration_date="1225",
                card_code="123"
            )
    
    def test_billing_address_creation(self):
        """Test billing address model creation."""
        address = BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
        
        assert address.first_name == "John"
        assert address.last_name == "Doe"
        assert address.address == "123 Main St"
        assert address.city == "Anytown"
        assert address.state == "CA"
        assert address.zip == "12345"
        assert address.country == "US"
    
    def test_billing_address_optional_fields(self):
        """Test billing address with optional fields."""
        address = BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US",
            phone="555-1234",
            email="john@example.com"
        )
        
        assert address.phone == "555-1234"
        assert address.email == "john@example.com"
    
    def test_transaction_request_creation(self, sample_credit_card, sample_billing_address):
        """Test transaction request creation."""
        request = TransactionRequest(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address,
            customer_id="cust_123",
            order_id="order_123"
        )
        
        assert request.amount == Decimal("10.00")
        assert request.credit_card == sample_credit_card
        assert request.billing_address == sample_billing_address
        assert request.customer_id == "cust_123"
        assert request.order_id == "order_123"
    
    def test_transaction_request_optional_fields(self, sample_credit_card, sample_billing_address):
        """Test transaction request with optional fields."""
        request = TransactionRequest(
            amount=Decimal("10.00"),
            credit_card=sample_credit_card,
            billing_address=sample_billing_address,
            customer_id="cust_123",
            order_id="order_123",
            description="Test transaction",
            metadata={"source": "test"}
        )
        
        assert request.description == "Test transaction"
        assert request.metadata == {"source": "test"}
    
    def test_transaction_response_creation(self):
        """Test transaction response creation."""
        response = TransactionResponse(
            transaction_id="test_trans_123",
            status="captured",
            response_code="1",
            response_text="Approved",
            auth_code="AUTH123",
            amount="10.00"
        )
        
        assert response.transaction_id == "test_trans_123"
        assert response.status == "captured"
        assert response.response_code == "1"
        assert response.response_text == "Approved"
        assert response.auth_code == "AUTH123"
        assert response.amount == "10.00"
    
    def test_transaction_response_optional_fields(self):
        """Test transaction response with optional fields."""
        response = TransactionResponse(
            transaction_id="test_trans_123",
            status="captured",
            response_code="1",
            response_text="Approved",
            auth_code="AUTH123",
            amount="10.00",
            avs_result_code="Y",
            cvv_result_code="M",
            settlement_time="2024-01-01T12:00:00Z"
        )
        
        assert response.avs_result_code == "Y"
        assert response.cvv_result_code == "M"
        assert response.settlement_time == "2024-01-01T12:00:00Z"


class TestAuthorizeNetWebhookHandler:
    """Comprehensive tests for Authorize.net webhook handler."""
    
    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler instance."""
        return AuthorizeNetWebhookHandler()
    
    @pytest.fixture
    def sample_webhook_payload(self):
        """Sample webhook payload."""
        return {
            "notificationId": "webhook_123",
            "eventType": "net.authorize.payment.authcapture.created",
            "eventDate": "2024-01-01T12:00:00Z",
            "webhookId": "webhook_456",
            "payload": {
                "merchantAuthentication": {
                    "name": "test_merchant",
                    "transactionKey": "test_key"
                },
                "transactionResponse": {
                    "transId": "test_trans_123",
                    "responseCode": "1",
                    "responseText": "Approved",
                    "authCode": "AUTH123",
                    "amount": "10.00"
                }
            }
        }
    
    def test_webhook_handler_initialization(self, webhook_handler):
        """Test webhook handler initialization."""
        assert webhook_handler is not None
        assert hasattr(webhook_handler, 'process_webhook')
        assert hasattr(webhook_handler, 'validate_signature')
        assert hasattr(webhook_handler, 'extract_transaction_data')
    
    @pytest.mark.asyncio
    async def test_process_webhook_success(self, webhook_handler, sample_webhook_payload):
        """Test successful webhook processing."""
        with patch.object(webhook_handler, 'validate_signature', return_value=True):
            with patch.object(webhook_handler, 'extract_transaction_data') as mock_extract:
                mock_extract.return_value = {
                    "transaction_id": "test_trans_123",
                    "status": "captured",
                    "amount": "10.00"
                }
                
                result = await webhook_handler.process_webhook(sample_webhook_payload)
                
                assert result is not None
                assert result["transaction_id"] == "test_trans_123"
                assert result["status"] == "captured"
                assert result["amount"] == "10.00"
    
    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(self, webhook_handler, sample_webhook_payload):
        """Test webhook processing with invalid signature."""
        with patch.object(webhook_handler, 'validate_signature', return_value=False):
            with pytest.raises(ValidationError):
                await webhook_handler.process_webhook(sample_webhook_payload)
    
    def test_validate_signature(self, webhook_handler):
        """Test signature validation."""
        payload = {"test": "data"}
        signature = "valid_signature"
        
        with patch.object(webhook_handler, '_verify_signature', return_value=True):
            result = webhook_handler.validate_signature(payload, signature)
            assert result is True
    
    def test_extract_transaction_data(self, webhook_handler, sample_webhook_payload):
        """Test transaction data extraction."""
        result = webhook_handler.extract_transaction_data(sample_webhook_payload)
        
        assert result is not None
        assert "transaction_id" in result
        assert "status" in result
        assert "amount" in result
    
    def test_extract_transaction_data_missing_fields(self, webhook_handler):
        """Test transaction data extraction with missing fields."""
        incomplete_payload = {
            "notificationId": "webhook_123",
            "eventType": "net.authorize.payment.authcapture.created"
        }
        
        with pytest.raises(ValidationError):
            webhook_handler.extract_transaction_data(incomplete_payload)
    
    def test_get_event_type(self, webhook_handler, sample_webhook_payload):
        """Test event type extraction."""
        event_type = webhook_handler.get_event_type(sample_webhook_payload)
        
        assert event_type == "net.authorize.payment.authcapture.created"
    
    def test_get_transaction_id(self, webhook_handler, sample_webhook_payload):
        """Test transaction ID extraction."""
        transaction_id = webhook_handler.get_transaction_id(sample_webhook_payload)
        
        assert transaction_id == "test_trans_123"
    
    def test_get_transaction_status(self, webhook_handler, sample_webhook_payload):
        """Test transaction status extraction."""
        status = webhook_handler.get_transaction_status(sample_webhook_payload)
        
        assert status is not None
    
    def test_get_transaction_amount(self, webhook_handler, sample_webhook_payload):
        """Test transaction amount extraction."""
        amount = webhook_handler.get_transaction_amount(sample_webhook_payload)
        
        assert amount == "10.00"


class TestWebhookHandler:
    """Comprehensive tests for webhook handler."""
    
    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler instance."""
        return WebhookHandler()
    
    @pytest.fixture
    def sample_webhook_data(self):
        """Sample webhook data."""
        return {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "payload": {
                "payment_id": "pay_123",
                "status": "completed",
                "amount": "10.00"
            },
            "secret": "webhook_secret_123"
        }
    
    def test_webhook_handler_initialization(self, webhook_handler):
        """Test webhook handler initialization."""
        assert webhook_handler is not None
        assert hasattr(webhook_handler, 'send_webhook')
        assert hasattr(webhook_handler, 'validate_webhook')
        assert hasattr(webhook_handler, 'retry_webhook')
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self, webhook_handler, sample_webhook_data):
        """Test successful webhook sending."""
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await webhook_handler.send_webhook(sample_webhook_data)
            
            assert result is not None
            assert result["status"] == "success"
            mock_client_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_webhook_failure(self, webhook_handler, sample_webhook_data):
        """Test webhook sending failure."""
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(ExternalServiceError):
                await webhook_handler.send_webhook(sample_webhook_data)
    
    @pytest.mark.asyncio
    async def test_send_webhook_timeout(self, webhook_handler, sample_webhook_data):
        """Test webhook sending timeout."""
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = Exception("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(ExternalServiceError):
                await webhook_handler.send_webhook(sample_webhook_data)
    
    def test_validate_webhook(self, webhook_handler, sample_webhook_data):
        """Test webhook validation."""
        result = webhook_handler.validate_webhook(sample_webhook_data)
        
        assert result is True
    
    def test_validate_webhook_invalid_url(self, webhook_handler):
        """Test webhook validation with invalid URL."""
        invalid_data = {
            "webhook_url": "invalid_url",
            "event_type": "payment.created",
            "payload": {"test": "data"}
        }
        
        with pytest.raises(ValidationError):
            webhook_handler.validate_webhook(invalid_data)
    
    def test_validate_webhook_missing_fields(self, webhook_handler):
        """Test webhook validation with missing fields."""
        incomplete_data = {
            "webhook_url": "https://example.com/webhook"
            # Missing event_type and payload
        }
        
        with pytest.raises(ValidationError):
            webhook_handler.validate_webhook(incomplete_data)
    
    @pytest.mark.asyncio
    async def test_retry_webhook(self, webhook_handler, sample_webhook_data):
        """Test webhook retry."""
        with patch.object(webhook_handler, 'send_webhook') as mock_send:
            mock_send.return_value = {"status": "success"}
            
            result = await webhook_handler.retry_webhook(sample_webhook_data, max_retries=3)
            
            assert result is not None
            assert result["status"] == "success"
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_webhook_with_failures(self, webhook_handler, sample_webhook_data):
        """Test webhook retry with failures."""
        with patch.object(webhook_handler, 'send_webhook') as mock_send:
            mock_send.side_effect = [
                ExternalServiceError("Network error"),
                ExternalServiceError("Network error"),
                {"status": "success"}  # Success on third attempt
            ]
            
            result = await webhook_handler.retry_webhook(sample_webhook_data, max_retries=3)
            
            assert result is not None
            assert result["status"] == "success"
            assert mock_send.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_webhook_max_retries_exceeded(self, webhook_handler, sample_webhook_data):
        """Test webhook retry with max retries exceeded."""
        with patch.object(webhook_handler, 'send_webhook') as mock_send:
            mock_send.side_effect = ExternalServiceError("Network error")
            
            with pytest.raises(ExternalServiceError):
                await webhook_handler.retry_webhook(sample_webhook_data, max_retries=2)
            
            assert mock_send.call_count == 2
    
    def test_generate_signature(self, webhook_handler):
        """Test signature generation."""
        payload = {"test": "data"}
        secret = "webhook_secret"
        
        signature = webhook_handler.generate_signature(payload, secret)
        
        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) > 0
    
    def test_verify_signature(self, webhook_handler):
        """Test signature verification."""
        payload = {"test": "data"}
        secret = "webhook_secret"
        
        signature = webhook_handler.generate_signature(payload, secret)
        
        result = webhook_handler.verify_signature(payload, signature, secret)
        
        assert result is True
    
    def test_verify_signature_invalid(self, webhook_handler):
        """Test signature verification with invalid signature."""
        payload = {"test": "data"}
        secret = "webhook_secret"
        invalid_signature = "invalid_signature"
        
        result = webhook_handler.verify_signature(payload, invalid_signature, secret)
        
        assert result is False


class TestIntegrationErrorHandling:
    """Comprehensive tests for integration error handling."""
    
    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client for error testing."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            mock_client = AsyncMock()
            mock_auth.return_value = mock_client
            return mock_client
    
    @pytest.mark.asyncio
    async def test_authorize_net_connection_error(self, mock_authorize_net_client):
        """Test Authorize.net connection error handling."""
        client = AuthorizeNetClient(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
        )
        
        mock_authorize_net_client.test_authentication.side_effect = AuthorizeNetConnectionError("Connection failed")
        
        with pytest.raises(AuthorizeNetConnectionError):
            await client.test_authentication()
    
    @pytest.mark.asyncio
    async def test_authorize_net_validation_error(self, mock_authorize_net_client):
        """Test Authorize.net validation error handling."""
        client = AuthorizeNetClient(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
        )
        
        mock_authorize_net_client.charge_credit_card.side_effect = AuthorizeNetValidationError("Invalid card number")
        
        with pytest.raises(AuthorizeNetValidationError):
            await client.charge_credit_card(Mock())
    
    @pytest.mark.asyncio
    async def test_webhook_network_error(self):
        """Test webhook network error handling."""
        webhook_handler = WebhookHandler()
        
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "payload": {"test": "data"}
        }
        
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = Exception("Network error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(ExternalServiceError):
                await webhook_handler.send_webhook(webhook_data)
    
    @pytest.mark.asyncio
    async def test_webhook_timeout_error(self):
        """Test webhook timeout error handling."""
        webhook_handler = WebhookHandler()
        
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "payload": {"test": "data"}
        }
        
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = Exception("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(ExternalServiceError):
                await webhook_handler.send_webhook(webhook_data)


class TestIntegrationRetryLogic:
    """Comprehensive tests for integration retry logic."""
    
    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client for retry testing."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            mock_client = AsyncMock()
            mock_auth.return_value = mock_client
            return mock_client
    
    @pytest.mark.asyncio
    async def test_authorize_net_retry_success(self, mock_authorize_net_client):
        """Test Authorize.net retry with eventual success."""
        client = AuthorizeNetClient(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
        )
        
        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_123"
        mock_response.status = "captured"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        
        mock_authorize_net_client.charge_credit_card.side_effect = [
            AuthorizeNetConnectionError("Connection failed"),
            AuthorizeNetConnectionError("Connection failed"),
            mock_response
        ]
        
        with patch.object(client, '_retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_response
            
            result = await client.charge_credit_card(Mock())
            
            assert result is not None
            assert result.transaction_id == "test_trans_123"
            mock_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_retry_with_exponential_backoff(self):
        """Test webhook retry with exponential backoff."""
        webhook_handler = WebhookHandler()
        
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "payload": {"test": "data"}
        }
        
        with patch.object(webhook_handler, 'send_webhook') as mock_send:
            mock_send.side_effect = [
                ExternalServiceError("Network error"),
                ExternalServiceError("Network error"),
                {"status": "success"}
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await webhook_handler.retry_webhook(webhook_data, max_retries=3)
                
                assert result is not None
                assert result["status"] == "success"
                assert mock_send.call_count == 3
                # Verify exponential backoff was used
                assert mock_sleep.call_count == 2


class TestIntegrationConfiguration:
    """Comprehensive tests for integration configuration."""
    
    def test_authorize_net_sandbox_configuration(self):
        """Test Authorize.net sandbox configuration."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            client = AuthorizeNetClient(
                api_login_id="test_login_id",
                transaction_key="test_transaction_key",
                sandbox=True
            )
            
            assert client.sandbox is True
            assert "sandbox" in client.base_url.lower()
    
    def test_authorize_net_production_configuration(self):
        """Test Authorize.net production configuration."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            client = AuthorizeNetClient(
                api_login_id="prod_login_id",
                transaction_key="prod_transaction_key",
                sandbox=False
            )
            
            assert client.sandbox is False
            assert "sandbox" not in client.base_url.lower()
    
    def test_webhook_handler_configuration(self):
        """Test webhook handler configuration."""
        webhook_handler = WebhookHandler()
        
        assert webhook_handler is not None
        assert hasattr(webhook_handler, 'default_timeout')
        assert hasattr(webhook_handler, 'default_retry_count')
    
    def test_integration_timeout_configuration(self):
        """Test integration timeout configuration."""
        webhook_handler = WebhookHandler()
        
        # Test default timeout
        assert webhook_handler.default_timeout > 0
        
        # Test custom timeout
        webhook_handler.default_timeout = 30
        assert webhook_handler.default_timeout == 30


class TestIntegrationMonitoring:
    """Comprehensive tests for integration monitoring."""
    
    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client for monitoring testing."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            mock_client = AsyncMock()
            mock_auth.return_value = mock_client
            return mock_client
    
    @pytest.mark.asyncio
    async def test_authorize_net_metrics_collection(self, mock_authorize_net_client):
        """Test Authorize.net metrics collection."""
        client = AuthorizeNetClient(
            api_login_id="test_login_id",
            transaction_key="test_transaction_key",
            sandbox=True
        )
        
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_123"
        mock_response.status = "captured"
        mock_response.response_code = "1"
        
        mock_authorize_net_client.charge_credit_card.return_value = mock_response
        
        with patch.object(client, '_record_metrics') as mock_record:
            await client.charge_credit_card(Mock())
            
            mock_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_metrics_collection(self):
        """Test webhook metrics collection."""
        webhook_handler = WebhookHandler()
        
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "payload": {"test": "data"}
        }
        
        with patch('src.integrations.webhooks.webhook_handler.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with patch.object(webhook_handler, '_record_metrics') as mock_record:
                await webhook_handler.send_webhook(webhook_data)
                
                mock_record.assert_called_once()
    
    def test_integration_health_checks(self):
        """Test integration health checks."""
        with patch('src.integrations.authorize_net.client.authorize') as mock_auth:
            client = AuthorizeNetClient(
                api_login_id="test_login_id",
                transaction_key="test_transaction_key",
                sandbox=True
            )
            
            assert hasattr(client, 'health_check')
            
            # Test health check method exists
            assert callable(getattr(client, 'health_check', None))
    
    def test_integration_error_tracking(self):
        """Test integration error tracking."""
        webhook_handler = WebhookHandler()
        
        assert hasattr(webhook_handler, 'error_count')
        assert hasattr(webhook_handler, 'success_count')
        
        # Test error tracking methods exist
        assert hasattr(webhook_handler, 'increment_error_count')
        assert hasattr(webhook_handler, 'increment_success_count')
