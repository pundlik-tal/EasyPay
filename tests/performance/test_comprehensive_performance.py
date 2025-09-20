"""
EasyPay Payment Gateway - Comprehensive Performance Tests

This module contains comprehensive performance tests for all system components
including load testing, stress testing, and performance benchmarking.
"""

import pytest
import uuid
import asyncio
import time
import statistics
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Tuple
import concurrent.futures
import threading

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.core.services.webhook_service import WebhookService
from src.core.repositories.payment_repository import PaymentRepository
from src.core.repositories.cached_payment_repository import CachedPaymentRepository
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.webhook import Webhook, WebhookStatus
from src.infrastructure.cache.cache_strategies import CacheStrategy
from src.infrastructure.circuit_breaker_service import CircuitBreakerService
from src.infrastructure.connection_pool import ConnectionPoolManager
from src.infrastructure.async_processor import AsyncTaskProcessor


class TestPaymentServicePerformance:
    """Performance tests for PaymentService."""
    
    @pytest.fixture
    async def payment_service(self, test_db_session):
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_payment_creation_performance(self, payment_service):
        """Test payment creation performance with various loads."""
        from src.api.v1.schemas.payment import PaymentCreateRequest
        
        # Test different batch sizes
        batch_sizes = [10, 50, 100, 200]
        results = {}
        
        for batch_size in batch_sizes:
            # Create payment requests
            payment_requests = []
            for i in range(batch_size):
                payment_data = {
                    "amount": Decimal(f"{10 + (i % 10)}.00"),
                    "currency": "USD",
                    "payment_method": PaymentMethod.CREDIT_CARD.value,
                    "customer_id": f"cust_perf_{i}",
                    "customer_email": f"perf{i}@example.com",
                    "customer_name": f"Performance Test Customer {i}",
                    "card_token": f"tok_perf_{i}",
                    "description": f"Performance test payment {i}",
                    "is_test": True
                }
                payment_requests.append(PaymentCreateRequest(**payment_data))
            
            # Measure creation time
            start_time = time.time()
            
            tasks = []
            for request in payment_requests:
                task = payment_service.create_payment(request)
                tasks.append(task)
            
            results_batch = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Calculate metrics
            total_time = end_time - start_time
            avg_time_per_payment = total_time / batch_size
            payments_per_second = batch_size / total_time
            
            results[batch_size] = {
                "total_time": total_time,
                "avg_time_per_payment": avg_time_per_payment,
                "payments_per_second": payments_per_second,
                "successful_payments": len([r for r in results_batch if r is not None])
            }
            
            # Verify all payments were created
            assert len(results_batch) == batch_size
            assert all(payment is not None for payment in results_batch)
            assert all(payment.status == PaymentStatus.PENDING for payment in results_batch)
        
        # Print performance results
        print("\nPayment Creation Performance Results:")
        print("=" * 60)
        for batch_size, metrics in results.items():
            print(f"Batch Size: {batch_size}")
            print(f"  Total Time: {metrics['total_time']:.3f}s")
            print(f"  Avg Time per Payment: {metrics['avg_time_per_payment']:.3f}s")
            print(f"  Payments per Second: {metrics['payments_per_second']:.2f}")
            print(f"  Success Rate: {metrics['successful_payments']}/{batch_size}")
            print()
        
        # Performance assertions
        assert results[10]["payments_per_second"] > 10  # At least 10 payments/second
        assert results[50]["payments_per_second"] > 5   # At least 5 payments/second for larger batches
        assert results[100]["payments_per_second"] > 3  # At least 3 payments/second for large batches
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_payment_search_performance(self, payment_service, test_db_session):
        """Test payment search performance with large datasets."""
        # Create large dataset
        batch_size = 1000
        payments = []
        
        print(f"Creating {batch_size} test payments for search performance test...")
        
        for i in range(batch_size):
            payment_data = {
                "amount": Decimal(f"{10 + (i % 50)}.00"),
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": f"cust_search_{i % 100}",  # 100 unique customers
                "customer_email": f"search{i % 100}@example.com",
                "customer_name": f"Search Test Customer {i % 100}",
                "card_token": f"tok_search_{i}",
                "description": f"Search test payment {i}",
                "status": PaymentStatus.PENDING if i % 2 == 0 else PaymentStatus.AUTHORIZED,
                "external_id": f"pay_search_{uuid.uuid4().hex[:12]}",
                "is_test": True
            }
            payment = Payment(**payment_data)
            test_db_session.add(payment)
            payments.append(payment)
        
        await test_db_session.commit()
        print(f"Created {len(payments)} test payments")
        
        # Test different search scenarios
        search_tests = [
            {
                "name": "Search by customer ID",
                "params": {"customer_id": "cust_search_1"},
                "expected_min_results": 1
            },
            {
                "name": "Search by amount range",
                "params": {"min_amount": Decimal("20.00"), "max_amount": Decimal("30.00")},
                "expected_min_results": 100  # 20% of payments in this range
            },
            {
                "name": "Search by status",
                "params": {"status": PaymentStatus.PENDING},
                "expected_min_results": 400  # 50% of payments
            },
            {
                "name": "Search with multiple filters",
                "params": {
                    "customer_id": "cust_search_5",
                    "status": PaymentStatus.AUTHORIZED,
                    "min_amount": Decimal("15.00")
                },
                "expected_min_results": 1
            }
        ]
        
        results = {}
        
        for test in search_tests:
            # Measure search time
            start_time = time.time()
            
            search_results = await payment_service.search_payments(**test["params"])
            
            end_time = time.time()
            
            search_time = end_time - start_time
            result_count = len(search_results)
            
            results[test["name"]] = {
                "search_time": search_time,
                "result_count": result_count,
                "results_per_second": result_count / search_time if search_time > 0 else 0
            }
            
            # Verify results
            assert result_count >= test["expected_min_results"], f"Expected at least {test['expected_min_results']} results for {test['name']}"
            
            print(f"{test['name']}: {search_time:.3f}s, {result_count} results, {result_count/search_time:.2f} results/sec")
        
        # Performance assertions
        assert results["Search by customer ID"]["search_time"] < 1.0  # Should be fast for indexed searches
        assert results["Search by amount range"]["search_time"] < 2.0  # Should be reasonable for range searches
        assert results["Search by status"]["search_time"] < 3.0  # Should handle large result sets
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_payment_operations_performance(self, payment_service, test_db_session):
        """Test concurrent payment operations performance."""
        # Create test payment
        payment_data = {
            "amount": Decimal("100.00"),
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_concurrent_123",
            "customer_email": "concurrent@example.com",
            "customer_name": "Concurrent Test Customer",
            "card_token": "tok_concurrent_123",
            "description": "Concurrent test payment",
            "is_test": True
        }
        
        from src.api.v1.schemas.payment import PaymentCreateRequest
        payment = await payment_service.create_payment(PaymentCreateRequest(**payment_data))
        
        # Test concurrent status updates
        async def update_payment_status(status):
            start_time = time.time()
            await payment_service.update_payment_status(payment.id, status)
            end_time = time.time()
            return {
                "status": status,
                "update_time": end_time - start_time,
                "success": True
            }
        
        # Test different concurrency levels
        concurrency_levels = [5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"Testing concurrent operations with {concurrency} threads...")
            
            # Create concurrent tasks
            tasks = []
            for i in range(concurrency):
                status = PaymentStatus.AUTHORIZED if i % 2 == 0 else PaymentStatus.CAPTURED
                task = update_payment_status(status)
                tasks.append(task)
            
            # Measure concurrent execution time
            start_time = time.time()
            
            try:
                results_batch = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                total_time = end_time - start_time
                successful_updates = len([r for r in results_batch if not isinstance(r, Exception)])
                failed_updates = len([r for r in results_batch if isinstance(r, Exception)])
                
                results[concurrency] = {
                    "total_time": total_time,
                    "successful_updates": successful_updates,
                    "failed_updates": failed_updates,
                    "updates_per_second": concurrency / total_time,
                    "success_rate": successful_updates / concurrency
                }
                
                print(f"  Total Time: {total_time:.3f}s")
                print(f"  Successful: {successful_updates}/{concurrency}")
                print(f"  Failed: {failed_updates}")
                print(f"  Updates/sec: {concurrency/total_time:.2f}")
                print(f"  Success Rate: {successful_updates/concurrency:.2%}")
                
            except Exception as e:
                print(f"  Error: {e}")
                results[concurrency] = {
                    "total_time": 0,
                    "successful_updates": 0,
                    "failed_updates": concurrency,
                    "updates_per_second": 0,
                    "success_rate": 0
                }
        
        # Performance assertions
        assert results[5]["success_rate"] > 0.8   # At least 80% success rate for low concurrency
        assert results[10]["success_rate"] > 0.7  # At least 70% success rate for medium concurrency
        assert results[20]["success_rate"] > 0.5  # At least 50% success rate for high concurrency


class TestCachePerformance:
    """Performance tests for cache system."""
    
    @pytest.fixture
    async def cache_strategy(self):
        """Create cache strategy instance."""
        return CacheStrategy()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_cache_read_write_performance(self, cache_strategy):
        """Test cache read/write performance."""
        # Test different data sizes
        data_sizes = [100, 1000, 10000]
        results = {}
        
        for size in data_sizes:
            print(f"Testing cache performance with {size} items...")
            
            # Test write performance
            write_start_time = time.time()
            
            write_tasks = []
            for i in range(size):
                key = f"perf_key_{i}"
                value = f"perf_value_{i}" * 10  # 10x the key size for realistic data
                task = cache_strategy.set(key, value, ttl=300)
                write_tasks.append(task)
            
            await asyncio.gather(*write_tasks)
            write_end_time = time.time()
            
            write_time = write_end_time - write_start_time
            writes_per_second = size / write_time
            
            # Test read performance
            read_start_time = time.time()
            
            read_tasks = []
            for i in range(size):
                key = f"perf_key_{i}"
                task = cache_strategy.get(key)
                read_tasks.append(task)
            
            read_results = await asyncio.gather(*read_tasks)
            read_end_time = time.time()
            
            read_time = read_end_time - read_start_time
            reads_per_second = size / read_time
            
            # Calculate hit rate
            hit_count = len([r for r in read_results if r is not None])
            hit_rate = hit_count / size
            
            results[size] = {
                "write_time": write_time,
                "writes_per_second": writes_per_second,
                "read_time": read_time,
                "reads_per_second": reads_per_second,
                "hit_rate": hit_rate
            }
            
            print(f"  Write Time: {write_time:.3f}s ({writes_per_second:.0f} writes/sec)")
            print(f"  Read Time: {read_time:.3f}s ({reads_per_second:.0f} reads/sec)")
            print(f"  Hit Rate: {hit_rate:.2%}")
        
        # Performance assertions
        assert results[100]["writes_per_second"] > 1000   # At least 1000 writes/sec
        assert results[100]["reads_per_second"] > 2000     # At least 2000 reads/sec
        assert results[1000]["writes_per_second"] > 500    # At least 500 writes/sec for larger datasets
        assert results[1000]["reads_per_second"] > 1000    # At least 1000 reads/sec for larger datasets
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_cache_memory_usage_performance(self, cache_strategy):
        """Test cache memory usage performance."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test memory usage with different cache sizes
        cache_sizes = [1000, 5000, 10000]
        memory_results = {}
        
        for size in cache_sizes:
            print(f"Testing memory usage with {size} cache items...")
            
            # Fill cache with data
            for i in range(size):
                key = f"memory_key_{i}"
                value = f"memory_value_{i}" * 100  # Larger values for memory testing
                await cache_strategy.set(key, value, ttl=300)
            
            # Measure memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = current_memory - initial_memory
            
            memory_results[size] = {
                "memory_used_mb": memory_used,
                "memory_per_item_kb": (memory_used * 1024) / size
            }
            
            print(f"  Memory Used: {memory_used:.2f} MB")
            print(f"  Memory per Item: {memory_per_item_kb:.2f} KB")
            
            # Clear cache for next test
            for i in range(size):
                key = f"memory_key_{i}"
                await cache_strategy.delete(key)
        
        # Memory usage assertions
        assert memory_results[1000]["memory_per_item_kb"] < 10   # Less than 10KB per item
        assert memory_results[5000]["memory_per_item_kb"] < 8    # Less than 8KB per item for larger caches
        assert memory_results[10000]["memory_per_item_kb"] < 6   # Less than 6KB per item for large caches


class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    @pytest.fixture
    async def payment_repository(self, test_db_session):
        """Create payment repository instance."""
        return PaymentRepository(test_db_session)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_database_bulk_operations_performance(self, payment_repository, test_db_session):
        """Test database bulk operations performance."""
        # Test bulk insert performance
        batch_sizes = [100, 500, 1000]
        results = {}
        
        for batch_size in batch_sizes:
            print(f"Testing bulk insert with {batch_size} payments...")
            
            # Create payment data
            payments = []
            for i in range(batch_size):
                payment_data = {
                    "amount": Decimal(f"{10 + (i % 50)}.00"),
                    "currency": "USD",
                    "payment_method": PaymentMethod.CREDIT_CARD.value,
                    "customer_id": f"cust_bulk_{i}",
                    "customer_email": f"bulk{i}@example.com",
                    "customer_name": f"Bulk Test Customer {i}",
                    "card_token": f"tok_bulk_{i}",
                    "description": f"Bulk test payment {i}",
                    "status": PaymentStatus.PENDING,
                    "external_id": f"pay_bulk_{uuid.uuid4().hex[:12]}",
                    "is_test": True
                }
                payment = Payment(**payment_data)
                payments.append(payment)
            
            # Measure bulk insert time
            start_time = time.time()
            
            test_db_session.add_all(payments)
            await test_db_session.commit()
            
            end_time = time.time()
            
            insert_time = end_time - start_time
            inserts_per_second = batch_size / insert_time
            
            results[batch_size] = {
                "insert_time": insert_time,
                "inserts_per_second": inserts_per_second
            }
            
            print(f"  Insert Time: {insert_time:.3f}s ({inserts_per_second:.0f} inserts/sec)")
        
        # Performance assertions
        assert results[100]["inserts_per_second"] > 50    # At least 50 inserts/sec
        assert results[500]["inserts_per_second"] > 25     # At least 25 inserts/sec for larger batches
        assert results[1000]["inserts_per_second"] > 10   # At least 10 inserts/sec for large batches
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_database_query_performance(self, payment_repository, test_db_session):
        """Test database query performance."""
        # Create test data
        test_payments = []
        for i in range(1000):
            payment_data = {
                "amount": Decimal(f"{10 + (i % 100)}.00"),
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "customer_id": f"cust_query_{i % 50}",  # 50 unique customers
                "customer_email": f"query{i % 50}@example.com",
                "customer_name": f"Query Test Customer {i % 50}",
                "card_token": f"tok_query_{i}",
                "description": f"Query test payment {i}",
                "status": PaymentStatus.PENDING if i % 2 == 0 else PaymentStatus.AUTHORIZED,
                "external_id": f"pay_query_{uuid.uuid4().hex[:12]}",
                "is_test": True
            }
            payment = Payment(**payment_data)
            test_payments.append(payment)
        
        test_db_session.add_all(test_payments)
        await test_db_session.commit()
        
        # Test different query types
        query_tests = [
            {
                "name": "Simple ID lookup",
                "query": lambda: payment_repository.get_by_id(test_payments[0].id),
                "expected_time": 0.1
            },
            {
                "name": "Customer ID search",
                "query": lambda: payment_repository.get_by_customer_id("cust_query_1"),
                "expected_time": 0.5
            },
            {
                "name": "Status filter",
                "query": lambda: payment_repository.search_payments(status=PaymentStatus.PENDING),
                "expected_time": 1.0
            },
            {
                "name": "Amount range search",
                "query": lambda: payment_repository.search_payments(min_amount=Decimal("50.00"), max_amount=Decimal("60.00")),
                "expected_time": 1.0
            },
            {
                "name": "Complex multi-filter search",
                "query": lambda: payment_repository.search_payments(
                    customer_id="cust_query_5",
                    status=PaymentStatus.AUTHORIZED,
                    min_amount=Decimal("20.00"),
                    max_amount=Decimal("80.00")
                ),
                "expected_time": 1.5
            }
        ]
        
        results = {}
        
        for test in query_tests:
            print(f"Testing {test['name']}...")
            
            # Measure query time
            start_time = time.time()
            result = await test["query"]()
            end_time = time.time()
            
            query_time = end_time - start_time
            result_count = len(result) if isinstance(result, list) else (1 if result else 0)
            
            results[test["name"]] = {
                "query_time": query_time,
                "result_count": result_count,
                "within_expected": query_time <= test["expected_time"]
            }
            
            print(f"  Query Time: {query_time:.3f}s")
            print(f"  Results: {result_count}")
            print(f"  Within Expected: {query_time <= test['expected_time']}")
        
        # Performance assertions
        assert results["Simple ID lookup"]["query_time"] < 0.1
        assert results["Customer ID search"]["query_time"] < 0.5
        assert results["Status filter"]["query_time"] < 1.0
        assert results["Amount range search"]["query_time"] < 1.0
        assert results["Complex multi-filter search"]["query_time"] < 1.5


class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Performance Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read", "payment:update"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_api_endpoint_performance(self, authenticated_client):
        """Test API endpoint performance."""
        # Test different endpoints
        endpoint_tests = [
            {
                "name": "Health Check",
                "method": "GET",
                "path": "/api/v1/health",
                "expected_time": 0.5
            },
            {
                "name": "Payment Creation",
                "method": "POST",
                "path": "/api/v1/payments",
                "data": {
                    "amount": "25.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": "cust_api_perf_123",
                    "customer_email": "apiperf@example.com",
                    "customer_name": "API Performance Test Customer",
                    "card_token": "tok_api_perf_123",
                    "description": "API performance test payment",
                    "is_test": True
                },
                "expected_time": 2.0
            },
            {
                "name": "Payment Retrieval",
                "method": "GET",
                "path": "/api/v1/payments/{payment_id}",
                "expected_time": 1.0
            }
        ]
        
        results = {}
        
        # Create a payment for retrieval test
        payment_data = {
            "amount": "30.00",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": "cust_api_perf_456",
            "customer_email": "apiperf2@example.com",
            "customer_name": "API Performance Test Customer 2",
            "card_token": "tok_api_perf_456",
            "description": "API performance test payment 2",
            "is_test": True
        }
        
        create_response = await authenticated_client.post("/api/v1/payments", json=payment_data)
        assert create_response.status_code == 201
        payment_id = create_response.json()["data"]["id"]
        
        for test in endpoint_tests:
            print(f"Testing {test['name']} performance...")
            
            # Prepare request
            if test["method"] == "GET":
                if "{payment_id}" in test["path"]:
                    path = test["path"].format(payment_id=payment_id)
                else:
                    path = test["path"]
                request_func = lambda: authenticated_client.get(path)
            elif test["method"] == "POST":
                request_func = lambda: authenticated_client.post(test["path"], json=test["data"])
            
            # Measure response time
            times = []
            for _ in range(10):  # Test 10 times for average
                start_time = time.time()
                response = await request_func()
                end_time = time.time()
                
                response_time = end_time - start_time
                times.append(response_time)
                
                assert response.status_code in [200, 201], f"Unexpected status code: {response.status_code}"
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            results[test["name"]] = {
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "std_dev": std_dev,
                "within_expected": avg_time <= test["expected_time"]
            }
            
            print(f"  Average Time: {avg_time:.3f}s")
            print(f"  Min Time: {min_time:.3f}s")
            print(f"  Max Time: {max_time:.3f}s")
            print(f"  Std Dev: {std_dev:.3f}s")
            print(f"  Within Expected: {avg_time <= test['expected_time']}")
        
        # Performance assertions
        assert results["Health Check"]["avg_time"] < 0.5
        assert results["Payment Creation"]["avg_time"] < 2.0
        assert results["Payment Retrieval"]["avg_time"] < 1.0
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_api_concurrent_load_performance(self, authenticated_client):
        """Test API performance under concurrent load."""
        # Test different concurrency levels
        concurrency_levels = [10, 25, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"Testing API performance with {concurrency} concurrent requests...")
            
            # Create concurrent requests
            async def make_request():
                start_time = time.time()
                response = await authenticated_client.get("/api/v1/health")
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
            
            # Execute concurrent requests
            start_time = time.time()
            tasks = [make_request() for _ in range(concurrency)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Analyze results
            successful_requests = len([r for r in responses if not isinstance(r, Exception) and r["success"]])
            failed_requests = len([r for r in responses if isinstance(r, Exception)])
            error_requests = len([r for r in responses if not isinstance(r, Exception) and not r["success"]])
            
            response_times = [r["response_time"] for r in responses if not isinstance(r, Exception)]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            results[concurrency] = {
                "total_time": total_time,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "error_requests": error_requests,
                "success_rate": successful_requests / concurrency,
                "avg_response_time": avg_response_time,
                "requests_per_second": concurrency / total_time
            }
            
            print(f"  Total Time: {total_time:.3f}s")
            print(f"  Successful: {successful_requests}/{concurrency}")
            print(f"  Failed: {failed_requests}")
            print(f"  Errors: {error_requests}")
            print(f"  Success Rate: {successful_requests/concurrency:.2%}")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  Requests/sec: {concurrency/total_time:.2f}")
        
        # Performance assertions
        assert results[10]["success_rate"] > 0.95   # At least 95% success rate for low concurrency
        assert results[25]["success_rate"] > 0.90   # At least 90% success rate for medium concurrency
        assert results[50]["success_rate"] > 0.80   # At least 80% success rate for high concurrency
        assert results[100]["success_rate"] > 0.70  # At least 70% success rate for very high concurrency


class TestSystemPerformance:
    """System-wide performance tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_end_to_end_performance(self):
        """Test end-to-end system performance."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key
            api_key_data = {
                "name": "E2E Performance Test Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read", "payment:update"]
            }
            
            start_time = time.time()
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            end_time = time.time()
            
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            api_key_creation_time = end_time - start_time
            
            # Set authorization header
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            
            # Test complete payment flow
            payment_flow_times = []
            
            for i in range(10):  # Test 10 complete flows
                flow_start_time = time.time()
                
                # 1. Create payment
                payment_data = {
                    "amount": f"{20 + i}.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_e2e_perf_{i}",
                    "customer_email": f"e2eperf{i}@example.com",
                    "customer_name": f"E2E Performance Test Customer {i}",
                    "card_token": f"tok_e2e_perf_{i}",
                    "description": f"E2E performance test payment {i}",
                    "is_test": True
                }
                
                create_response = await client.post("/api/v1/payments", json=payment_data)
                assert create_response.status_code == 201
                payment_id = create_response.json()["data"]["id"]
                
                # 2. Get payment
                get_response = await client.get(f"/api/v1/payments/{payment_id}")
                assert get_response.status_code == 200
                
                # 3. Update payment
                update_data = {"status": "authorized"}
                update_response = await client.put(f"/api/v1/payments/{payment_id}", json=update_data)
                assert update_response.status_code == 200
                
                flow_end_time = time.time()
                flow_time = flow_end_time - flow_start_time
                payment_flow_times.append(flow_time)
            
            # Calculate statistics
            avg_flow_time = statistics.mean(payment_flow_times)
            min_flow_time = min(payment_flow_times)
            max_flow_time = max(payment_flow_times)
            
            print(f"\nEnd-to-End Performance Results:")
            print(f"API Key Creation Time: {api_key_creation_time:.3f}s")
            print(f"Average Payment Flow Time: {avg_flow_time:.3f}s")
            print(f"Min Payment Flow Time: {min_flow_time:.3f}s")
            print(f"Max Payment Flow Time: {max_flow_time:.3f}s")
            
            # Performance assertions
            assert api_key_creation_time < 2.0    # API key creation should be fast
            assert avg_flow_time < 5.0            # Average payment flow should be reasonable
            assert max_flow_time < 10.0           # Max payment flow should not be too slow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
