"""
EasyPay Payment Gateway - Payment Service Unit Tests
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.services.payment_service import PaymentService
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.exceptions import (
    PaymentError,
    PaymentNotFoundError,
    ValidationError,
    DatabaseError,
    ExternalServiceError
)
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest
)


class TestPaymentService:
    """Test cases for PaymentService."""
    
    @pytest.fixture
    def payment_service(self, test_db_session):
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, payment_service, sample_payment_create_request):
        """Test successful payment creation."""
        with patch.object(payment_service, 'advanced_features', None):
            payment = await payment_service.create_payment(sample_payment_create_request)
            
            assert payment is not None
            assert payment.amount == sample_payment_create_request.amount
            assert payment.currency == sample_payment_create_request.currency
            assert payment.status == PaymentStatus.PENDING
            assert payment.payment_method == sample_payment_create_request.payment_method
            assert payment.customer_id == sample_payment_create_request.customer_id
            assert payment.customer_email == sample_payment_create_request.customer_email
            assert payment.description == sample_payment_create_request.description
            assert payment.is_test == sample_payment_create_request.is_test
    
    @pytest.mark.asyncio
    async def test_create_payment_with_advanced_features(self, payment_service, sample_payment_create_request, mock_advanced_features):
        """Test payment creation with advanced features."""
        payment_service.advanced_features = mock_advanced_features
        
        payment = await payment_service.create_payment(sample_payment_create_request)
        
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING
        
        # Verify advanced features were called
        mock_advanced_features.track_payment_status_change.assert_called_once()
        mock_advanced_features.store_payment_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_payment_validation_error_amount(self, payment_service):
        """Test payment creation with invalid amount."""
        invalid_request = PaymentCreateRequest(
            amount=Decimal("0"),  # Invalid amount
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123",
            description="Test payment",
            is_test=True
        )
        
        with pytest.raises(ValidationError, match="Payment amount must be greater than 0"):
            await payment_service.create_payment(invalid_request)
    
    @pytest.mark.asyncio
    async def test_create_payment_validation_error_currency(self, payment_service):
        """Test payment creation with invalid currency."""
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="US",  # Invalid currency (too short)
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123",
            description="Test payment",
            is_test=True
        )
        
        with pytest.raises(ValidationError, match="Currency must be a 3-character code"):
            await payment_service.create_payment(invalid_request)
    
    @pytest.mark.asyncio
    async def test_create_payment_validation_error_email(self, payment_service):
        """Test payment creation with invalid email."""
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="invalid-email",  # Invalid email
            customer_name="Test Customer",
            card_token="tok_123",
            description="Test payment",
            is_test=True
        )
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            await payment_service.create_payment(invalid_request)
    
    @pytest.mark.asyncio
    async def test_get_payment_success(self, payment_service, sample_payment):
        """Test successful payment retrieval."""
        payment = await payment_service.get_payment(sample_payment.id)
        
        assert payment is not None
        assert payment.id == sample_payment.id
        assert payment.amount == sample_payment.amount
        assert payment.status == sample_payment.status
    
    @pytest.mark.asyncio
    async def test_get_payment_not_found(self, payment_service):
        """Test payment retrieval with non-existent ID."""
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(PaymentNotFoundError, match=f"Payment {non_existent_id} not found"):
            await payment_service.get_payment(non_existent_id)
    
    @pytest.mark.asyncio
    async def test_get_payment_by_external_id_success(self, payment_service, sample_payment):
        """Test successful payment retrieval by external ID."""
        payment = await payment_service.get_payment_by_external_id(sample_payment.external_id)
        
        assert payment is not None
        assert payment.id == sample_payment.id
        assert payment.external_id == sample_payment.external_id
    
    @pytest.mark.asyncio
    async def test_get_payment_by_external_id_not_found(self, payment_service):
        """Test payment retrieval by non-existent external ID."""
        non_existent_external_id = "pay_nonexistent"
        
        with pytest.raises(PaymentNotFoundError, match=f"Payment with external ID {non_existent_external_id} not found"):
            await payment_service.get_payment_by_external_id(non_existent_external_id)
    
    @pytest.mark.asyncio
    async def test_update_payment_success(self, payment_service, sample_payment, sample_payment_update_request):
        """Test successful payment update."""
        updated_payment = await payment_service.update_payment(sample_payment.id, sample_payment_update_request)
        
        assert updated_payment is not None
        assert updated_payment.id == sample_payment.id
        assert updated_payment.description == sample_payment_update_request.description
        assert updated_payment.payment_metadata == sample_payment_update_request.metadata
    
    @pytest.mark.asyncio
    async def test_update_payment_validation_error(self, payment_service, sample_payment):
        """Test payment update with invalid data."""
        invalid_update = PaymentUpdateRequest(
            description=None,
            metadata=None  # Both fields are None
        )
        
        with pytest.raises(ValidationError, match="At least one field must be provided for update"):
            await payment_service.update_payment(sample_payment.id, invalid_update)
    
    @pytest.mark.asyncio
    async def test_refund_payment_success(self, payment_service, sample_payment, sample_payment_refund_request):
        """Test successful payment refund."""
        # Set payment status to COMPLETED to make it refundable
        sample_payment.status = PaymentStatus.COMPLETED
        await payment_service.session.commit()
        
        with patch.object(payment_service, 'advanced_features', None):
            refunded_payment = await payment_service.refund_payment(
                sample_payment.id, 
                sample_payment_refund_request
            )
            
            assert refunded_payment is not None
            assert refunded_payment.id == sample_payment.id
            assert refunded_payment.status in [PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED]
            assert refunded_payment.refunded_amount == sample_payment_refund_request.amount
    
    @pytest.mark.asyncio
    async def test_refund_payment_not_refundable(self, payment_service, sample_payment, sample_payment_refund_request):
        """Test refund of non-refundable payment."""
        # Keep payment status as PENDING (not refundable)
        
        with pytest.raises(ValidationError, match="Payment cannot be refunded"):
            await payment_service.refund_payment(sample_payment.id, sample_payment_refund_request)
    
    @pytest.mark.asyncio
    async def test_refund_payment_amount_exceeds_remaining(self, payment_service, sample_payment):
        """Test refund with amount exceeding remaining refundable amount."""
        # Set payment status to COMPLETED and set refunded amount
        sample_payment.status = PaymentStatus.COMPLETED
        sample_payment.refunded_amount = Decimal("8.00")  # Already refunded $8
        await payment_service.session.commit()
        
        refund_request = PaymentRefundRequest(
            amount=Decimal("5.00"),  # Trying to refund $5, but only $2 remaining
            reason="Test refund"
        )
        
        with pytest.raises(ValidationError, match="Refund amount.*exceeds remaining refundable amount"):
            await payment_service.refund_payment(sample_payment.id, refund_request)
    
    @pytest.mark.asyncio
    async def test_cancel_payment_success(self, payment_service, sample_payment, sample_payment_cancel_request):
        """Test successful payment cancellation."""
        # Set payment status to PENDING to make it cancellable
        sample_payment.status = PaymentStatus.PENDING
        await payment_service.session.commit()
        
        with patch.object(payment_service, 'advanced_features', None):
            cancelled_payment = await payment_service.cancel_payment(
                sample_payment.id, 
                sample_payment_cancel_request
            )
            
            assert cancelled_payment is not None
            assert cancelled_payment.id == sample_payment.id
            assert cancelled_payment.status == PaymentStatus.VOIDED
    
    @pytest.mark.asyncio
    async def test_cancel_payment_not_cancellable(self, payment_service, sample_payment, sample_payment_cancel_request):
        """Test cancellation of non-cancellable payment."""
        # Set payment status to COMPLETED (not cancellable)
        sample_payment.status = PaymentStatus.COMPLETED
        await payment_service.session.commit()
        
        with pytest.raises(ValidationError, match="Payment cannot be cancelled"):
            await payment_service.cancel_payment(sample_payment.id, sample_payment_cancel_request)
    
    @pytest.mark.asyncio
    async def test_list_payments_success(self, payment_service, sample_payment):
        """Test successful payment listing."""
        result = await payment_service.list_payments()
        
        assert "payments" in result
        assert "total" in result
        assert len(result["payments"]) >= 1
        assert result["total"] >= 1
        
        # Check that our sample payment is in the results
        payment_ids = [p.id for p in result["payments"]]
        assert sample_payment.id in payment_ids
    
    @pytest.mark.asyncio
    async def test_list_payments_with_filters(self, payment_service, sample_payment):
        """Test payment listing with filters."""
        # Test filtering by customer_id
        result = await payment_service.list_payments(customer_id=sample_payment.customer_id)
        
        assert "payments" in result
        assert "total" in result
        assert len(result["payments"]) >= 1
        
        # All returned payments should have the same customer_id
        for payment in result["payments"]:
            assert payment.customer_id == sample_payment.customer_id
    
    @pytest.mark.asyncio
    async def test_search_payments_success(self, payment_service, sample_payment):
        """Test successful payment search."""
        result = await payment_service.search_payments(sample_payment.customer_id)
        
        assert "payments" in result
        assert "total" in result
        assert len(result["payments"]) >= 1
    
    @pytest.mark.asyncio
    async def test_get_payment_stats_success(self, payment_service, sample_payment):
        """Test successful payment statistics retrieval."""
        stats = await payment_service.get_payment_stats()
        
        assert "total_count" in stats
        assert "total_amount" in stats
        assert "status_counts" in stats
        assert stats["total_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_payment_status_history_no_advanced_features(self, payment_service, sample_payment):
        """Test status history retrieval without advanced features."""
        payment_service.advanced_features = None
        
        history = await payment_service.get_payment_status_history(sample_payment.id)
        
        assert history == []
    
    @pytest.mark.asyncio
    async def test_get_payment_metadata_no_advanced_features(self, payment_service, sample_payment):
        """Test metadata retrieval without advanced features."""
        payment_service.advanced_features = None
        
        metadata = await payment_service.get_payment_metadata(sample_payment.id)
        
        assert metadata is None
    
    @pytest.mark.asyncio
    async def test_update_payment_metadata_no_advanced_features(self, payment_service, sample_payment):
        """Test metadata update without advanced features."""
        payment_service.advanced_features = None
        
        # Should not raise an error, just return
        await payment_service.update_payment_metadata(sample_payment.id, {"test": "data"})
    
    @pytest.mark.asyncio
    async def test_search_payments_advanced_no_advanced_features(self, payment_service):
        """Test advanced search without advanced features."""
        payment_service.advanced_features = None
        
        results = await payment_service.search_payments_advanced({"test": "search"})
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_get_circuit_breaker_metrics_no_advanced_features(self, payment_service):
        """Test circuit breaker metrics without advanced features."""
        payment_service.advanced_features = None
        
        metrics = payment_service.get_circuit_breaker_metrics()
        
        assert metrics == {}
    
    @pytest.mark.asyncio
    async def test_payment_service_context_manager(self, test_db_session):
        """Test payment service as context manager."""
        async with PaymentService(test_db_session) as service:
            assert service is not None
            assert isinstance(service, PaymentService)
    
    @pytest.mark.asyncio
    async def test_payment_service_close(self, payment_service, mock_authorize_net_client):
        """Test payment service close method."""
        payment_service.authorize_net_client = mock_authorize_net_client
        
        await payment_service.close()
        
        mock_authorize_net_client.close.assert_called_once()


class TestPaymentServiceValidation:
    """Test cases for payment service validation methods."""
    
    @pytest.fixture
    def payment_service(self, test_db_session):
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.mark.asyncio
    async def test_validate_payment_data_amount_too_large(self, payment_service):
        """Test validation with amount exceeding maximum."""
        invalid_request = PaymentCreateRequest(
            amount=Decimal("1000000.00"),  # Exceeds maximum
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123",
            description="Test payment",
            is_test=True
        )
        
        with pytest.raises(ValidationError, match="Payment amount cannot exceed 999,999.99"):
            await payment_service._validate_payment_data(invalid_request)
    
    @pytest.mark.asyncio
    async def test_validate_payment_data_invalid_payment_method(self, payment_service):
        """Test validation with invalid payment method."""
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method="invalid_method",  # Invalid payment method
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123",
            description="Test payment",
            is_test=True
        )
        
        with pytest.raises(ValidationError, match="Invalid payment method"):
            await payment_service._validate_payment_data(invalid_request)
    
    @pytest.mark.asyncio
    async def test_validate_refund_eligibility_success(self, payment_service, sample_payment):
        """Test successful refund eligibility validation."""
        # Set payment status to COMPLETED
        sample_payment.status = PaymentStatus.COMPLETED
        await payment_service.session.commit()
        
        refund_request = PaymentRefundRequest(amount=Decimal("5.00"), reason="Test")
        
        # Should not raise an exception
        await payment_service._validate_refund_eligibility(sample_payment, refund_request)
    
    @pytest.mark.asyncio
    async def test_validate_cancellation_eligibility_success(self, payment_service, sample_payment):
        """Test successful cancellation eligibility validation."""
        # Set payment status to PENDING
        sample_payment.status = PaymentStatus.PENDING
        await payment_service.session.commit()
        
        # Should not raise an exception
        await payment_service._validate_cancellation_eligibility(sample_payment)
