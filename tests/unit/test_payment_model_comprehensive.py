"""
EasyPay Payment Gateway - Comprehensive Payment Model Unit Tests
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod


class TestPaymentModel:
    """Comprehensive test suite for Payment model."""

    @pytest.fixture
    def sample_payment_data(self):
        """Sample payment data for testing."""
        return {
            "external_id": "pay_test_123",
            "amount": Decimal("10.00"),
            "currency": "USD",
            "status": PaymentStatus.PENDING,
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_123",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_123456789",
            "description": "Test payment",
            "payment_metadata": {"order_id": "order_123"},
            "is_test": True,
            "is_live": False,
            "refunded_amount": Decimal("0"),
            "refund_count": 0
        }

    @pytest.fixture
    def sample_payment(self, sample_payment_data):
        """Create a sample payment instance."""
        return Payment(**sample_payment_data)

    # Test PaymentStatus enum
    def test_payment_status_enum_values(self):
        """Test that PaymentStatus enum has correct values."""
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.AUTHORIZED == "authorized"
        assert PaymentStatus.CAPTURED == "captured"
        assert PaymentStatus.SETTLED == "settled"
        assert PaymentStatus.REFUNDED == "refunded"
        assert PaymentStatus.PARTIALLY_REFUNDED == "partially_refunded"
        assert PaymentStatus.VOIDED == "voided"
        assert PaymentStatus.FAILED == "failed"
        assert PaymentStatus.DECLINED == "declined"

    def test_payment_status_enum_membership(self):
        """Test PaymentStatus enum membership."""
        assert "pending" in PaymentStatus.__members__.values()
        assert "authorized" in PaymentStatus.__members__.values()
        assert "captured" in PaymentStatus.__members__.values()
        assert "settled" in PaymentStatus.__members__.values()
        assert "refunded" in PaymentStatus.__members__.values()
        assert "partially_refunded" in PaymentStatus.__members__.values()
        assert "voided" in PaymentStatus.__members__.values()
        assert "failed" in PaymentStatus.__members__.values()
        assert "declined" in PaymentStatus.__members__.values()

    # Test PaymentMethod enum
    def test_payment_method_enum_values(self):
        """Test that PaymentMethod enum has correct values."""
        assert PaymentMethod.CREDIT_CARD == "credit_card"
        assert PaymentMethod.DEBIT_CARD == "debit_card"
        assert PaymentMethod.BANK_TRANSFER == "bank_transfer"
        assert PaymentMethod.DIGITAL_WALLET == "digital_wallet"

    def test_payment_method_enum_membership(self):
        """Test PaymentMethod enum membership."""
        assert "credit_card" in PaymentMethod.__members__.values()
        assert "debit_card" in PaymentMethod.__members__.values()
        assert "bank_transfer" in PaymentMethod.__members__.values()
        assert "digital_wallet" in PaymentMethod.__members__.values()

    # Test Payment model creation
    def test_payment_creation_with_all_fields(self, sample_payment_data):
        """Test payment creation with all fields."""
        payment = Payment(**sample_payment_data)
        
        assert payment.external_id == "pay_test_123"
        assert payment.amount == Decimal("10.00")
        assert payment.currency == "USD"
        assert payment.status == PaymentStatus.PENDING
        assert payment.payment_method == PaymentMethod.CREDIT_CARD.value
        assert payment.customer_id == "cust_123"
        assert payment.customer_email == "test@example.com"
        assert payment.customer_name == "Test Customer"
        assert payment.card_token == "tok_123456789"
        assert payment.description == "Test payment"
        assert payment.payment_metadata == {"order_id": "order_123"}
        assert payment.is_test is True
        assert payment.is_live is False
        assert payment.refunded_amount == Decimal("0")
        assert payment.refund_count == 0

    def test_payment_creation_with_minimal_fields(self):
        """Test payment creation with minimal required fields."""
        minimal_data = {
            "external_id": "pay_minimal_123",
            "amount": Decimal("5.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value
        }
        
        payment = Payment(**minimal_data)
        
        assert payment.external_id == "pay_minimal_123"
        assert payment.amount == Decimal("5.00")
        assert payment.currency == "USD"
        assert payment.payment_method == PaymentMethod.CREDIT_CARD.value
        assert payment.status == PaymentStatus.PENDING  # Default value
        assert payment.is_test is False  # Default value
        assert payment.is_live is False  # Default value

    def test_payment_creation_with_default_values(self):
        """Test payment creation with default values."""
        minimal_data = {
            "external_id": "pay_default_123",
            "amount": Decimal("5.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value
        }
        
        payment = Payment(**minimal_data)
        
        # Test default values
        assert payment.status == PaymentStatus.PENDING
        assert payment.is_test is False
        assert payment.is_live is False
        assert payment.refunded_amount == Decimal("0")
        assert payment.refund_count is None
        assert payment.customer_id is None
        assert payment.customer_email is None
        assert payment.customer_name is None
        assert payment.card_token is None
        assert payment.description is None
        assert payment.payment_metadata is None

    def test_payment_id_generation(self, sample_payment_data):
        """Test that payment ID is automatically generated."""
        payment = Payment(**sample_payment_data)
        
        assert payment.id is not None
        assert isinstance(payment.id, uuid.UUID)

    def test_payment_timestamps(self, sample_payment_data):
        """Test that payment timestamps are automatically set."""
        payment = Payment(**sample_payment_data)
        
        assert payment.created_at is not None
        assert payment.updated_at is not None
        assert isinstance(payment.created_at, datetime)
        assert isinstance(payment.updated_at, datetime)
        assert payment.created_at <= datetime.utcnow()
        assert payment.updated_at <= datetime.utcnow()

    # Test Payment properties
    def test_is_refundable_property_captured_status(self, sample_payment_data):
        """Test is_refundable property with captured status."""
        sample_payment_data["status"] = PaymentStatus.CAPTURED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is True

    def test_is_refundable_property_settled_status(self, sample_payment_data):
        """Test is_refundable property with settled status."""
        sample_payment_data["status"] = PaymentStatus.SETTLED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is True

    def test_is_refundable_property_pending_status(self, sample_payment_data):
        """Test is_refundable property with pending status."""
        sample_payment_data["status"] = PaymentStatus.PENDING
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_refundable_property_authorized_status(self, sample_payment_data):
        """Test is_refundable property with authorized status."""
        sample_payment_data["status"] = PaymentStatus.AUTHORIZED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_refundable_property_refunded_status(self, sample_payment_data):
        """Test is_refundable property with refunded status."""
        sample_payment_data["status"] = PaymentStatus.REFUNDED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_refundable_property_voided_status(self, sample_payment_data):
        """Test is_refundable property with voided status."""
        sample_payment_data["status"] = PaymentStatus.VOIDED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_refundable_property_failed_status(self, sample_payment_data):
        """Test is_refundable property with failed status."""
        sample_payment_data["status"] = PaymentStatus.FAILED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_refundable_property_declined_status(self, sample_payment_data):
        """Test is_refundable property with declined status."""
        sample_payment_data["status"] = PaymentStatus.DECLINED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_refundable is False

    def test_is_voidable_property_pending_status(self, sample_payment_data):
        """Test is_voidable property with pending status."""
        sample_payment_data["status"] = PaymentStatus.PENDING
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is True

    def test_is_voidable_property_authorized_status(self, sample_payment_data):
        """Test is_voidable property with authorized status."""
        sample_payment_data["status"] = PaymentStatus.AUTHORIZED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is True

    def test_is_voidable_property_captured_status(self, sample_payment_data):
        """Test is_voidable property with captured status."""
        sample_payment_data["status"] = PaymentStatus.CAPTURED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_is_voidable_property_settled_status(self, sample_payment_data):
        """Test is_voidable property with settled status."""
        sample_payment_data["status"] = PaymentStatus.SETTLED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_is_voidable_property_refunded_status(self, sample_payment_data):
        """Test is_voidable property with refunded status."""
        sample_payment_data["status"] = PaymentStatus.REFUNDED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_is_voidable_property_voided_status(self, sample_payment_data):
        """Test is_voidable property with voided status."""
        sample_payment_data["status"] = PaymentStatus.VOIDED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_is_voidable_property_failed_status(self, sample_payment_data):
        """Test is_voidable property with failed status."""
        sample_payment_data["status"] = PaymentStatus.FAILED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_is_voidable_property_declined_status(self, sample_payment_data):
        """Test is_voidable property with declined status."""
        sample_payment_data["status"] = PaymentStatus.DECLINED
        payment = Payment(**sample_payment_data)
        
        assert payment.is_voidable is False

    def test_remaining_refund_amount_no_refunds(self, sample_payment_data):
        """Test remaining_refund_amount with no previous refunds."""
        sample_payment_data["refunded_amount"] = None
        payment = Payment(**sample_payment_data)
        
        assert payment.remaining_refund_amount == Decimal("10.00")

    def test_remaining_refund_amount_with_refunds(self, sample_payment_data):
        """Test remaining_refund_amount with previous refunds."""
        sample_payment_data["refunded_amount"] = Decimal("3.00")
        payment = Payment(**sample_payment_data)
        
        assert payment.remaining_refund_amount == Decimal("7.00")

    def test_remaining_refund_amount_full_refund(self, sample_payment_data):
        """Test remaining_refund_amount with full refund."""
        sample_payment_data["refunded_amount"] = Decimal("10.00")
        payment = Payment(**sample_payment_data)
        
        assert payment.remaining_refund_amount == Decimal("0.00")

    def test_remaining_refund_amount_zero_refunded(self, sample_payment_data):
        """Test remaining_refund_amount with zero refunded amount."""
        sample_payment_data["refunded_amount"] = Decimal("0")
        payment = Payment(**sample_payment_data)
        
        assert payment.remaining_refund_amount == Decimal("10.00")

    # Test Payment string representation
    def test_payment_repr(self, sample_payment_data):
        """Test payment string representation."""
        payment = Payment(**sample_payment_data)
        repr_str = repr(payment)
        
        assert "Payment" in repr_str
        assert "pay_test_123" in repr_str
        assert "10.00" in repr_str
        assert "pending" in repr_str

    # Test Payment with different currencies
    def test_payment_with_different_currencies(self):
        """Test payment creation with different currencies."""
        currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
        
        for currency in currencies:
            payment_data = {
                "external_id": f"pay_{currency.lower()}_123",
                "amount": Decimal("10.00"),
                "currency": currency,
                "payment_method": PaymentMethod.CREDIT_CARD.value
            }
            
            payment = Payment(**payment_data)
            assert payment.currency == currency

    # Test Payment with different amounts
    def test_payment_with_different_amounts(self):
        """Test payment creation with different amounts."""
        amounts = [
            Decimal("0.01"),  # Minimum amount
            Decimal("1.00"),   # Small amount
            Decimal("100.00"), # Medium amount
            Decimal("999999.99") # Maximum amount
        ]
        
        for amount in amounts:
            payment_data = {
                "external_id": f"pay_amount_{amount}",
                "amount": amount,
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value
            }
            
            payment = Payment(**payment_data)
            assert payment.amount == amount

    # Test Payment with different payment methods
    def test_payment_with_different_payment_methods(self):
        """Test payment creation with different payment methods."""
        for method in PaymentMethod:
            payment_data = {
                "external_id": f"pay_{method.value}_123",
                "amount": Decimal("10.00"),
                "currency": "USD",
                "payment_method": method.value
            }
            
            payment = Payment(**payment_data)
            assert payment.payment_method == method.value

    # Test Payment with metadata
    def test_payment_with_complex_metadata(self, sample_payment_data):
        """Test payment creation with complex metadata."""
        complex_metadata = {
            "order_id": "order_123",
            "customer_info": {
                "segment": "premium",
                "lifetime_value": 1000.00
            },
            "transaction_details": {
                "source": "web",
                "campaign": "summer_sale",
                "referrer": "google.com"
            },
            "risk_score": 0.15,
            "fraud_checks": ["velocity", "address_verification"],
            "tags": ["high_value", "repeat_customer"]
        }
        
        sample_payment_data["payment_metadata"] = complex_metadata
        payment = Payment(**sample_payment_data)
        
        assert payment.payment_metadata == complex_metadata
        assert payment.payment_metadata["customer_info"]["segment"] == "premium"
        assert payment.payment_metadata["transaction_details"]["source"] == "web"
        assert payment.payment_metadata["risk_score"] == 0.15

    # Test Payment with card information
    def test_payment_with_card_information(self, sample_payment_data):
        """Test payment creation with card information."""
        sample_payment_data.update({
            "card_last_four": "4242",
            "card_brand": "visa",
            "card_exp_month": "12",
            "card_exp_year": "2025"
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.card_last_four == "4242"
        assert payment.card_brand == "visa"
        assert payment.card_exp_month == "12"
        assert payment.card_exp_year == "2025"

    # Test Payment with processor information
    def test_payment_with_processor_information(self, sample_payment_data):
        """Test payment creation with processor information."""
        sample_payment_data.update({
            "processor_response_code": "1",
            "processor_response_message": "Approved",
            "processor_transaction_id": "proc_trans_123",
            "authorize_net_transaction_id": "auth_net_123"
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.processor_response_code == "1"
        assert payment.processor_response_message == "Approved"
        assert payment.processor_transaction_id == "proc_trans_123"
        assert payment.authorize_net_transaction_id == "auth_net_123"

    # Test Payment with refund information
    def test_payment_with_refund_information(self, sample_payment_data):
        """Test payment creation with refund information."""
        sample_payment_data.update({
            "refunded_amount": Decimal("5.00"),
            "refund_count": 2
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.refunded_amount == Decimal("5.00")
        assert payment.refund_count == 2
        assert payment.remaining_refund_amount == Decimal("5.00")

    # Test Payment with timestamps
    def test_payment_with_custom_timestamps(self, sample_payment_data):
        """Test payment creation with custom timestamps."""
        now = datetime.utcnow()
        processed_at = now + timedelta(minutes=1)
        settled_at = now + timedelta(hours=1)
        
        sample_payment_data.update({
            "created_at": now,
            "updated_at": now,
            "processed_at": processed_at,
            "settled_at": settled_at
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.created_at == now
        assert payment.updated_at == now
        assert payment.processed_at == processed_at
        assert payment.settled_at == settled_at

    # Test Payment flags
    def test_payment_flags_combinations(self):
        """Test payment creation with different flag combinations."""
        # Test payment
        test_payment_data = {
            "external_id": "pay_test_123",
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "is_test": True,
            "is_live": False
        }
        
        test_payment = Payment(**test_payment_data)
        assert test_payment.is_test is True
        assert test_payment.is_live is False
        
        # Live payment
        live_payment_data = {
            "external_id": "pay_live_123",
            "amount": Decimal("10.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "is_test": False,
            "is_live": True
        }
        
        live_payment = Payment(**live_payment_data)
        assert live_payment.is_test is False
        assert live_payment.is_live is True

    # Test edge cases
    def test_payment_with_empty_strings(self, sample_payment_data):
        """Test payment creation with empty string values."""
        sample_payment_data.update({
            "customer_id": "",
            "customer_email": "",
            "customer_name": "",
            "description": "",
            "card_token": ""
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.customer_id == ""
        assert payment.customer_email == ""
        assert payment.customer_name == ""
        assert payment.description == ""
        assert payment.card_token == ""

    def test_payment_with_none_values(self, sample_payment_data):
        """Test payment creation with None values."""
        sample_payment_data.update({
            "customer_id": None,
            "customer_email": None,
            "customer_name": None,
            "description": None,
            "card_token": None,
            "payment_metadata": None
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.customer_id is None
        assert payment.customer_email is None
        assert payment.customer_name is None
        assert payment.description is None
        assert payment.card_token is None
        assert payment.payment_metadata is None

    def test_payment_with_very_long_strings(self, sample_payment_data):
        """Test payment creation with very long string values."""
        long_string = "x" * 1000
        
        sample_payment_data.update({
            "description": long_string,
            "customer_name": long_string[:255]  # Truncated to max length
        })
        
        payment = Payment(**sample_payment_data)
        
        assert payment.description == long_string
        assert len(payment.customer_name) <= 255

    # Test Payment model validation (if any)
    def test_payment_model_equality(self, sample_payment_data):
        """Test payment model equality."""
        payment1 = Payment(**sample_payment_data)
        payment2 = Payment(**sample_payment_data)
        
        # Payments with different IDs should not be equal
        assert payment1 != payment2
        
        # But they should have the same external_id
        assert payment1.external_id == payment2.external_id

    def test_payment_model_hash(self, sample_payment_data):
        """Test payment model hash."""
        payment = Payment(**sample_payment_data)
        
        # Should be hashable
        hash_value = hash(payment)
        assert isinstance(hash_value, int)

    # Test Payment model serialization
    def test_payment_model_to_dict(self, sample_payment_data):
        """Test payment model to dictionary conversion."""
        payment = Payment(**sample_payment_data)
        
        # Convert to dict (if method exists)
        if hasattr(payment, 'to_dict'):
            payment_dict = payment.to_dict()
            assert isinstance(payment_dict, dict)
            assert payment_dict['external_id'] == "pay_test_123"
            assert payment_dict['amount'] == Decimal("10.00")

    # Test Payment model with relationships
    def test_payment_model_relationships(self, sample_payment_data):
        """Test payment model relationships."""
        payment = Payment(**sample_payment_data)
        
        # Test that relationships are properly initialized
        assert hasattr(payment, 'webhooks')
        assert hasattr(payment, 'audit_logs')
        
        # Relationships should be empty initially
        assert payment.webhooks == []
        assert payment.audit_logs == []

    # Test Payment model with different status transitions
    def test_payment_status_transitions(self, sample_payment_data):
        """Test payment status transitions."""
        payment = Payment(**sample_payment_data)
        
        # Test initial status
        assert payment.status == PaymentStatus.PENDING
        assert payment.is_voidable is True
        assert payment.is_refundable is False
        
        # Simulate status change to authorized
        payment.status = PaymentStatus.AUTHORIZED
        assert payment.is_voidable is True
        assert payment.is_refundable is False
        
        # Simulate status change to captured
        payment.status = PaymentStatus.CAPTURED
        assert payment.is_voidable is False
        assert payment.is_refundable is True
        
        # Simulate status change to settled
        payment.status = PaymentStatus.SETTLED
        assert payment.is_voidable is False
        assert payment.is_refundable is True
        
        # Simulate status change to refunded
        payment.status = PaymentStatus.REFUNDED
        assert payment.is_voidable is False
        assert payment.is_refundable is False
        
        # Simulate status change to voided
        payment.status = PaymentStatus.VOIDED
        assert payment.is_voidable is False
        assert payment.is_refundable is False

    # Test Payment model with boundary amounts
    def test_payment_boundary_amounts(self):
        """Test payment creation with boundary amounts."""
        # Test minimum amount
        min_payment_data = {
            "external_id": "pay_min_123",
            "amount": Decimal("0.01"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value
        }
        
        min_payment = Payment(**min_payment_data)
        assert min_payment.amount == Decimal("0.01")
        assert min_payment.remaining_refund_amount == Decimal("0.01")
        
        # Test maximum amount
        max_payment_data = {
            "external_id": "pay_max_123",
            "amount": Decimal("999999.99"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value
        }
        
        max_payment = Payment(**max_payment_data)
        assert max_payment.amount == Decimal("999999.99")
        assert max_payment.remaining_refund_amount == Decimal("999999.99")

    # Test Payment model with decimal precision
    def test_payment_decimal_precision(self):
        """Test payment creation with decimal precision."""
        # Test with 2 decimal places
        payment_data = {
            "external_id": "pay_precision_123",
            "amount": Decimal("10.99"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value
        }
        
        payment = Payment(**payment_data)
        assert payment.amount == Decimal("10.99")
        
        # Test with more decimal places (should be handled by database)
        payment_data["amount"] = Decimal("10.999")
        payment = Payment(**payment_data)
        assert payment.amount == Decimal("10.999")
