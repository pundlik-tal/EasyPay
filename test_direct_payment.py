#!/usr/bin/env python3
"""
Test script to debug direct payment creation
"""
import asyncio
import uuid
from decimal import Decimal

from src.infrastructure.database import get_db_session
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod

async def test_direct_payment_creation():
    """Test direct payment creation to debug the issue."""
    try:
        # Create a simple payment object
        payment_data = {
            "external_id": f"pay_{uuid.uuid4().hex[:12]}",
            "amount": Decimal("10.00"),
            "currency": "USD",
            "status": PaymentStatus.PENDING,
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "is_test": True,
            "is_live": False
        }
        
        print(f"Payment data: {payment_data}")
        
        # Get database session
        async for session in get_db_session():
            try:
                print("Creating payment object...")
                payment = Payment(**payment_data)
                print(f"Payment object created: {payment}")
                
                print("Adding to session...")
                session.add(payment)
                
                print("Committing...")
                await session.commit()
                
                print("Refreshing...")
                await session.refresh(payment)
                
                print(f"Payment created successfully: {payment.id}")
                break
                
            except Exception as e:
                print(f"Database error: {e}")
                await session.rollback()
                raise
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_payment_creation())
