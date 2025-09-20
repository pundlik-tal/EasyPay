"""
EasyPay Payment Gateway - Comprehensive Payment Service Unit Tests
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

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
    """Comprehensive test suite for PaymentService class."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_payment_repository(self):
        """Mock payment repository."""
        mock_repo = AsyncMock()
        mock_repo.create.return_value = MagicMock()
        mock_repo.get_by_id.return_value = None
        mock_repo.get_by_external_id.return_value = None
        mock_repo.update.return_value = MagicMock()
        mock_repo.list_payments.return_value = {"payments": [], "total": 0, "page": 1, "per_page": 20}
        mock_repo.search_payments.return_value = {"payments": [], "total": 0, "page": 1, "per_page": 20}
        mock_repo.get_payment_stats.return_value = {"total_count": 0, "total_amount": Decimal("0")}
        return mock_repo

    @pytest.fixture
    def mock_audit_repository(self):
        """Mock audit repository."""
        mock_repo = AsyncMock()
        mock_repo.create.return_value = MagicMock()
        return mock_repo

    @pytest.fixture
    def mock_advanced_features(self):
        """Mock advanced features."""
        mock_features = AsyncMock()
        mock_correlation_manager = MagicMock()
        mock_correlation_manager.generate_correlation_id.return_value = "corr_test_123"
        mock_features.correlation_manager = mock_correlation_manager
        mock_features.track_payment_status_change.return_value = None
        mock_features.store_payment_metadata.return_value = None
        mock_features.update_payment_metadata.return_value = None
        mock_features.get_payment_status_history.return_value = []
        mock_features.get_payment_metadata.return_value = {}
        mock_features.search_payments.return_value = []
        mock_features.get_circuit_breaker_metrics.return_value = {}
        return mock_features

    @pytest.fixture
    def mock_authorize_net_client(self):
        """Mock Authorize.net client."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.transaction_id = "test_trans_123"
        mock_response.status = "captured"
        mock_response.response_code = "1"
        mock_response.response_text = "Approved"
        mock_client.void_transaction.return_value = mock_response
        return mock_client

    @pytest.fixture
    def payment_service(
        self, 
        mock_session, 
        mock_payment_repository, 
        mock_audit_repository,
        mock_advanced_features,
        mock_authorize_net_client
    ):
        """Create PaymentService instance with mocked dependencies."""
        with patch('src.core.services.payment_service.PaymentRepository', return_value=mock_payment_repository), \
             patch('src.core.services.payment_service.AuditLogRepository', return_value=mock_audit_repository), \
             patch('src.core.services.payment_service.AdvancedPaymentFeatures', return_value=mock_advanced_features), \
             patch('src.core.services.payment_service.AuthorizeNetClient', return_value=mock_authorize_net_client):
            
            service = PaymentService(mock_session)
            service.payment_repository = mock_payment_repository
            service.audit_repository = mock_audit_repository
            service.advanced_features = mock_advanced_features
            service.authorize_net_client = mock_authorize_net_client
            return service

    @pytest.fixture
    def sample_payment_create_request(self):
        """Sample payment create request."""
        return PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123456789",
            description="Test payment",
            metadata={"order_id": "order_123"},
            is_test=True
        )

    @pytest.fixture
    def sample_payment(self):
        """Sample payment instance."""
        payment = MagicMock(spec=Payment)
        payment.id = uuid.uuid4()
        payment.external_id = "pay_test_123"
        payment.amount = Decimal("10.00")
        payment.currency = "USD"
        payment.status = PaymentStatus.PENDING
        payment.payment_method = PaymentMethod.CREDIT_CARD.value
        payment.customer_id = "cust_123"
        payment.customer_email = "test@example.com"
        payment.customer_name = "Test Customer"
        payment.card_token = "tok_123456789"
        payment.description = "Test payment"
        payment.payment_metadata = {"order_id": "order_123"}
        payment.is_test = True
        payment.is_live = False
        payment.refunded_amount = Decimal("0")
        payment.refund_count = 0
        payment.authorize_net_transaction_id = None
        payment.is_refundable = False
        payment.is_voidable = True
        payment.remaining_refund_amount = Decimal("10.00")
        return payment

    # Test create_payment method
    async def test_create_payment_success(self, payment_service, sample_payment_create_request, sample_payment):
        """Test successful payment creation."""
        # Arrange
        payment_service.payment_repository.create.return_value = sample_payment
        
        # Act
        result = await payment_service.create_payment(sample_payment_create_request)
        
        # Assert
        assert result == sample_payment
        payment_service.payment_repository.create.assert_called_once()
        payment_service.advanced_features.track_payment_status_change.assert_called_once()
        payment_service.advanced_features.store_payment_metadata.assert_called_once()

    async def test_create_payment_with_correlation_id(self, payment_service, sample_payment_create_request, sample_payment):
        """Test payment creation with provided correlation ID."""
        # Arrange
        correlation_id = "custom_corr_123"
        payment_service.payment_repository.create.return_value = sample_payment
        
        # Act
        result = await payment_service.create_payment(sample_payment_create_request, correlation_id)
        
        # Assert
        assert result == sample_payment
        # Verify correlation ID was used in logging
        payment_service.advanced_features.track_payment_status_change.assert_called_once()

    async def test_create_payment_validation_error_amount_zero(self, payment_service):
        """Test payment creation with zero amount validation error."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("0"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Payment amount must be greater than 0"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_validation_error_amount_negative(self, payment_service):
        """Test payment creation with negative amount validation error."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("-10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Payment amount must be greater than 0"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_validation_error_amount_too_large(self, payment_service):
        """Test payment creation with amount exceeding maximum."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("1000000.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Payment amount cannot exceed 999,999.99"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_validation_error_invalid_currency(self, payment_service):
        """Test payment creation with invalid currency."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="INVALID",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Currency must be a 3-character code"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_validation_error_invalid_payment_method(self, payment_service):
        """Test payment creation with invalid payment method."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method="invalid_method",
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid payment method"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_validation_error_invalid_email(self, payment_service):
        """Test payment creation with invalid email format."""
        # Arrange
        invalid_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="invalid-email",
            card_token="tok_123456789",
            is_test=True
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid email format"):
            await payment_service.create_payment(invalid_request)

    async def test_create_payment_database_error(self, payment_service, sample_payment_create_request):
        """Test payment creation with database error."""
        # Arrange
        payment_service.payment_repository.create.side_effect = DatabaseError("Database connection failed")
        
        # Act & Assert
        with pytest.raises(DatabaseError):
            await payment_service.create_payment(sample_payment_create_request)

    async def test_create_payment_unexpected_error(self, payment_service, sample_payment_create_request):
        """Test payment creation with unexpected error."""
        # Arrange
        payment_service.payment_repository.create.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(PaymentError, match="Failed to create payment"):
            await payment_service.create_payment(sample_payment_create_request)

    # Test get_payment method
    async def test_get_payment_success(self, payment_service, sample_payment):
        """Test successful payment retrieval."""
        # Arrange
        payment_id = sample_payment.id
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act
        result = await payment_service.get_payment(payment_id)
        
        # Assert
        assert result == sample_payment
        payment_service.payment_repository.get_by_id.assert_called_once_with(payment_id)

    async def test_get_payment_not_found(self, payment_service):
        """Test payment retrieval when payment not found."""
        # Arrange
        payment_id = uuid.uuid4()
        payment_service.payment_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(PaymentNotFoundError, match=f"Payment {payment_id} not found"):
            await payment_service.get_payment(payment_id)

    async def test_get_payment_database_error(self, payment_service):
        """Test payment retrieval with database error."""
        # Arrange
        payment_id = uuid.uuid4()
        payment_service.payment_repository.get_by_id.side_effect = DatabaseError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError):
            await payment_service.get_payment(payment_id)

    # Test get_payment_by_external_id method
    async def test_get_payment_by_external_id_success(self, payment_service, sample_payment):
        """Test successful payment retrieval by external ID."""
        # Arrange
        external_id = sample_payment.external_id
        payment_service.payment_repository.get_by_external_id.return_value = sample_payment
        
        # Act
        result = await payment_service.get_payment_by_external_id(external_id)
        
        # Assert
        assert result == sample_payment
        payment_service.payment_repository.get_by_external_id.assert_called_once_with(external_id)

    async def test_get_payment_by_external_id_not_found(self, payment_service):
        """Test payment retrieval by external ID when not found."""
        # Arrange
        external_id = "pay_nonexistent"
        payment_service.payment_repository.get_by_external_id.return_value = None
        
        # Act & Assert
        with pytest.raises(PaymentNotFoundError, match=f"Payment with external ID {external_id} not found"):
            await payment_service.get_payment_by_external_id(external_id)

    # Test update_payment method
    async def test_update_payment_success(self, payment_service, sample_payment):
        """Test successful payment update."""
        # Arrange
        payment_id = sample_payment.id
        update_request = PaymentUpdateRequest(
            description="Updated description",
            metadata={"updated": True}
        )
        updated_payment = MagicMock(spec=Payment)
        updated_payment.id = payment_id
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        payment_service.payment_repository.update.return_value = updated_payment
        
        # Act
        result = await payment_service.update_payment(payment_id, update_request)
        
        # Assert
        assert result == updated_payment
        payment_service.payment_repository.update.assert_called_once()
        payment_service.audit_repository.create.assert_called_once()

    async def test_update_payment_validation_error_no_fields(self, payment_service, sample_payment):
        """Test payment update with no fields provided."""
        # Arrange
        payment_id = sample_payment.id
        update_request = PaymentUpdateRequest(description=None, metadata=None)
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act & Assert
        with pytest.raises(ValidationError, match="At least one field must be provided for update"):
            await payment_service.update_payment(payment_id, update_request)

    async def test_update_payment_not_found(self, payment_service):
        """Test payment update when payment not found."""
        # Arrange
        payment_id = uuid.uuid4()
        update_request = PaymentUpdateRequest(description="Updated")
        
        payment_service.payment_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(PaymentNotFoundError):
            await payment_service.update_payment(payment_id, update_request)

    # Test refund_payment method
    async def test_refund_payment_success(self, payment_service, sample_payment):
        """Test successful payment refund."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.CAPTURED
        sample_payment.is_refundable = True
        sample_payment.remaining_refund_amount = Decimal("10.00")
        
        refund_request = PaymentRefundRequest(
            amount=Decimal("5.00"),
            reason="Customer request"
        )
        
        updated_payment = MagicMock(spec=Payment)
        updated_payment.id = payment_id
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        payment_service.payment_repository.update.return_value = updated_payment
        
        # Act
        result = await payment_service.refund_payment(payment_id, refund_request)
        
        # Assert
        assert result == updated_payment
        payment_service.payment_repository.update.assert_called_once()
        payment_service.audit_repository.create.assert_called_once()

    async def test_refund_payment_not_refundable(self, payment_service, sample_payment):
        """Test refund when payment is not refundable."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.PENDING
        sample_payment.is_refundable = False
        
        refund_request = PaymentRefundRequest(amount=Decimal("5.00"))
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Payment cannot be refunded"):
            await payment_service.refund_payment(payment_id, refund_request)

    async def test_refund_payment_amount_exceeds_remaining(self, payment_service, sample_payment):
        """Test refund when amount exceeds remaining refundable amount."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.CAPTURED
        sample_payment.is_refundable = True
        sample_payment.remaining_refund_amount = Decimal("5.00")
        
        refund_request = PaymentRefundRequest(amount=Decimal("10.00"))
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Refund amount.*exceeds remaining refundable amount"):
            await payment_service.refund_payment(payment_id, refund_request)

    async def test_refund_payment_zero_amount(self, payment_service, sample_payment):
        """Test refund with zero amount."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.CAPTURED
        sample_payment.is_refundable = True
        
        refund_request = PaymentRefundRequest(amount=Decimal("0"))
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Refund amount must be greater than 0"):
            await payment_service.refund_payment(payment_id, refund_request)

    # Test cancel_payment method
    async def test_cancel_payment_success(self, payment_service, sample_payment):
        """Test successful payment cancellation."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.PENDING
        sample_payment.is_voidable = True
        
        cancel_request = PaymentCancelRequest(reason="Customer cancelled")
        
        updated_payment = MagicMock(spec=Payment)
        updated_payment.id = payment_id
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        payment_service.payment_repository.update.return_value = updated_payment
        
        # Act
        result = await payment_service.cancel_payment(payment_id, cancel_request)
        
        # Assert
        assert result == updated_payment
        payment_service.payment_repository.update.assert_called_once()
        payment_service.audit_repository.create.assert_called_once()

    async def test_cancel_payment_not_voidable(self, payment_service, sample_payment):
        """Test cancellation when payment is not voidable."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.CAPTURED
        sample_payment.is_voidable = False
        
        cancel_request = PaymentCancelRequest(reason="Customer cancelled")
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Payment cannot be cancelled"):
            await payment_service.cancel_payment(payment_id, cancel_request)

    # Test list_payments method
    async def test_list_payments_success(self, payment_service):
        """Test successful payment listing."""
        # Arrange
        expected_result = {
            "payments": [MagicMock()],
            "total": 1,
            "page": 1,
            "per_page": 20
        }
        payment_service.payment_repository.list_payments.return_value = expected_result
        
        # Act
        result = await payment_service.list_payments()
        
        # Assert
        assert result == expected_result
        payment_service.payment_repository.list_payments.assert_called_once()

    async def test_list_payments_with_filters(self, payment_service):
        """Test payment listing with filters."""
        # Arrange
        expected_result = {"payments": [], "total": 0, "page": 1, "per_page": 10}
        payment_service.payment_repository.list_payments.return_value = expected_result
        
        # Act
        result = await payment_service.list_payments(
            customer_id="cust_123",
            status=PaymentStatus.PENDING,
            page=1,
            per_page=10
        )
        
        # Assert
        assert result == expected_result
        payment_service.payment_repository.list_payments.assert_called_once_with(
            customer_id="cust_123",
            status=PaymentStatus.PENDING,
            start_date=None,
            end_date=None,
            page=1,
            per_page=10,
            order_by="created_at",
            order_direction="desc"
        )

    # Test search_payments method
    async def test_search_payments_success(self, payment_service):
        """Test successful payment search."""
        # Arrange
        expected_result = {
            "payments": [MagicMock()],
            "total": 1,
            "page": 1,
            "per_page": 20
        }
        payment_service.payment_repository.search_payments.return_value = expected_result
        
        # Act
        result = await payment_service.search_payments("test search")
        
        # Assert
        assert result == expected_result
        payment_service.payment_repository.search_payments.assert_called_once_with(
            search_term="test search",
            page=1,
            per_page=20
        )

    # Test get_payment_stats method
    async def test_get_payment_stats_success(self, payment_service):
        """Test successful payment statistics retrieval."""
        # Arrange
        expected_stats = {
            "total_count": 100,
            "total_amount": Decimal("1000.00"),
            "successful_count": 95,
            "failed_count": 5
        }
        payment_service.payment_repository.get_payment_stats.return_value = expected_stats
        
        # Act
        result = await payment_service.get_payment_stats()
        
        # Assert
        assert result == expected_stats
        payment_service.payment_repository.get_payment_stats.assert_called_once()

    # Test advanced features methods
    async def test_get_payment_status_history_with_advanced_features(self, payment_service):
        """Test getting payment status history with advanced features available."""
        # Arrange
        payment_id = uuid.uuid4()
        expected_history = [{"status": "pending", "timestamp": "2024-01-01T00:00:00Z"}]
        payment_service.advanced_features.get_payment_status_history.return_value = expected_history
        
        # Act
        result = await payment_service.get_payment_status_history(payment_id)
        
        # Assert
        assert result == expected_history
        payment_service.advanced_features.get_payment_status_history.assert_called_once_with(str(payment_id))

    async def test_get_payment_status_history_without_advanced_features(self, payment_service):
        """Test getting payment status history without advanced features."""
        # Arrange
        payment_id = uuid.uuid4()
        payment_service.advanced_features = None
        
        # Act
        result = await payment_service.get_payment_status_history(payment_id)
        
        # Assert
        assert result == []

    async def test_get_payment_metadata_with_advanced_features(self, payment_service):
        """Test getting payment metadata with advanced features available."""
        # Arrange
        payment_id = uuid.uuid4()
        expected_metadata = {"order_id": "order_123", "source": "web"}
        payment_service.advanced_features.get_payment_metadata.return_value = expected_metadata
        
        # Act
        result = await payment_service.get_payment_metadata(payment_id)
        
        # Assert
        assert result == expected_metadata
        payment_service.advanced_features.get_payment_metadata.assert_called_once_with(str(payment_id))

    async def test_get_payment_metadata_without_advanced_features(self, payment_service):
        """Test getting payment metadata without advanced features."""
        # Arrange
        payment_id = uuid.uuid4()
        payment_service.advanced_features = None
        
        # Act
        result = await payment_service.get_payment_metadata(payment_id)
        
        # Assert
        assert result is None

    # Test context manager methods
    async def test_context_manager_entry(self, payment_service):
        """Test async context manager entry."""
        # Act
        result = await payment_service.__aenter__()
        
        # Assert
        assert result == payment_service

    async def test_context_manager_exit(self, payment_service):
        """Test async context manager exit."""
        # Act
        await payment_service.__aexit__(None, None, None)
        
        # Assert
        payment_service.authorize_net_client.close.assert_called_once()

    async def test_close_method(self, payment_service):
        """Test close method."""
        # Act
        await payment_service.close()
        
        # Assert
        payment_service.authorize_net_client.close.assert_called_once()

    # Test circuit breaker metrics
    def test_get_circuit_breaker_metrics_with_advanced_features(self, payment_service):
        """Test getting circuit breaker metrics with advanced features."""
        # Arrange
        expected_metrics = {"status": "closed", "failure_count": 0}
        payment_service.advanced_features.get_circuit_breaker_metrics.return_value = expected_metrics
        
        # Act
        result = payment_service.get_circuit_breaker_metrics()
        
        # Assert
        assert result == expected_metrics

    def test_get_circuit_breaker_metrics_without_advanced_features(self, payment_service):
        """Test getting circuit breaker metrics without advanced features."""
        # Arrange
        payment_service.advanced_features = None
        
        # Act
        result = payment_service.get_circuit_breaker_metrics()
        
        # Assert
        assert result == {}

    # Test edge cases and boundary conditions
    async def test_create_payment_with_maximum_valid_amount(self, payment_service):
        """Test payment creation with maximum valid amount."""
        # Arrange
        max_amount_request = PaymentCreateRequest(
            amount=Decimal("999999.99"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        sample_payment = MagicMock(spec=Payment)
        payment_service.payment_repository.create.return_value = sample_payment
        
        # Act
        result = await payment_service.create_payment(max_amount_request)
        
        # Assert
        assert result == sample_payment

    async def test_create_payment_with_minimum_valid_amount(self, payment_service):
        """Test payment creation with minimum valid amount."""
        # Arrange
        min_amount_request = PaymentCreateRequest(
            amount=Decimal("0.01"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            card_token="tok_123456789",
            is_test=True
        )
        
        sample_payment = MagicMock(spec=Payment)
        payment_service.payment_repository.create.return_value = sample_payment
        
        # Act
        result = await payment_service.create_payment(min_amount_request)
        
        # Assert
        assert result == sample_payment

    async def test_create_payment_with_all_payment_methods(self, payment_service):
        """Test payment creation with all valid payment methods."""
        for method in PaymentMethod:
            # Arrange
            request = PaymentCreateRequest(
                amount=Decimal("10.00"),
                currency="USD",
                payment_method=method.value,
                customer_id="cust_123",
                customer_email="test@example.com",
                card_token="tok_123456789",
                is_test=True
            )
            
            sample_payment = MagicMock(spec=Payment)
            payment_service.payment_repository.create.return_value = sample_payment
            
            # Act
            result = await payment_service.create_payment(request)
            
            # Assert
            assert result == sample_payment

    async def test_create_payment_without_optional_fields(self, payment_service):
        """Test payment creation without optional fields."""
        # Arrange
        minimal_request = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            card_token="tok_123456789",
            is_test=True
        )
        
        sample_payment = MagicMock(spec=Payment)
        payment_service.payment_repository.create.return_value = sample_payment
        
        # Act
        result = await payment_service.create_payment(minimal_request)
        
        # Assert
        assert result == sample_payment

    # Test error handling scenarios
    async def test_refund_payment_external_service_error(self, payment_service, sample_payment):
        """Test refund payment with external service error."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.CAPTURED
        sample_payment.is_refundable = True
        sample_payment.authorize_net_transaction_id = "trans_123"
        
        refund_request = PaymentRefundRequest(amount=Decimal("5.00"))
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        payment_service.authorize_net_client.refund.side_effect = Exception("External service error")
        
        # Act & Assert
        with pytest.raises(ExternalServiceError, match="Refund processing failed"):
            await payment_service.refund_payment(payment_id, refund_request)

    async def test_cancel_payment_external_service_error(self, payment_service, sample_payment):
        """Test cancel payment with external service error."""
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = PaymentStatus.PENDING
        sample_payment.is_voidable = True
        sample_payment.authorize_net_transaction_id = "trans_123"
        
        cancel_request = PaymentCancelRequest(reason="Customer cancelled")
        
        payment_service.payment_repository.get_by_id.return_value = sample_payment
        payment_service.authorize_net_client.void_transaction.side_effect = Exception("External service error")
        
        # Act & Assert
        with pytest.raises(ExternalServiceError, match="Cancellation processing failed"):
            await payment_service.cancel_payment(payment_id, cancel_request)
