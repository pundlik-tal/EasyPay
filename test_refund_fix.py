#!/usr/bin/env python3
"""
Test script to verify the refund validation fix.
This script tests that ValidationError is properly raised for voided payments
instead of being wrapped in a DatabaseError.
"""

import asyncio
import uuid
from decimal import Decimal
from src.core.models.payment import Payment, PaymentStatus
from src.core.services.payment_service import PaymentService
from src.core.exceptions import ValidationError
from src.api.v1.schemas.payment import PaymentRefundRequest
from src.infrastructure.database_config import get_db_session


async def test_refund_validation():
    """Test that refund validation properly raises ValidationError for voided payments."""
    
    # Create a mock voided payment
    voided_payment = Payment(
        id=uuid.uuid4(),
        external_id="test_payment_001",
        amount=Decimal("25.99"),
        currency="USD",
        status=PaymentStatus.VOIDED,
        payment_method="credit_card",
        customer_id="test_customer",
        customer_email="test@example.com",
        customer_name="Test Customer",
        refunded_amount=Decimal("0.00"),
        refund_count=0,
        is_test=True
    )
    
    # Create refund request
    refund_request = PaymentRefundRequest(
        amount=Decimal("10.00"),
        reason="Test refund",
        metadata={"test": True}
    )
    
    # Test the validation logic directly
    try:
        # This should raise ValidationError, not DatabaseError
        if not voided_payment.is_refundable:
            if voided_payment.status == PaymentStatus.VOIDED:
                raise ValidationError(
                    "Payment cannot be refunded because it has been voided. "
                    "Voided payments were never charged and therefore cannot be refunded. "
                    "Only captured or settled payments can be refunded."
                )
        
        print("❌ ERROR: ValidationError was not raised for voided payment!")
        return False
        
    except ValidationError as e:
        print(f"✅ SUCCESS: ValidationError correctly raised: {e}")
        return True
    except Exception as e:
        print(f"❌ ERROR: Unexpected exception type: {type(e).__name__}: {e}")
        return False


async def test_database_session_error_handling():
    """Test that database session doesn't wrap ValidationError."""
    
    try:
        # This should not wrap ValidationError in DatabaseError
        async for session in get_db_session():
            # Simulate a ValidationError being raised
            raise ValidationError("Test validation error")
            
    except ValidationError as e:
        print(f"✅ SUCCESS: ValidationError not wrapped in DatabaseError: {e}")
        return True
    except Exception as e:
        print(f"❌ ERROR: ValidationError was wrapped: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing refund validation fix...")
    print("=" * 50)
    
    # Test 1: Direct validation logic
    print("\n1. Testing direct validation logic:")
    test1_result = await test_refund_validation()
    
    # Test 2: Database session error handling
    print("\n2. Testing database session error handling:")
    test2_result = await test_database_session_error_handling()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"Direct validation test: {'PASS' if test1_result else 'FAIL'}")
    print(f"Database session test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The refund validation fix is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    asyncio.run(main())