"""
EasyPay Payment Gateway - Payment Flow Integration Tests
Comprehensive testing of payment processing with authentication and external integrations.
"""
import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, APIKeyStatus, Permission
from src.core.services.auth_service import AuthService
from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import PaymentCreateRequest, PaymentRefundRequest, PaymentCancelRequest
from src.api.v1.schemas.auth import APIKeyCreateRequest


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with proper configuration."""
    from src.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestPaymentFlowIntegration:
    """Integration tests for complete payment processing flow."""
    
    @pytest.fixture
    async def auth_service(self, test_db_session: AsyncSession) -> AuthService:
        """Create authentication service instance."""
        return AuthService(test_db_session)
    
    @pytest.fixture
    async def payment_service(self, test_db_session: AsyncSession) -> PaymentService:
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.fixture
    async def test_api_key(self, auth_service: AuthService) -> Dict[str, Any]:
        """Create a test API key for payment operations."""
        api_key_request = APIKeyCreateRequest(
            name="Payment Flow Test Key",
            description="API key for payment flow testing",
            permissions=[
                Permission.PAYMENTS_READ.value,
                Permission.PAYMENTS_WRITE.value,
                Permission.PAYMENTS_DELETE.value
            ],
            rate_limit_per_minute=1000,
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000
        )
        
        api_key_response = await auth_service.create_api_key(api_key_request)
        return {
            "key_id": api_key_response["key_id"],
            "key_secret": api_key_response["key_secret"],
            "api_key_id": api_key_response["api_key_id"]
        }
    
    @pytest.fixture
    def auth_headers(self, test_api_key: Dict[str, Any]) -> Dict[str, str]:
        """Create authentication headers for API requests."""
        return {
            "X-API-Key-ID": test_api_key["key_id"],
            "X-API-Key-Secret": test_api_key["key_secret"],
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_payment_creation_with_authorize_net_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test payment creation with Authorize.net integration."""
        
        # Mock Authorize.net client for testing
        with patch('src.core.services.payment_service.AuthorizeNetClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.transaction_id = "test_trans_123"
            mock_response.status = "captured"
            mock_response.response_code = "1"
            mock_response.response_text = "Approved"
            mock_response.auth_code = "AUTH123"
            mock_response.amount = "100.00"
            
            mock_client.charge_credit_card.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Create payment
            payment_data = {
                "amount": "100.00",
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": "cust_auth_net_test",
                "customer_email": "authnet@example.com",
                "customer_name": "Authorize.net Test Customer",
                "card_token": "tok_auth_net_test",
                "description": "Authorize.net integration test",
                "metadata": {"integration": "authorize_net", "test": True},
                "is_test": True
            }
            
            response = await test_client.post(
                "/api/v1/payments/",
                json=payment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            payment_response = response.json()
            
            assert payment_response["amount"] == "100.00"
            assert payment_response["status"] == PaymentStatus.PENDING.value
            assert payment_response["customer_id"] == "cust_auth_net_test"
            
            # Verify Authorize.net client was called
            mock_client.charge_credit_card.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_refund_flow_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test complete payment refund flow."""
        
        # First create a payment
        payment_data = {
            "amount": "75.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_refund_test",
            "customer_email": "refund@example.com",
            "customer_name": "Refund Test Customer",
            "card_token": "tok_refund_test",
            "description": "Refund flow test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        payment_id = payment_response["id"]
        
        # Mock Authorize.net refund response
        with patch('src.core.services.payment_service.AuthorizeNetClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_refund_response = MagicMock()
            mock_refund_response.transaction_id = "refund_trans_123"
            mock_refund_response.status = "refunded"
            mock_refund_response.response_code = "1"
            mock_refund_response.response_text = "Refund Approved"
            mock_refund_response.amount = "75.00"
            
            mock_client.refund.return_value = mock_refund_response
            mock_client_class.return_value = mock_client
            
            # Process refund
            refund_data = {
                "amount": "75.00",
                "reason": "Customer request",
                "metadata": {"refund_reason": "customer_request", "test": True}
            }
            
            response = await test_client.post(
                f"/api/v1/payments/{payment_id}/refund",
                json=refund_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            refund_response = response.json()
            
            assert refund_response["status"] == PaymentStatus.REFUNDED.value
            assert refund_response["amount"] == "75.00"
            
            # Verify Authorize.net refund was called
            mock_client.refund.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_cancellation_flow_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test complete payment cancellation flow."""
        
        # First create a payment
        payment_data = {
            "amount": "50.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_cancel_test",
            "customer_email": "cancel@example.com",
            "customer_name": "Cancel Test Customer",
            "card_token": "tok_cancel_test",
            "description": "Cancellation flow test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        payment_id = payment_response["id"]
        
        # Mock Authorize.net void response
        with patch('src.core.services.payment_service.AuthorizeNetClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_void_response = MagicMock()
            mock_void_response.transaction_id = "void_trans_123"
            mock_void_response.status = "voided"
            mock_void_response.response_code = "1"
            mock_void_response.response_text = "Void Approved"
            
            mock_client.void_transaction.return_value = mock_void_response
            mock_client_class.return_value = mock_client
            
            # Process cancellation
            cancel_data = {
                "reason": "Customer cancelled",
                "metadata": {"cancellation_reason": "customer_cancelled", "test": True}
            }
            
            response = await test_client.post(
                f"/api/v1/payments/{payment_id}/cancel",
                json=cancel_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            cancel_response = response.json()
            
            assert cancel_response["status"] == PaymentStatus.CANCELLED.value
            
            # Verify Authorize.net void was called
            mock_client.void_transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_search_and_filtering_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test payment search and filtering functionality."""
        
        # Create multiple payments for testing
        payments_data = [
            {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": "cust_search_1",
                "customer_email": "search1@example.com",
                "customer_name": "Search Test Customer 1",
                "card_token": "tok_search_1",
                "description": "Search test payment 1",
                "metadata": {"test_type": "search", "category": "electronics"},
                "is_test": True
            },
            {
                "amount": "50.00",
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": "cust_search_2",
                "customer_email": "search2@example.com",
                "customer_name": "Search Test Customer 2",
                "card_token": "tok_search_2",
                "description": "Search test payment 2",
                "metadata": {"test_type": "search", "category": "clothing"},
                "is_test": True
            },
            {
                "amount": "75.00",
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": "cust_search_3",
                "customer_email": "search3@example.com",
                "customer_name": "Search Test Customer 3",
                "card_token": "tok_search_3",
                "description": "Search test payment 3",
                "metadata": {"test_type": "search", "category": "electronics"},
                "is_test": True
            }
        ]
        
        created_payments = []
        for payment_data in payments_data:
            response = await test_client.post(
                "/api/v1/payments/",
                json=payment_data,
                headers=auth_headers
            )
            assert response.status_code == 201
            created_payments.append(response.json())
        
        # Test search by customer email
        search_params = {
            "customer_email": "search1@example.com"
        }
        
        response = await test_client.post(
            "/api/v1/payments/search",
            json=search_params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_response = response.json()
        
        assert "payments" in search_response
        assert len(search_response["payments"]) == 1
        assert search_response["payments"][0]["customer_email"] == "search1@example.com"
        
        # Test search by amount range
        search_params = {
            "amount_min": "40.00",
            "amount_max": "60.00"
        }
        
        response = await test_client.post(
            "/api/v1/payments/search",
            json=search_params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_response = response.json()
        
        assert "payments" in search_response
        assert len(search_response["payments"]) == 1
        assert search_response["payments"][0]["amount"] == "50.00"
        
        # Test search by metadata
        search_params = {
            "metadata": {"category": "electronics"}
        }
        
        response = await test_client.post(
            "/api/v1/payments/search",
            json=search_params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_response = response.json()
        
        assert "payments" in search_response
        assert len(search_response["payments"]) == 2  # Two electronics payments
    
    @pytest.mark.asyncio
    async def test_payment_status_tracking_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test payment status tracking and history."""
        
        # Create payment
        payment_data = {
            "amount": "60.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_status_test",
            "customer_email": "status@example.com",
            "customer_name": "Status Test Customer",
            "card_token": "tok_status_test",
            "description": "Status tracking test",
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        payment_id = payment_response["id"]
        
        # Get payment status history
        response = await test_client.get(
            f"/api/v1/payments/{payment_id}/status-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        status_response = response.json()
        
        assert "status_history" in status_response
        assert len(status_response["status_history"]) >= 1
        assert status_response["status_history"][0]["status"] == PaymentStatus.PENDING.value
        
        # Update payment status (simulate external processing)
        update_data = {
            "status": PaymentStatus.COMPLETED.value,
            "metadata": {"status_update": "external_processing_complete"}
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{payment_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        update_response = response.json()
        assert update_response["status"] == PaymentStatus.COMPLETED.value
        
        # Get updated status history
        response = await test_client.get(
            f"/api/v1/payments/{payment_id}/status-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        status_response = response.json()
        
        assert len(status_response["status_history"]) >= 2
        statuses = [entry["status"] for entry in status_response["status_history"]]
        assert PaymentStatus.PENDING.value in statuses
        assert PaymentStatus.COMPLETED.value in statuses
    
    @pytest.mark.asyncio
    async def test_payment_metadata_management_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test payment metadata management."""
        
        # Create payment with initial metadata
        payment_data = {
            "amount": "40.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_metadata_test",
            "customer_email": "metadata@example.com",
            "customer_name": "Metadata Test Customer",
            "card_token": "tok_metadata_test",
            "description": "Metadata management test",
            "metadata": {
                "initial": True,
                "category": "test",
                "priority": "high"
            },
            "is_test": True
        }
        
        response = await test_client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        payment_response = response.json()
        payment_id = payment_response["id"]
        
        # Get payment metadata
        response = await test_client.get(
            f"/api/v1/payments/{payment_id}/metadata",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        metadata_response = response.json()
        
        assert "metadata" in metadata_response
        assert metadata_response["metadata"]["initial"] is True
        assert metadata_response["metadata"]["category"] == "test"
        assert metadata_response["metadata"]["priority"] == "high"
        
        # Update payment metadata
        update_metadata = {
            "updated": True,
            "category": "updated_test",
            "priority": "medium",
            "additional_field": "new_value"
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{payment_id}/metadata",
            json=update_metadata,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        update_response = response.json()
        
        assert update_response["metadata"]["updated"] is True
        assert update_response["metadata"]["category"] == "updated_test"
        assert update_response["metadata"]["priority"] == "medium"
        assert update_response["metadata"]["additional_field"] == "new_value"
        
        # Verify metadata was updated
        response = await test_client.get(
            f"/api/v1/payments/{payment_id}/metadata",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        metadata_response = response.json()
        
        assert metadata_response["metadata"]["updated"] is True
        assert metadata_response["metadata"]["category"] == "updated_test"
    
    @pytest.mark.asyncio
    async def test_payment_error_handling_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test payment error handling and recovery."""
        
        # Test Authorize.net error handling
        with patch('src.core.services.payment_service.AuthorizeNetClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_error_response = MagicMock()
            mock_error_response.response_code = "3"
            mock_error_response.response_text = "Declined"
            mock_error_response.error_code = "E00001"
            mock_error_response.error_text = "Invalid card number"
            
            mock_client.charge_credit_card.return_value = mock_error_response
            mock_client_class.return_value = mock_client
            
            # Create payment that will fail
            payment_data = {
                "amount": "100.00",
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": "cust_error_test",
                "customer_email": "error@example.com",
                "customer_name": "Error Test Customer",
                "card_token": "tok_error_test",
                "description": "Error handling test",
                "is_test": True
            }
            
            response = await test_client.post(
                "/api/v1/payments/",
                json=payment_data,
                headers=auth_headers
            )
            
            # Payment should still be created but with error status
            assert response.status_code == 201
            payment_response = response.json()
            
            assert payment_response["status"] == PaymentStatus.FAILED.value
            assert "error" in payment_response or "error_details" in payment_response
            
            # Verify Authorize.net client was called
            mock_client.charge_credit_card.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_concurrent_processing_integration(
        self, 
        test_client: AsyncClient, 
        auth_headers: Dict[str, str],
        payment_service: PaymentService
    ):
        """Test concurrent payment processing."""
        
        # Create multiple concurrent payment requests
        payment_data_template = {
            "amount": "20.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_concurrent_payment",
            "customer_email": "concurrent@example.com",
            "customer_name": "Concurrent Payment Customer",
            "card_token": "tok_concurrent_payment",
            "description": "Concurrent payment test",
            "is_test": True
        }
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            payment_data = payment_data_template.copy()
            payment_data["customer_id"] = f"cust_concurrent_payment_{i}"
            payment_data["description"] = f"Concurrent payment test {i}"
            
            task = test_client.post(
                "/api/v1/payments/",
                json=payment_data,
                headers=auth_headers
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)
        
        # Check that all requests succeeded
        created_payments = []
        for response in responses:
            assert response.status_code == 201
            payment_data = response.json()
            assert "id" in payment_data
            assert payment_data["amount"] == "20.00"
            created_payments.append(payment_data)
        
        # Verify all payments have unique IDs
        payment_ids = [payment["id"] for payment in created_payments]
        assert len(set(payment_ids)) == len(payment_ids)  # All unique
        
        # Test concurrent operations on the same payment
        if created_payments:
            payment_id = created_payments[0]["id"]
            
            # Concurrent update and refund operations
            update_task = test_client.put(
                f"/api/v1/payments/{payment_id}",
                json={"description": "Concurrent update"},
                headers=auth_headers
            )
            
            refund_task = test_client.post(
                f"/api/v1/payments/{payment_id}/refund",
                json={"amount": "20.00", "reason": "Concurrent refund"},
                headers=auth_headers
            )
            
            update_response, refund_response = await asyncio.gather(update_task, refund_task)
            
            # At least one should succeed
            assert update_response.status_code in [200, 409]  # 409 for conflict
            assert refund_response.status_code in [200, 409]  # 409 for conflict
