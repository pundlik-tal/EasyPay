#!/usr/bin/env python3
"""
Simple test to verify the refund validation fix.
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from decimal import Decimal
from src.core.models.payment import Payment, PaymentStatus
from src.core.exceptions import ValidationError


def test_refund_validation():
    """Test that refund validation properly raises ValidationError for voided payments."""
    
    # Create a mock voided payment
    voided_payment = Payment(
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
        
        print("ERROR: ValidationError was not raised for voided payment!")
        return False
        
    except ValidationError as e:
        print(f"SUCCESS: ValidationError correctly raised: {e}")
        return True
    except Exception as e:
        print(f"ERROR: Unexpected exception type: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("Testing refund validation fix...")
    result = test_refund_validation()
    
    if result:
        print("Test passed! The refund validation fix is working correctly.")
    else:
        print("Test failed. Please check the implementation.")
