"""
EasyPay Payment Gateway - Payment Test Fixtures
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.audit_log import AuditLog
from src.core.models.webhook import Webhook


class PaymentFixtures:
    """Factory class for creating test payment data."""
    
    @staticmethod
    def create_payment_data(**overrides) -> Dict[str, Any]:
        """Create basic payment data with optional overrides."""
        base_data = {
            "external_id": f"pay_{uuid.uuid4().hex[:12]}",
            "amount": Decimal("10.00"),
            "currency": "USD",
            "status": PaymentStatus.PENDING,
            "payment_method": PaymentMethod.CREDIT_CARD,
            "customer_id": f"cust_{uuid.uuid4().hex[:8]}",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": f"tok_{uuid.uuid4().hex[:12]}",
            "description": "Test payment",
            "payment_metadata": {"test": True, "source": "fixture"},
            "is_test": True,
            "is_live": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_completed_payment_data(**overrides) -> Dict[str, Any]:
        """Create completed payment data."""
        return PaymentFixtures.create_payment_data(
            status=PaymentStatus.COMPLETED,
            processor_transaction_id=f"proc_{uuid.uuid4().hex[:12]}",
            processor_response_code="1",
            processor_response_message="Approved",
            **overrides
        )
    
    @staticmethod
    def create_refunded_payment_data(**overrides) -> Dict[str, Any]:
        """Create refunded payment data."""
        return PaymentFixtures.create_payment_data(
            status=PaymentStatus.REFUNDED,
            refunded_amount=Decimal("10.00"),
            refund_count=1,
            processor_transaction_id=f"proc_{uuid.uuid4().hex[:12]}",
            **overrides
        )
    
    @staticmethod
    def create_partially_refunded_payment_data(**overrides) -> Dict[str, Any]:
        """Create partially refunded payment data."""
        return PaymentFixtures.create_payment_data(
            status=PaymentStatus.PARTIALLY_REFUNDED,
            refunded_amount=Decimal("5.00"),
            refund_count=1,
            processor_transaction_id=f"proc_{uuid.uuid4().hex[:12]}",
            **overrides
        )
    
    @staticmethod
    def create_voided_payment_data(**overrides) -> Dict[str, Any]:
        """Create voided payment data."""
        return PaymentFixtures.create_payment_data(
            status=PaymentStatus.VOIDED,
            processor_transaction_id=f"proc_{uuid.uuid4().hex[:12]}",
            **overrides
        )
    
    @staticmethod
    def create_failed_payment_data(**overrides) -> Dict[str, Any]:
        """Create failed payment data."""
        return PaymentFixtures.create_payment_data(
            status=PaymentStatus.FAILED,
            processor_response_code="2",
            processor_response_message="Declined",
            **overrides
        )
    
    @staticmethod
    def create_payment_with_customer(customer_id: str, **overrides) -> Dict[str, Any]:
        """Create payment data for specific customer."""
        return PaymentFixtures.create_payment_data(
            customer_id=customer_id,
            customer_email=f"{customer_id}@example.com",
            customer_name=f"Customer {customer_id}",
            **overrides
        )
    
    @staticmethod
    def create_payment_with_amount(amount: Decimal, **overrides) -> Dict[str, Any]:
        """Create payment data with specific amount."""
        return PaymentFixtures.create_payment_data(
            amount=amount,
            **overrides
        )
    
    @staticmethod
    def create_payment_with_status(status: PaymentStatus, **overrides) -> Dict[str, Any]:
        """Create payment data with specific status."""
        return PaymentFixtures.create_payment_data(
            status=status,
            **overrides
        )
    
    @staticmethod
    def create_payment_with_metadata(metadata: Dict[str, Any], **overrides) -> Dict[str, Any]:
        """Create payment data with specific metadata."""
        return PaymentFixtures.create_payment_data(
            payment_metadata=metadata,
            **overrides
        )
    
    @staticmethod
    def create_multiple_payments(count: int, **overrides) -> List[Dict[str, Any]]:
        """Create multiple payment data entries."""
        payments = []
        for i in range(count):
            payment_data = PaymentFixtures.create_payment_data(
                customer_id=f"cust_batch_{i}",
                customer_email=f"batch{i}@example.com",
                amount=Decimal(f"{10 + i * 5}.00"),
                description=f"Batch payment {i}",
                **overrides
            )
            payments.append(payment_data)
        return payments


class AuditLogFixtures:
    """Factory class for creating test audit log data."""
    
    @staticmethod
    def create_audit_log_data(**overrides) -> Dict[str, Any]:
        """Create basic audit log data with optional overrides."""
        base_data = {
            "payment_id": uuid.uuid4(),
            "action": "payment_created",
            "level": "info",
            "message": "Test audit log entry",
            "entity_type": "payment",
            "entity_id": str(uuid.uuid4()),
            "audit_metadata": {"test": True, "source": "fixture"},
            "user_id": None,
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent",
            "created_at": datetime.utcnow()
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_payment_audit_log(payment_id: uuid.UUID, action: str, **overrides) -> Dict[str, Any]:
        """Create audit log for specific payment action."""
        return AuditLogFixtures.create_audit_log_data(
            payment_id=payment_id,
            action=action,
            entity_type="payment",
            entity_id=str(payment_id),
            **overrides
        )
    
    @staticmethod
    def create_error_audit_log(**overrides) -> Dict[str, Any]:
        """Create error audit log data."""
        return AuditLogFixtures.create_audit_log_data(
            level="error",
            message="Test error audit log entry",
            **overrides
        )
    
    @staticmethod
    def create_warning_audit_log(**overrides) -> Dict[str, Any]:
        """Create warning audit log data."""
        return AuditLogFixtures.create_audit_log_data(
            level="warning",
            message="Test warning audit log entry",
            **overrides
        )


class WebhookFixtures:
    """Factory class for creating test webhook data."""
    
    @staticmethod
    def create_webhook_data(**overrides) -> Dict[str, Any]:
        """Create basic webhook data with optional overrides."""
        base_data = {
            "webhook_url": "https://example.com/webhook",
            "event_type": "payment.created",
            "is_active": True,
            "secret": f"secret_{uuid.uuid4().hex[:12]}",
            "metadata": {"test": True, "source": "fixture"},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_payment_webhook(event_type: str, **overrides) -> Dict[str, Any]:
        """Create webhook for payment events."""
        return WebhookFixtures.create_webhook_data(
            event_type=event_type,
            **overrides
        )
    
    @staticmethod
    def create_inactive_webhook(**overrides) -> Dict[str, Any]:
        """Create inactive webhook data."""
        return WebhookFixtures.create_webhook_data(
            is_active=False,
            **overrides
        )


class AuthorizeNetFixtures:
    """Factory class for creating test Authorize.net data."""
    
    @staticmethod
    def create_success_response(**overrides) -> Dict[str, Any]:
        """Create successful Authorize.net response."""
        base_response = {
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
        base_response.update(overrides)
        return base_response
    
    @staticmethod
    def create_declined_response(**overrides) -> Dict[str, Any]:
        """Create declined Authorize.net response."""
        return AuthorizeNetFixtures.create_success_response(
            transactionResponse={
                "transId": f"test_trans_{uuid.uuid4().hex[:12]}",
                "responseCode": "2",
                "responseText": "Declined",
                "amount": "10.00"
            },
            **overrides
        )
    
    @staticmethod
    def create_error_response(error_code: str = "E00001", error_text: str = "Error", **overrides) -> Dict[str, Any]:
        """Create error Authorize.net response."""
        base_response = {
            "messages": {
                "resultCode": "Error",
                "message": [{"code": error_code, "text": error_text}]
            }
        }
        base_response.update(overrides)
        return base_response
    
    @staticmethod
    def create_authentication_error_response(**overrides) -> Dict[str, Any]:
        """Create authentication error response."""
        return AuthorizeNetFixtures.create_error_response(
            error_code="E00001",
            error_text="Authentication failed.",
            **overrides
        )
    
    @staticmethod
    def create_network_error_response(**overrides) -> Dict[str, Any]:
        """Create network error response."""
        return AuthorizeNetFixtures.create_error_response(
            error_code="E00002",
            error_text="Network error.",
            **overrides
        )


class TestDataSets:
    """Predefined test data sets for common scenarios."""
    
    @staticmethod
    def get_small_payment_dataset() -> List[Dict[str, Any]]:
        """Get small dataset of payments for basic testing."""
        return [
            PaymentFixtures.create_payment_data(
                customer_id="cust_small_1",
                amount=Decimal("10.00"),
                status=PaymentStatus.COMPLETED
            ),
            PaymentFixtures.create_payment_data(
                customer_id="cust_small_2",
                amount=Decimal("20.00"),
                status=PaymentStatus.PENDING
            ),
            PaymentFixtures.create_payment_data(
                customer_id="cust_small_1",
                amount=Decimal("15.00"),
                status=PaymentStatus.REFUNDED
            )
        ]
    
    @staticmethod
    def get_medium_payment_dataset() -> List[Dict[str, Any]]:
        """Get medium dataset of payments for comprehensive testing."""
        payments = []
        
        # Different customers
        for i in range(5):
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=f"cust_medium_{i}",
                amount=Decimal(f"{10 + i * 10}.00"),
                status=PaymentStatus.COMPLETED
            ))
        
        # Different statuses
        statuses = [PaymentStatus.PENDING, PaymentStatus.FAILED, PaymentStatus.VOIDED]
        for i, status in enumerate(statuses):
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=f"cust_status_{i}",
                amount=Decimal("25.00"),
                status=status
            ))
        
        # Different amounts
        amounts = [Decimal("5.00"), Decimal("50.00"), Decimal("100.00"), Decimal("500.00")]
        for i, amount in enumerate(amounts):
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=f"cust_amount_{i}",
                amount=amount,
                status=PaymentStatus.COMPLETED
            ))
        
        return payments
    
    @staticmethod
    def get_large_payment_dataset() -> List[Dict[str, Any]]:
        """Get large dataset of payments for performance testing."""
        payments = []
        
        # Create 100 payments with varied data
        for i in range(100):
            customer_id = f"cust_large_{i % 10}"  # 10 different customers
            amount = Decimal(f"{5 + (i % 20) * 5}.00")  # Amounts from 5 to 100
            status = list(PaymentStatus)[i % len(PaymentStatus)]  # Rotate through statuses
            
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=customer_id,
                amount=amount,
                status=status,
                description=f"Large dataset payment {i}",
                payment_metadata={"dataset": "large", "index": i}
            ))
        
        return payments
    
    @staticmethod
    def get_edge_case_dataset() -> List[Dict[str, Any]]:
        """Get dataset with edge cases for boundary testing."""
        return [
            # Minimum amount
            PaymentFixtures.create_payment_data(
                amount=Decimal("0.01"),
                description="Minimum amount payment"
            ),
            # Maximum amount
            PaymentFixtures.create_payment_data(
                amount=Decimal("999999.99"),
                description="Maximum amount payment"
            ),
            # Different currencies
            PaymentFixtures.create_payment_data(
                currency="EUR",
                description="Euro payment"
            ),
            PaymentFixtures.create_payment_data(
                currency="GBP",
                description="Pound payment"
            ),
            # Long customer names
            PaymentFixtures.create_payment_data(
                customer_name="A" * 100,
                description="Long customer name"
            ),
            # Special characters in metadata
            PaymentFixtures.create_payment_data(
                payment_metadata={"special": "chars: !@#$%^&*()", "unicode": "测试"},
                description="Special characters payment"
            )
        ]


class PerformanceTestData:
    """Test data specifically designed for performance testing."""
    
    @staticmethod
    def get_bulk_payment_data(count: int) -> List[Dict[str, Any]]:
        """Generate bulk payment data for performance testing."""
        payments = []
        for i in range(count):
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=f"perf_cust_{i % 100}",  # 100 different customers
                amount=Decimal(f"{1 + (i % 50)}.00"),  # Amounts from 1 to 50
                description=f"Performance test payment {i}",
                payment_metadata={"perf_test": True, "index": i}
            ))
        return payments
    
    @staticmethod
    def get_concurrent_payment_data(count: int) -> List[Dict[str, Any]]:
        """Generate payment data for concurrent testing."""
        payments = []
        for i in range(count):
            payments.append(PaymentFixtures.create_payment_data(
                customer_id=f"concurrent_cust_{i}",
                amount=Decimal("10.00"),
                description=f"Concurrent test payment {i}",
                payment_metadata={"concurrent_test": True, "thread_id": i}
            ))
        return payments
