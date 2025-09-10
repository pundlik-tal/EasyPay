#!/usr/bin/env python3
"""
Test script to debug payment creation issue
"""
import asyncio
import uuid
from decimal import Decimal

from src.infrastructure.database import get_db_session
from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import PaymentCreateRequest

async def test_payment_creation():
    """Test payment creation to debug the issue."""
    try:
        # Create a simple payment request
        payment_data = PaymentCreateRequest(
            amount=Decimal("10.00"),
            currency="USD",
            payment_method="credit_card",
            description="Test payment",
            is_test=True
        )
        
        print(f"Payment data: {payment_data}")
        
        # Get database session
        async for session in get_db_session():
            async with PaymentService(session) as payment_service:
                print("Creating payment...")
                payment = await payment_service.create_payment(payment_data)
                print(f"Payment created successfully: {payment.id}")
                break
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_payment_creation())
