#!/usr/bin/env python3
"""
Test script for advanced payment features.

This script tests the newly implemented advanced payment features including:
- Idempotency handling
- Retry logic with exponential backoff
- Circuit breaker pattern
- Request correlation IDs
- Payment status tracking
- Payment metadata support
- Payment search/filtering
- Payment history tracking
"""
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime

from src.infrastructure.database import get_db_session
from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import PaymentCreateRequest, PaymentRefundRequest, PaymentCancelRequest


async def test_advanced_features():
    """Test advanced payment features."""
    print("🧪 Testing Advanced Payment Features")
    print("=" * 50)
    
    # Get database session
    async for db in get_db_session():
        async with PaymentService(db) as payment_service:
            print(f"✅ Payment service initialized with advanced features: {payment_service.advanced_features is not None}")
            
            # Test 1: Create payment with correlation ID
            print("\n1️⃣ Testing payment creation with correlation ID...")
            correlation_id = f"test_corr_{uuid.uuid4().hex[:8]}"
            
            payment_data = PaymentCreateRequest(
                amount=Decimal("25.00"),
                currency="USD",
                payment_method="credit_card",
                customer_id="test_customer_123",
                customer_email="test@example.com",
                customer_name="Test User",
                description="Test payment for advanced features",
                metadata={"test_feature": "advanced_payment", "source": "test_script"},
                is_test=True
            )
            
            try:
                payment = await payment_service.create_payment(payment_data, correlation_id)
                print(f"✅ Payment created: {payment.id}")
                print(f"   External ID: {payment.external_id}")
                print(f"   Status: {payment.status}")
                print(f"   Amount: {payment.amount} {payment.currency}")
                
                # Test 2: Get payment status history
                print("\n2️⃣ Testing payment status history...")
                status_history = await payment_service.get_payment_status_history(payment.id)
                print(f"✅ Status history retrieved: {len(status_history)} entries")
                for entry in status_history:
                    print(f"   - {entry.get('old_status')} → {entry.get('new_status')}: {entry.get('reason')}")
                
                # Test 3: Get payment metadata
                print("\n3️⃣ Testing payment metadata...")
                metadata = await payment_service.get_payment_metadata(payment.id)
                print(f"✅ Metadata retrieved: {metadata}")
                
                # Test 4: Update payment metadata
                print("\n4️⃣ Testing metadata update...")
                new_metadata = {
                    "updated_at": datetime.utcnow().isoformat(),
                    "test_phase": "advanced_features",
                    "additional_info": "Updated via test script"
                }
                await payment_service.update_payment_metadata(payment.id, new_metadata)
                print("✅ Metadata updated successfully")
                
                # Verify updated metadata
                updated_metadata = await payment_service.get_payment_metadata(payment.id)
                print(f"✅ Updated metadata: {updated_metadata}")
                
                # Test 5: Test refund with correlation ID (simulate captured status first)
                print("\n5️⃣ Testing refund with correlation ID...")
                refund_correlation_id = f"refund_corr_{uuid.uuid4().hex[:8]}"
                
                # First, simulate capturing the payment by updating its status
                from src.core.models.payment import PaymentStatus
                await payment_service.payment_repository.update(payment.id, {
                    "status": PaymentStatus.CAPTURED,
                    "processed_at": datetime.utcnow()
                })
                print("   Payment status updated to CAPTURED for refund test")
                
                refund_data = PaymentRefundRequest(
                    amount=Decimal("10.00"),
                    reason="Test refund for advanced features",
                    metadata={"refund_reason": "testing", "test_phase": "advanced_features"}
                )
                
                refunded_payment = await payment_service.refund_payment(
                    payment.id, refund_data, refund_correlation_id
                )
                print(f"✅ Payment refunded: {refunded_payment.id}")
                print(f"   New status: {refunded_payment.status}")
                print(f"   Refunded amount: {refunded_payment.refunded_amount}")
                
                # Test 6: Test cancellation with correlation ID
                print("\n6️⃣ Testing cancellation with correlation ID...")
                cancel_correlation_id = f"cancel_corr_{uuid.uuid4().hex[:8]}"
                
                # First create a new payment for cancellation test
                cancel_payment_data = PaymentCreateRequest(
                    amount=Decimal("15.00"),
                    currency="USD",
                    payment_method="credit_card",
                    customer_id="test_customer_456",
                    customer_email="cancel@example.com",
                    customer_name="Cancel Test User",
                    description="Test payment for cancellation",
                    metadata={"test_feature": "cancellation", "source": "test_script"},
                    is_test=True
                )
                
                cancel_payment = await payment_service.create_payment(cancel_payment_data, cancel_correlation_id)
                print(f"✅ Test payment for cancellation created: {cancel_payment.id}")
                
                cancel_data = PaymentCancelRequest(
                    reason="Test cancellation for advanced features",
                    metadata={"cancel_reason": "testing", "test_phase": "advanced_features"}
                )
                
                cancelled_payment = await payment_service.cancel_payment(
                    cancel_payment.id, cancel_data, cancel_correlation_id
                )
                print(f"✅ Payment cancelled: {cancelled_payment.id}")
                print(f"   New status: {cancelled_payment.status}")
                
                # Test 7: Test circuit breaker metrics
                print("\n7️⃣ Testing circuit breaker metrics...")
                circuit_metrics = payment_service.get_circuit_breaker_metrics()
                print(f"✅ Circuit breaker metrics: {circuit_metrics}")
                
                # Test 8: Test advanced search
                print("\n8️⃣ Testing advanced search...")
                search_params = {
                    "customer_id": "test_customer_123",
                    "status": "partially_refunded",
                    "page": 1,
                    "per_page": 10
                }
                
                search_results = await payment_service.search_payments_advanced(search_params)
                print(f"✅ Advanced search completed: {len(search_results)} results")
                
                print("\n🎉 All advanced features tests completed successfully!")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                import traceback
                traceback.print_exc()
            
            break  # Exit the async generator


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("\n🔧 Testing Circuit Breaker Pattern")
    print("=" * 40)
    
    from src.core.services.advanced_payment_features import CircuitBreaker, RetryManager, RetryPolicies
    
    # Test circuit breaker
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    
    def failing_function():
        raise Exception("Simulated failure")
    
    def working_function():
        return "Success"
    
    print("Testing circuit breaker with failing function...")
    for i in range(5):
        try:
            result = circuit.call(failing_function)
            print(f"  Attempt {i+1}: {result}")
        except Exception as e:
            print(f"  Attempt {i+1}: Failed - {e}")
            print(f"  Circuit state: {circuit.state.value}")
    
    print(f"\nCircuit metrics: {circuit.get_metrics()}")
    
    # Test retry manager
    print("\nTesting retry manager...")
    retry_manager = RetryManager(RetryPolicies.FAST)
    
    def flaky_function():
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure")
        return "Success after retries"
    
    try:
        result = retry_manager.retry_with_backoff(flaky_function)
        print(f"✅ Retry successful: {result}")
    except Exception as e:
        print(f"❌ Retry failed: {e}")


async def test_idempotency():
    """Test idempotency functionality."""
    print("\n🔄 Testing Idempotency Pattern")
    print("=" * 35)
    
    from src.infrastructure.cache import get_cache_client
    from src.core.services.advanced_payment_features import IdempotencyManager
    
    try:
        cache_client = get_cache_client()
        idempotency_manager = IdempotencyManager(cache_client)
        
        # Test idempotency key generation
        key1 = idempotency_manager.generate_idempotency_key("create_payment", amount="25.00", customer_id="123")
        key2 = idempotency_manager.generate_idempotency_key("create_payment", amount="25.00", customer_id="123")
        key3 = idempotency_manager.generate_idempotency_key("create_payment", amount="30.00", customer_id="123")
        
        print(f"✅ Key 1: {key1}")
        print(f"✅ Key 2: {key2}")
        print(f"✅ Key 3: {key3}")
        print(f"✅ Keys 1 and 2 are identical: {key1 == key2}")
        print(f"✅ Keys 1 and 3 are different: {key1 != key3}")
        
        # Test storing and retrieving idempotency result
        test_result = {"payment_id": "test_123", "status": "created", "amount": "25.00"}
        await idempotency_manager.store_idempotency_result(key1, test_result)
        
        retrieved_result = await idempotency_manager.check_idempotency(key1)
        print(f"✅ Stored and retrieved result: {retrieved_result}")
        
    except Exception as e:
        print(f"❌ Idempotency test failed: {e}")


async def main():
    """Main test function."""
    print("🚀 Starting Advanced Payment Features Tests")
    print("=" * 60)
    
    try:
        # Test individual components
        await test_circuit_breaker()
        await test_idempotency()
        
        # Test integrated features
        await test_advanced_features()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
