"""
EasyPay Payment Gateway - Comprehensive Chaos Engineering Tests

This module contains comprehensive chaos engineering tests for system resilience
including failure injection, network issues, and resource exhaustion.
"""

import pytest
import uuid
import asyncio
import time
import random
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.infrastructure.circuit_breaker_service import CircuitBreakerService
from src.infrastructure.error_recovery import ErrorRecoveryService


class TestFailureInjection:
    """Chaos tests for failure injection scenarios."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Chaos Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_database_connection_failure(self, authenticated_client):
        """Test system behavior when database connection fails."""
        print("\nTesting database connection failure...")
        
        # Simulate database connection failure
        with patch('src.infrastructure.database.get_db_session') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # Test payment creation with database failure
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_db_123",
                "customer_email": "chaosdb@example.com",
                "customer_name": "Chaos DB Test Customer",
                "card_token": "tok_chaos_db_123",
                "description": "Chaos DB test payment",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # System should handle database failure gracefully
            assert response.status_code in [500, 503], "Should return server error for database failure"
            
            error_data = response.json()
            assert "detail" in error_data
            # Should not expose internal database errors
            assert "database" not in str(error_data).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_external_service_failure(self, authenticated_client):
        """Test system behavior when external services fail."""
        print("\nTesting external service failure...")
        
        # Simulate Authorize.net service failure
        with patch('src.integrations.authorize_net.client.AuthorizeNetClient.charge_credit_card') as mock_charge:
            mock_charge.side_effect = Exception("External service unavailable")
            
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_ext_123",
                "customer_email": "chaosext@example.com",
                "customer_name": "Chaos External Test Customer",
                "card_token": "tok_chaos_ext_123",
                "description": "Chaos external test payment",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # System should handle external service failure gracefully
            assert response.status_code in [500, 503], "Should return server error for external service failure"
            
            error_data = response.json()
            assert "detail" in error_data
            # Should not expose internal service errors
            assert "authorize" not in str(error_data).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_cache_failure(self, authenticated_client):
        """Test system behavior when cache fails."""
        print("\nTesting cache failure...")
        
        # Simulate cache failure
        with patch('src.infrastructure.cache.cache_strategies.CacheStrategy.get') as mock_cache_get:
            mock_cache_get.side_effect = Exception("Cache service unavailable")
            
            # Test payment retrieval with cache failure
            # First create a payment
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_cache_123",
                "customer_email": "chaoscache@example.com",
                "customer_name": "Chaos Cache Test Customer",
                "card_token": "tok_chaos_cache_123",
                "description": "Chaos cache test payment",
                "is_test": True
            }
            
            create_response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            assert create_response.status_code == 201
            
            payment_id = create_response.json()["data"]["id"]
            
            # Now test retrieval with cache failure
            get_response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
            
            # System should fallback to database when cache fails
            assert get_response.status_code == 200, "Should fallback to database when cache fails"
            
            payment = get_response.json()["data"]
            assert payment["id"] == payment_id
            assert payment["amount"] == "25.00"


class TestNetworkChaos:
    """Chaos tests for network-related issues."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Network Chaos Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_network_timeout(self, authenticated_client):
        """Test system behavior with network timeouts."""
        print("\nTesting network timeout...")
        
        # Simulate network timeout
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_timeout_123",
                "customer_email": "chaostimeout@example.com",
                "customer_name": "Chaos Timeout Test Customer",
                "card_token": "tok_chaos_timeout_123",
                "description": "Chaos timeout test payment",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            
            # System should handle timeout gracefully
            assert response.status_code in [500, 503, 504], "Should return timeout error"
            
            error_data = response.json()
            assert "detail" in error_data
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_network_latency(self, authenticated_client):
        """Test system behavior with high network latency."""
        print("\nTesting network latency...")
        
        # Simulate high latency
        async def slow_request(*args, **kwargs):
            await asyncio.sleep(5)  # 5 second delay
            return MagicMock(status_code=200, json=lambda: {"status": "success"})
        
        with patch('httpx.AsyncClient.post', side_effect=slow_request):
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_latency_123",
                "customer_email": "chaoslatency@example.com",
                "customer_name": "Chaos Latency Test Customer",
                "card_token": "tok_chaos_latency_123",
                "description": "Chaos latency test payment",
                "is_test": True
            }
            
            start_time = time.time()
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            end_time = time.time()
            
            # Should handle latency gracefully
            assert response.status_code in [200, 201, 504], "Should handle latency"
            
            # Response time should be reasonable despite external latency
            response_time = end_time - start_time
            assert response_time < 10.0, f"Response time {response_time:.2f}s too high"


class TestResourceExhaustion:
    """Chaos tests for resource exhaustion scenarios."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Resource Chaos Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_memory_pressure(self, authenticated_client):
        """Test system behavior under memory pressure."""
        print("\nTesting memory pressure...")
        
        # Simulate memory pressure by creating large objects
        large_data = "x" * (10 * 1024 * 1024)  # 10MB string
        
        payment_data = {
            "amount": "25.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_chaos_memory_123",
            "customer_email": "chaosmemory@example.com",
            "customer_name": "Chaos Memory Test Customer",
            "card_token": "tok_chaos_memory_123",
            "description": f"Chaos memory test payment with large data: {large_data[:100]}...",
            "metadata": {"large_data": large_data},
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        
        # System should handle large data gracefully
        if response.status_code == 201:
            # If accepted, verify it was processed correctly
            payment = response.json()["data"]
            assert payment["amount"] == "25.00"
            # Large data should be truncated or handled appropriately
            assert len(payment.get("description", "")) < len(payment_data["description"])
        else:
            # Should reject overly large requests
            assert response.status_code in [400, 413, 422], "Should reject large requests"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_concurrent_resource_contention(self, authenticated_client):
        """Test system behavior under concurrent resource contention."""
        print("\nTesting concurrent resource contention...")
        
        # Create many concurrent requests to cause resource contention
        async def create_payment(request_id: int):
            payment_data = {
                "amount": f"{10 + (request_id % 50)}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_chaos_concurrent_{request_id}",
                "customer_email": f"chaosconcurrent{request_id}@example.com",
                "customer_name": f"Chaos Concurrent Test Customer {request_id}",
                "card_token": f"tok_chaos_concurrent_{request_id}",
                "description": f"Chaos concurrent test payment {request_id}",
                "is_test": True
            }
            
            try:
                response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                return {
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "request_id": request_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "request_id": request_id
                }
        
        # Create 100 concurrent requests
        tasks = [create_payment(i) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_requests = len([r for r in results if not isinstance(r, Exception) and r["success"]])
        failed_requests = len([r for r in results if isinstance(r, Exception) or not r["success"]])
        
        success_rate = successful_requests / len(results)
        
        print(f"  Concurrent Resource Contention Results:")
        print(f"    Total Requests: {len(results)}")
        print(f"    Successful: {successful_requests}")
        print(f"    Failed: {failed_requests}")
        print(f"    Success Rate: {success_rate:.2%}")
        
        # System should handle resource contention gracefully
        assert success_rate > 0.5, f"Success rate {success_rate:.2%} too low under resource contention"


class TestCircuitBreakerChaos:
    """Chaos tests for circuit breaker behavior."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance."""
        return CircuitBreakerService(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_circuit_breaker_failure_scenarios(self, circuit_breaker):
        """Test circuit breaker behavior under various failure scenarios."""
        print("\nTesting circuit breaker failure scenarios...")
        
        # Test circuit breaker state transitions
        async def failing_operation():
            raise Exception("Simulated failure")
        
        async def successful_operation():
            return "success"
        
        # Initially closed
        assert circuit_breaker.state == "closed"
        
        # Simulate failures to open circuit
        for i in range(5):
            try:
                await circuit_breaker.call_async(failing_operation)
            except Exception:
                pass
        
        # Circuit should be open
        assert circuit_breaker.state == "open"
        
        # Test that circuit breaker blocks requests when open
        try:
            await circuit_breaker.call_async(successful_operation)
            assert False, "Circuit breaker should block requests when open"
        except Exception as e:
            assert "circuit breaker is open" in str(e).lower()
        
        # Simulate recovery timeout
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=61)
        
        # Circuit should be half-open
        assert circuit_breaker.state == "half-open"
        
        # Test successful operation in half-open state
        result = await circuit_breaker.call_async(successful_operation)
        assert result == "success"
        
        # Circuit should be closed again
        assert circuit_breaker.state == "closed"


class TestErrorRecoveryChaos:
    """Chaos tests for error recovery mechanisms."""
    
    @pytest.fixture
    def error_recovery(self):
        """Create error recovery instance."""
        return ErrorRecoveryService()
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_error_recovery_strategies(self, error_recovery):
        """Test error recovery strategies under chaos conditions."""
        print("\nTesting error recovery strategies...")
        
        # Test retry strategy with intermittent failures
        retry_count = 0
        
        async def intermittent_failing_operation():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise Exception(f"Temporary failure {retry_count}")
            return f"success after {retry_count} attempts"
        
        result = await error_recovery.execute_with_retry(
            intermittent_failing_operation,
            max_retries=5,
            retry_delay=0.1
        )
        
        assert result == "success after 3 attempts"
        assert retry_count == 3
        
        # Test circuit breaker strategy
        circuit_breaker = CircuitBreakerService(
            failure_threshold=3,
            recovery_timeout=10,
            expected_exception=Exception
        )
        
        async def operation_with_circuit_breaker():
            return "success with circuit breaker"
        
        result = await error_recovery.execute_with_circuit_breaker(
            operation_with_circuit_breaker,
            circuit_breaker
        )
        
        assert result == "success with circuit breaker"


class TestSystemResilience:
    """Chaos tests for overall system resilience."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "System Resilience Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_system_recovery_after_failures(self, authenticated_client):
        """Test system recovery after various failure scenarios."""
        print("\nTesting system recovery after failures...")
        
        # Test 1: Database failure recovery
        with patch('src.infrastructure.database.get_db_session') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            payment_data = {
                "amount": "25.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_chaos_recovery_123",
                "customer_email": "chaosrecovery@example.com",
                "customer_name": "Chaos Recovery Test Customer",
                "card_token": "tok_chaos_recovery_123",
                "description": "Chaos recovery test payment",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            assert response.status_code in [500, 503]
        
        # Test 2: System should recover after database comes back
        # (In real scenario, database would be restored)
        
        # Test normal operation after recovery
        payment_data = {
            "amount": "30.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_chaos_recovery_456",
            "customer_email": "chaosrecovery2@example.com",
            "customer_name": "Chaos Recovery Test Customer 2",
            "card_token": "tok_chaos_recovery_456",
            "description": "Chaos recovery test payment 2",
            "is_test": True
        }
        
        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert response.status_code == 201
        
        payment = response.json()["data"]
        assert payment["amount"] == "30.00"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_graceful_degradation(self, authenticated_client):
        """Test system graceful degradation under stress."""
        print("\nTesting graceful degradation...")
        
        # Simulate high load with limited resources
        async def stress_operation(request_id: int):
            # Add random delay to simulate resource contention
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            payment_data = {
                "amount": f"{10 + (request_id % 50)}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_chaos_stress_{request_id}",
                "customer_email": f"chaosstress{request_id}@example.com",
                "customer_name": f"Chaos Stress Test Customer {request_id}",
                "card_token": f"tok_chaos_stress_{request_id}",
                "description": f"Chaos stress test payment {request_id}",
                "is_test": True
            }
            
            try:
                response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                return {
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "request_id": request_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "request_id": request_id
                }
        
        # Create stress load
        tasks = [stress_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze graceful degradation
        successful_requests = len([r for r in results if not isinstance(r, Exception) and r["success"]])
        failed_requests = len([r for r in results if isinstance(r, Exception) or not r["success"]])
        
        success_rate = successful_requests / len(results)
        
        print(f"  Graceful Degradation Results:")
        print(f"    Total Requests: {len(results)}")
        print(f"    Successful: {successful_requests}")
        print(f"    Failed: {failed_requests}")
        print(f"    Success Rate: {success_rate:.2%}")
        
        # System should maintain reasonable performance under stress
        assert success_rate > 0.7, f"Success rate {success_rate:.2%} too low under stress"
        
        # Failed requests should be handled gracefully
        failed_status_codes = [r.get("status_code") for r in results if not isinstance(r, Exception) and not r["success"]]
        if failed_status_codes:
            # Should return proper HTTP error codes, not crash
            assert all(code in [400, 401, 403, 422, 429, 500, 503] for code in failed_status_codes), "Should return proper error codes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
