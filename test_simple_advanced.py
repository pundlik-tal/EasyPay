#!/usr/bin/env python3
"""
Simple test for advanced payment features.
"""
import asyncio
from src.core.services.advanced_payment_features import CircuitBreaker, RetryManager, RetryPolicies

async def test_simple():
    """Test basic functionality."""
    print("🧪 Testing Advanced Payment Features (Simple)")
    print("=" * 50)
    
    # Test circuit breaker
    print("\n1️⃣ Testing Circuit Breaker...")
    circuit = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    def failing_func():
        raise Exception("Test failure")
    
    def working_func():
        return "Success"
    
    # Test failing function
    for i in range(4):
        try:
            result = circuit.call(failing_func)
            print(f"  Attempt {i+1}: {result}")
        except Exception as e:
            print(f"  Attempt {i+1}: Failed - {e}")
            print(f"  Circuit state: {circuit.state.value}")
    
    print(f"Circuit metrics: {circuit.get_metrics()}")
    
    # Test retry manager
    print("\n2️⃣ Testing Retry Manager...")
    retry_manager = RetryManager(RetryPolicies.FAST)
    
    def flaky_func():
        import random
        if random.random() < 0.8:  # 80% chance of failure
            raise Exception("Random failure")
        return "Success after retries"
    
    try:
        result = retry_manager.retry_with_backoff(flaky_func)
        print(f"✅ Retry successful: {result}")
    except Exception as e:
        print(f"❌ Retry failed: {e}")
    
    print("\n✅ Basic tests completed!")

if __name__ == "__main__":
    asyncio.run(test_simple())
