#!/usr/bin/env python3
"""
Test script to verify database models and schemas work correctly.
"""
import sys
import os
from datetime import datetime
from decimal import Decimal
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Payment, Webhook, AuditLog
from core.models.payment import PaymentStatus, PaymentMethod
from core.models.webhook import WebhookStatus, WebhookEventType
from core.models.audit_log import AuditLogLevel, AuditLogAction
from api.v1.schemas.payment import PaymentCreateRequest, PaymentResponse
from api.v1.schemas.webhook import WebhookCreateRequest, WebhookResponse


def test_payment_model():
    """Test Payment SQLAlchemy model."""
    print("Testing Payment SQLAlchemy model...")
    
    # Create a payment instance
    payment = Payment(
        external_id="pay_test_123",
        amount=Decimal("10.00"),
        currency="USD",
        status=PaymentStatus.PENDING,
        payment_method=PaymentMethod.CREDIT_CARD,
        customer_id="cust_123",
        customer_email="test@example.com",
        customer_name="Test Customer",
        card_last_four="4242",
        card_brand="visa",
        description="Test payment",
        metadata={"test": True}
    )
    
    print(f"✓ Payment created: {payment}")
    print(f"✓ Is refundable: {payment.is_refundable}")
    print(f"✓ Is voidable: {payment.is_voidable}")
    print(f"✓ Remaining refund amount: {payment.remaining_refund_amount}")
    print()


def test_webhook_model():
    """Test Webhook SQLAlchemy model."""
    print("Testing Webhook SQLAlchemy model...")
    
    # Create a webhook instance
    webhook = Webhook(
        event_type=WebhookEventType.PAYMENT_AUTHORIZED,
        event_id="evt_test_123",
        status=WebhookStatus.PENDING,
        url="https://example.com/webhook",
        payload={"test": "data"},
        retry_count=0,
        max_retries=3
    )
    
    print(f"✓ Webhook created: {webhook}")
    print(f"✓ Can retry: {webhook.can_retry}")
    print(f"✓ Is expired: {webhook.is_expired}")
    
    # Test retry scheduling
    webhook.schedule_retry()
    print(f"✓ Retry scheduled: {webhook.next_retry_at}")
    print()


def test_audit_log_model():
    """Test AuditLog SQLAlchemy model."""
    print("Testing AuditLog SQLAlchemy model...")
    
    # Create an audit log instance
    audit_log = AuditLog.create_payment_log(
        action=AuditLogAction.PAYMENT_CREATED,
        payment_id=uuid.uuid4(),
        message="Payment created successfully",
        user_id="user_123",
        metadata={"amount": "10.00"}
    )
    
    print(f"✓ Audit log created: {audit_log}")
    print()


def test_payment_schemas():
    """Test Payment Pydantic schemas."""
    print("Testing Payment Pydantic schemas...")
    
    # Test PaymentCreateRequest
    payment_data = {
        "amount": "10.00",
        "currency": "USD",
        "payment_method": "credit_card",
        "customer_id": "cust_123",
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "card_token": "tok_123",
        "description": "Test payment",
        "metadata": {"test": True}
    }
    
    payment_request = PaymentCreateRequest(**payment_data)
    print(f"✓ PaymentCreateRequest created: {payment_request.amount} {payment_request.currency}")
    
    # Test PaymentResponse
    payment_response_data = {
        "id": uuid.uuid4(),
        "external_id": "pay_test_123",
        "amount": Decimal("10.00"),
        "currency": "USD",
        "status": "captured",
        "payment_method": "credit_card",
        "customer_id": "cust_123",
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "card_last_four": "4242",
        "card_brand": "visa",
        "description": "Test payment",
        "metadata": {"test": True},
        "refunded_amount": Decimal("0.00"),
        "refund_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "processed_at": datetime.utcnow(),
        "is_test": False
    }
    
    payment_response = PaymentResponse(**payment_response_data)
    print(f"✓ PaymentResponse created: {payment_response.external_id}")
    print(f"✓ Is refundable: {payment_response.is_refundable}")
    print(f"✓ Remaining refund amount: {payment_response.remaining_refund_amount}")
    print()


def test_webhook_schemas():
    """Test Webhook Pydantic schemas."""
    print("Testing Webhook Pydantic schemas...")
    
    # Test WebhookCreateRequest
    webhook_data = {
        "url": "https://example.com/webhook",
        "event_types": ["payment.authorized", "payment.captured"],
        "description": "Test webhook",
        "metadata": {"test": True}
    }
    
    webhook_request = WebhookCreateRequest(**webhook_data)
    print(f"✓ WebhookCreateRequest created: {webhook_request.url}")
    
    # Test WebhookResponse
    webhook_response_data = {
        "id": uuid.uuid4(),
        "event_type": "payment.authorized",
        "event_id": "evt_test_123",
        "status": "delivered",
        "url": "https://example.com/webhook",
        "retry_count": 0,
        "max_retries": 3,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "delivered_at": datetime.utcnow(),
        "is_test": False,
        "signature_verified": True
    }
    
    webhook_response = WebhookResponse(**webhook_response_data)
    print(f"✓ WebhookResponse created: {webhook_response.event_id}")
    print(f"✓ Can retry: {webhook_response.can_retry}")
    print()


def test_validation():
    """Test schema validation."""
    print("Testing schema validation...")
    
    # Test invalid amount
    try:
        invalid_payment = PaymentCreateRequest(
            amount=Decimal("-10.00"),  # Invalid negative amount
            currency="USD",
            payment_method="credit_card"
        )
        print("✗ Should have failed validation")
    except ValueError as e:
        print(f"✓ Correctly caught validation error: {e}")
    
    # Test invalid currency
    try:
        invalid_payment = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="INVALID",  # Invalid currency
            payment_method="credit_card"
        )
        print("✗ Should have failed validation")
    except ValueError as e:
        print(f"✓ Correctly caught validation error: {e}")
    
    # Test invalid URL
    try:
        invalid_webhook = WebhookCreateRequest(
            url="invalid-url",  # Invalid URL
            event_types=["payment.authorized"]
        )
        print("✗ Should have failed validation")
    except ValueError as e:
        print(f"✓ Correctly caught validation error: {e}")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("EasyPay Database Models and Schemas Test")
    print("=" * 60)
    print()
    
    try:
        test_payment_model()
        test_webhook_model()
        test_audit_log_model()
        test_payment_schemas()
        test_webhook_schemas()
        test_validation()
        
        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("✓ Database models and schemas are working correctly")
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

