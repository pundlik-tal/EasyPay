#!/usr/bin/env python3
"""
Test script for Payment Service
"""
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime

from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest
)
from src.infrastructure.database import AsyncSessionLocal


async def test_payment_service():
    """Test the payment service functionality."""
    print("🧪 Testing Payment Service...")
    
    async with AsyncSessionLocal() as session:
        async with PaymentService(session) as payment_service:
            
            # Test 1: Create Payment
            print("\n1️⃣ Testing payment creation...")
            try:
                payment_data = PaymentCreateRequest(
                    amount=Decimal("10.00"),
                    currency="USD",
                    payment_method="credit_card",
                    customer_id="cust_test_123",
                    customer_email="test@example.com",
                    customer_name="Test Customer",
                    description="Test payment",
                    metadata={"test": True, "order_id": "order_123"}
                )
                
                payment = await payment_service.create_payment(payment_data)
                print(f"✅ Payment created successfully: {payment.id}")
                print(f"   External ID: {payment.external_id}")
                print(f"   Amount: {payment.amount} {payment.currency}")
                print(f"   Status: {payment.status}")
                
            except Exception as e:
                print(f"❌ Payment creation failed: {e}")
                return
            
            # Test 2: Get Payment
            print("\n2️⃣ Testing payment retrieval...")
            try:
                retrieved_payment = await payment_service.get_payment(payment.id)
                print(f"✅ Payment retrieved successfully: {retrieved_payment.id}")
                print(f"   Status: {retrieved_payment.status}")
                
            except Exception as e:
                print(f"❌ Payment retrieval failed: {e}")
                return
            
            # Test 3: Get Payment by External ID
            print("\n3️⃣ Testing payment retrieval by external ID...")
            try:
                retrieved_payment = await payment_service.get_payment_by_external_id(payment.external_id)
                print(f"✅ Payment retrieved by external ID successfully: {retrieved_payment.id}")
                
            except Exception as e:
                print(f"❌ Payment retrieval by external ID failed: {e}")
                return
            
            # Test 4: Update Payment
            print("\n4️⃣ Testing payment update...")
            try:
                update_data = PaymentUpdateRequest(
                    description="Updated test payment description",
                    metadata={"updated": True, "timestamp": datetime.utcnow().isoformat()}
                )
                
                updated_payment = await payment_service.update_payment(payment.id, update_data)
                print(f"✅ Payment updated successfully: {updated_payment.id}")
                print(f"   Description: {updated_payment.description}")
                
            except Exception as e:
                print(f"❌ Payment update failed: {e}")
                return
            
            # Test 5: List Payments
            print("\n5️⃣ Testing payment listing...")
            try:
                payments_list = await payment_service.list_payments(page=1, per_page=10)
                print(f"✅ Payments listed successfully: {len(payments_list['payments'])} payments found")
                print(f"   Total: {payments_list['total']}")
                
            except Exception as e:
                print(f"❌ Payment listing failed: {e}")
                return
            
            # Test 6: Search Payments
            print("\n6️⃣ Testing payment search...")
            try:
                search_results = await payment_service.search_payments("test", page=1, per_page=10)
                print(f"✅ Payment search successful: {len(search_results['payments'])} payments found")
                
            except Exception as e:
                print(f"❌ Payment search failed: {e}")
                return
            
            # Test 7: Get Payment Stats
            print("\n7️⃣ Testing payment statistics...")
            try:
                stats = await payment_service.get_payment_stats()
                print(f"✅ Payment stats retrieved successfully:")
                print(f"   Total count: {stats['total_count']}")
                print(f"   Total amount: {stats['total_amount']}")
                print(f"   Average amount: {stats['average_amount']}")
                
            except Exception as e:
                print(f"❌ Payment stats failed: {e}")
                return
            
            # Test 8: Test Validation Errors
            print("\n8️⃣ Testing validation errors...")
            try:
                # Test invalid amount
                invalid_payment_data = PaymentCreateRequest(
                    amount=Decimal("-10.00"),  # Invalid negative amount
                    currency="USD",
                    payment_method="credit_card"
                )
                await payment_service.create_payment(invalid_payment_data)
                print("❌ Validation should have failed for negative amount")
                
            except Exception as e:
                print(f"✅ Validation correctly caught error: {e}")
            
            print("\n🎉 All Payment Service tests completed!")


if __name__ == "__main__":
    asyncio.run(test_payment_service())
