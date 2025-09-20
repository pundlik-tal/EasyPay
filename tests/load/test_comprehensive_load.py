"""
EasyPay Payment Gateway - Comprehensive Load Tests

This module contains comprehensive load tests for all system components
including stress testing, endurance testing, and scalability testing.
"""

import pytest
import uuid
import asyncio
import time
import statistics
import concurrent.futures
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Tuple
import threading
import random

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.services.payment_service import PaymentService
from src.core.services.auth_service import AuthService
from src.core.services.webhook_service import WebhookService
from src.core.repositories.payment_repository import PaymentRepository
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.models.auth import APIKey, AuthToken, User
from src.core.models.webhook import Webhook, WebhookStatus


class TestPaymentLoadTesting:
    """Load tests for payment operations."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Load Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read", "payment:update", "payment:refund"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_payment_creation_load(self, authenticated_client):
        """Test payment creation under various load conditions."""
        # Test different load levels
        load_levels = [
            {"concurrent_users": 10, "requests_per_user": 10, "expected_success_rate": 0.95},
            {"concurrent_users": 25, "requests_per_user": 20, "expected_success_rate": 0.90},
            {"concurrent_users": 50, "requests_per_user": 30, "expected_success_rate": 0.85},
            {"concurrent_users": 100, "requests_per_user": 50, "expected_success_rate": 0.80}
        ]
        
        results = {}
        
        for load_level in load_levels:
            print(f"\nTesting load: {load_level['concurrent_users']} users, {load_level['requests_per_user']} requests each")
            
            # Create concurrent users
            async def simulate_user(user_id: int, requests_count: int):
                """Simulate a single user making requests."""
                user_results = []
                
                for request_id in range(requests_count):
                    payment_data = {
                        "amount": f"{10 + (request_id % 50)}.00",
                        "currency": "USD",
                        "payment_method": "credit_card",
                        "customer_id": f"cust_load_{user_id}_{request_id}",
                        "customer_email": f"load{user_id}_{request_id}@example.com",
                        "customer_name": f"Load Test Customer {user_id}-{request_id}",
                        "card_token": f"tok_load_{user_id}_{request_id}",
                        "description": f"Load test payment {user_id}-{request_id}",
                        "is_test": True
                    }
                    
                    start_time = time.time()
                    try:
                        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                        end_time = time.time()
                        
                        user_results.append({
                            "success": response.status_code == 201,
                            "response_time": end_time - start_time,
                            "status_code": response.status_code,
                            "request_id": request_id
                        })
                    except Exception as e:
                        end_time = time.time()
                        user_results.append({
                            "success": False,
                            "response_time": end_time - start_time,
                            "error": str(e),
                            "request_id": request_id
                        })
                
                return user_results
            
            # Execute load test
            start_time = time.time()
            
            tasks = []
            for user_id in range(load_level["concurrent_users"]):
                task = simulate_user(user_id, load_level["requests_per_user"])
                tasks.append(task)
            
            all_results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Analyze results
            total_requests = load_level["concurrent_users"] * load_level["requests_per_user"]
            successful_requests = sum(len([r for r in user_results if r["success"]]) for user_results in all_results)
            failed_requests = total_requests - successful_requests
            
            all_response_times = []
            for user_results in all_results:
                all_response_times.extend([r["response_time"] for r in user_results])
            
            avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
            p95_response_time = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 20 else max(all_response_times) if all_response_times else 0
            p99_response_time = statistics.quantiles(all_response_times, n=100)[98] if len(all_response_times) > 100 else max(all_response_times) if all_response_times else 0
            
            success_rate = successful_requests / total_requests
            requests_per_second = total_requests / (end_time - start_time)
            
            results[load_level["concurrent_users"]] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "p99_response_time": p99_response_time,
                "requests_per_second": requests_per_second,
                "total_time": end_time - start_time
            }
            
            print(f"  Total Requests: {total_requests}")
            print(f"  Successful: {successful_requests} ({success_rate:.2%})")
            print(f"  Failed: {failed_requests}")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  95th Percentile: {p95_response_time:.3f}s")
            print(f"  99th Percentile: {p99_response_time:.3f}s")
            print(f"  Requests/sec: {requests_per_second:.2f}")
            print(f"  Total Time: {end_time - start_time:.3f}s")
            
            # Verify success rate meets expectations
            assert success_rate >= load_level["expected_success_rate"], f"Success rate {success_rate:.2%} below expected {load_level['expected_success_rate']:.2%}"
        
        # Performance assertions
        assert results[10]["avg_response_time"] < 2.0    # Low load should be fast
        assert results[25]["avg_response_time"] < 3.0    # Medium load should be reasonable
        assert results[50]["avg_response_time"] < 5.0    # High load should be acceptable
        assert results[100]["avg_response_time"] < 10.0   # Very high load should not be too slow
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_payment_read_load(self, authenticated_client):
        """Test payment read operations under load."""
        # First create some test payments
        print("Creating test payments for read load test...")
        
        test_payments = []
        for i in range(100):
            payment_data = {
                "amount": f"{10 + (i % 50)}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_read_load_{i}",
                "customer_email": f"readload{i}@example.com",
                "customer_name": f"Read Load Test Customer {i}",
                "card_token": f"tok_read_load_{i}",
                "description": f"Read load test payment {i}",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            if response.status_code == 201:
                test_payments.append(response.json()["data"])
        
        print(f"Created {len(test_payments)} test payments")
        
        # Test different read load scenarios
        read_scenarios = [
            {
                "name": "Individual Payment Reads",
                "concurrent_users": 20,
                "requests_per_user": 25,
                "operation": lambda client, payment_id: client.get(f"/api/v1/payments/{payment_id}")
            },
            {
                "name": "Payment List Reads",
                "concurrent_users": 15,
                "requests_per_user": 20,
                "operation": lambda client, _: client.get("/api/v1/payments")
            },
            {
                "name": "Payment Search Reads",
                "concurrent_users": 10,
                "requests_per_user": 15,
                "operation": lambda client, _: client.get("/api/v1/payments/search?status=pending")
            }
        ]
        
        results = {}
        
        for scenario in read_scenarios:
            print(f"\nTesting {scenario['name']} load...")
            
            async def simulate_read_user(user_id: int, requests_count: int):
                """Simulate a single user making read requests."""
                user_results = []
                
                for request_id in range(requests_count):
                    # Select random payment for individual reads
                    if "Individual" in scenario["name"]:
                        payment_id = random.choice(test_payments)["id"]
                    else:
                        payment_id = None
                    
                    start_time = time.time()
                    try:
                        response = await scenario["operation"](authenticated_client, payment_id)
                        end_time = time.time()
                        
                        user_results.append({
                            "success": response.status_code == 200,
                            "response_time": end_time - start_time,
                            "status_code": response.status_code,
                            "request_id": request_id
                        })
                    except Exception as e:
                        end_time = time.time()
                        user_results.append({
                            "success": False,
                            "response_time": end_time - start_time,
                            "error": str(e),
                            "request_id": request_id
                        })
                
                return user_results
            
            # Execute read load test
            start_time = time.time()
            
            tasks = []
            for user_id in range(scenario["concurrent_users"]):
                task = simulate_read_user(user_id, scenario["requests_per_user"])
                tasks.append(task)
            
            all_results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Analyze results
            total_requests = scenario["concurrent_users"] * scenario["requests_per_user"]
            successful_requests = sum(len([r for r in user_results if r["success"]]) for user_results in all_results)
            
            all_response_times = []
            for user_results in all_results:
                all_response_times.extend([r["response_time"] for r in user_results])
            
            avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
            p95_response_time = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 20 else max(all_response_times) if all_response_times else 0
            
            success_rate = successful_requests / total_requests
            requests_per_second = total_requests / (end_time - start_time)
            
            results[scenario["name"]] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "requests_per_second": requests_per_second
            }
            
            print(f"  Total Requests: {total_requests}")
            print(f"  Successful: {successful_requests} ({success_rate:.2%})")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  95th Percentile: {p95_response_time:.3f}s")
            print(f"  Requests/sec: {requests_per_second:.2f}")
        
        # Performance assertions for read operations
        assert results["Individual Payment Reads"]["avg_response_time"] < 1.0
        assert results["Payment List Reads"]["avg_response_time"] < 2.0
        assert results["Payment Search Reads"]["avg_response_time"] < 3.0
        
        assert results["Individual Payment Reads"]["success_rate"] > 0.95
        assert results["Payment List Reads"]["success_rate"] > 0.90
        assert results["Payment Search Reads"]["success_rate"] > 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_mixed_workload_load(self, authenticated_client):
        """Test mixed workload under load."""
        print("\nTesting mixed workload under load...")
        
        # Define mixed workload
        workload_mix = [
            {"operation": "create", "weight": 0.3, "concurrent_users": 20},
            {"operation": "read", "weight": 0.5, "concurrent_users": 30},
            {"operation": "update", "weight": 0.2, "concurrent_users": 10}
        ]
        
        # Create some test payments for read/update operations
        test_payments = []
        for i in range(50):
            payment_data = {
                "amount": f"{10 + (i % 30)}.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_mixed_{i}",
                "customer_email": f"mixed{i}@example.com",
                "customer_name": f"Mixed Load Test Customer {i}",
                "card_token": f"tok_mixed_{i}",
                "description": f"Mixed load test payment {i}",
                "is_test": True
            }
            
            response = await authenticated_client.post("/api/v1/payments", json=payment_data)
            if response.status_code == 201:
                test_payments.append(response.json()["data"])
        
        print(f"Created {len(test_payments)} test payments for mixed workload")
        
        async def simulate_mixed_user(user_id: int, operation_type: str, requests_count: int):
            """Simulate a user performing mixed operations."""
            user_results = []
            
            for request_id in range(requests_count):
                start_time = time.time()
                
                try:
                    if operation_type == "create":
                        payment_data = {
                            "amount": f"{10 + (request_id % 50)}.00",
                            "currency": "USD",
                            "payment_method": "credit_card",
                            "customer_id": f"cust_mixed_create_{user_id}_{request_id}",
                            "customer_email": f"mixedcreate{user_id}_{request_id}@example.com",
                            "customer_name": f"Mixed Create Customer {user_id}-{request_id}",
                            "card_token": f"tok_mixed_create_{user_id}_{request_id}",
                            "description": f"Mixed create test payment {user_id}-{request_id}",
                            "is_test": True
                        }
                        response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                        success = response.status_code == 201
                        
                    elif operation_type == "read":
                        if test_payments:
                            payment_id = random.choice(test_payments)["id"]
                            response = await authenticated_client.get(f"/api/v1/payments/{payment_id}")
                            success = response.status_code == 200
                        else:
                            success = False
                            
                    elif operation_type == "update":
                        if test_payments:
                            payment_id = random.choice(test_payments)["id"]
                            update_data = {"status": "authorized"}
                            response = await authenticated_client.put(f"/api/v1/payments/{payment_id}", json=update_data)
                            success = response.status_code == 200
                        else:
                            success = False
                    
                    end_time = time.time()
                    
                    user_results.append({
                        "operation": operation_type,
                        "success": success,
                        "response_time": end_time - start_time,
                        "status_code": response.status_code if 'response' in locals() else 0,
                        "request_id": request_id
                    })
                    
                except Exception as e:
                    end_time = time.time()
                    user_results.append({
                        "operation": operation_type,
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": str(e),
                        "request_id": request_id
                    })
            
            return user_results
        
        # Execute mixed workload test
        start_time = time.time()
        
        tasks = []
        requests_per_user = 20
        
        for workload in workload_mix:
            for user_id in range(workload["concurrent_users"]):
                task = simulate_mixed_user(user_id, workload["operation"], requests_per_user)
                tasks.append(task)
        
        all_results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyze results by operation type
        operation_results = {}
        
        for workload in workload_mix:
            operation = workload["operation"]
            operation_results[operation] = {
                "total_requests": 0,
                "successful_requests": 0,
                "response_times": []
            }
        
        for user_results in all_results:
            for result in user_results:
                operation = result["operation"]
                operation_results[operation]["total_requests"] += 1
                if result["success"]:
                    operation_results[operation]["successful_requests"] += 1
                operation_results[operation]["response_times"].append(result["response_time"])
        
        # Calculate metrics for each operation
        for operation, data in operation_results.items():
            if data["total_requests"] > 0:
                success_rate = data["successful_requests"] / data["total_requests"]
                avg_response_time = statistics.mean(data["response_times"]) if data["response_times"] else 0
                p95_response_time = statistics.quantiles(data["response_times"], n=20)[18] if len(data["response_times"]) > 20 else max(data["response_times"]) if data["response_times"] else 0
                
                print(f"\n{operation.upper()} Operation Results:")
                print(f"  Total Requests: {data['total_requests']}")
                print(f"  Successful: {data['successful_requests']} ({success_rate:.2%})")
                print(f"  Avg Response Time: {avg_response_time:.3f}s")
                print(f"  95th Percentile: {p95_response_time:.3f}s")
        
        total_requests = sum(data["total_requests"] for data in operation_results.values())
        total_successful = sum(data["successful_requests"] for data in operation_results.values())
        overall_success_rate = total_successful / total_requests if total_requests > 0 else 0
        total_time = end_time - start_time
        overall_requests_per_second = total_requests / total_time
        
        print(f"\nOverall Mixed Workload Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {total_successful} ({overall_success_rate:.2%})")
        print(f"  Requests/sec: {overall_requests_per_second:.2f}")
        print(f"  Total Time: {total_time:.3f}s")
        
        # Performance assertions
        assert overall_success_rate > 0.80, f"Overall success rate {overall_success_rate:.2%} too low"
        assert overall_requests_per_second > 10, f"Requests per second {overall_requests_per_second:.2f} too low"


class TestAuthenticationLoadTesting:
    """Load tests for authentication operations."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_authentication_load(self, client):
        """Test authentication operations under load."""
        print("\nTesting authentication load...")
        
        # Test API key creation load
        async def simulate_api_key_creation(user_id: int, requests_count: int):
            """Simulate API key creation requests."""
            user_results = []
            
            for request_id in range(requests_count):
                api_key_data = {
                    "name": f"Load Test API Key {user_id}_{request_id}",
                    "environment": "sandbox",
                    "permissions": ["payment:create", "payment:read"]
                }
                
                start_time = time.time()
                try:
                    response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
                    end_time = time.time()
                    
                    user_results.append({
                        "success": response.status_code == 201,
                        "response_time": end_time - start_time,
                        "status_code": response.status_code,
                        "request_id": request_id
                    })
                except Exception as e:
                    end_time = time.time()
                    user_results.append({
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": str(e),
                        "request_id": request_id
                    })
            
            return user_results
        
        # Test token generation load
        async def simulate_token_generation(user_id: int, requests_count: int):
            """Simulate token generation requests."""
            user_results = []
            
            for request_id in range(requests_count):
                token_data = {
                    "user_id": f"user_load_{user_id}_{request_id}",
                    "permissions": ["payment:create", "payment:read"]
                }
                
                start_time = time.time()
                try:
                    response = await client.post("/api/v1/auth/tokens", json=token_data)
                    end_time = time.time()
                    
                    user_results.append({
                        "success": response.status_code == 201,
                        "response_time": end_time - start_time,
                        "status_code": response.status_code,
                        "request_id": request_id
                    })
                except Exception as e:
                    end_time = time.time()
                    user_results.append({
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": str(e),
                        "request_id": request_id
                    })
            
            return user_results
        
        # Test API key creation load
        print("Testing API key creation load...")
        start_time = time.time()
        
        api_key_tasks = []
        for user_id in range(20):  # 20 concurrent users
            task = simulate_api_key_creation(user_id, 10)  # 10 requests each
            api_key_tasks.append(task)
        
        api_key_results = await asyncio.gather(*api_key_tasks)
        api_key_end_time = time.time()
        
        # Analyze API key creation results
        api_key_total_requests = 20 * 10
        api_key_successful = sum(len([r for r in user_results if r["success"]]) for user_results in api_key_results)
        api_key_success_rate = api_key_successful / api_key_total_requests
        
        api_key_response_times = []
        for user_results in api_key_results:
            api_key_response_times.extend([r["response_time"] for r in user_results])
        
        api_key_avg_response_time = statistics.mean(api_key_response_times) if api_key_response_times else 0
        api_key_requests_per_second = api_key_total_requests / (api_key_end_time - start_time)
        
        print(f"  API Key Creation Results:")
        print(f"    Total Requests: {api_key_total_requests}")
        print(f"    Successful: {api_key_successful} ({api_key_success_rate:.2%})")
        print(f"    Avg Response Time: {api_key_avg_response_time:.3f}s")
        print(f"    Requests/sec: {api_key_requests_per_second:.2f}")
        
        # Test token generation load
        print("Testing token generation load...")
        start_time = time.time()
        
        token_tasks = []
        for user_id in range(25):  # 25 concurrent users
            task = simulate_token_generation(user_id, 15)  # 15 requests each
            token_tasks.append(task)
        
        token_results = await asyncio.gather(*token_tasks)
        token_end_time = time.time()
        
        # Analyze token generation results
        token_total_requests = 25 * 15
        token_successful = sum(len([r for r in user_results if r["success"]]) for user_results in token_results)
        token_success_rate = token_successful / token_total_requests
        
        token_response_times = []
        for user_results in token_results:
            token_response_times.extend([r["response_time"] for r in user_results])
        
        token_avg_response_time = statistics.mean(token_response_times) if token_response_times else 0
        token_requests_per_second = token_total_requests / (token_end_time - start_time)
        
        print(f"  Token Generation Results:")
        print(f"    Total Requests: {token_total_requests}")
        print(f"    Successful: {token_successful} ({token_success_rate:.2%})")
        print(f"    Avg Response Time: {token_avg_response_time:.3f}s")
        print(f"    Requests/sec: {token_requests_per_second:.2f}")
        
        # Performance assertions
        assert api_key_success_rate > 0.90, f"API key creation success rate {api_key_success_rate:.2%} too low"
        assert token_success_rate > 0.90, f"Token generation success rate {token_success_rate:.2%} too low"
        assert api_key_avg_response_time < 3.0, f"API key creation response time {api_key_avg_response_time:.3f}s too high"
        assert token_avg_response_time < 2.0, f"Token generation response time {token_avg_response_time:.3f}s too high"


class TestWebhookLoadTesting:
    """Load tests for webhook operations."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Webhook Load Test API Key",
                "environment": "sandbox",
                "permissions": ["webhook:create", "webhook:read", "webhook:update"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_webhook_registration_load(self, authenticated_client):
        """Test webhook registration under load."""
        print("\nTesting webhook registration load...")
        
        async def simulate_webhook_registration(user_id: int, requests_count: int):
            """Simulate webhook registration requests."""
            user_results = []
            
            for request_id in range(requests_count):
                webhook_data = {
                    "webhook_url": f"https://loadtest{user_id}_{request_id}.example.com/webhook",
                    "event_type": "payment.created",
                    "secret": f"webhook_secret_{user_id}_{request_id}",
                    "max_retries": 3,
                    "retry_interval": 60
                }
                
                start_time = time.time()
                try:
                    response = await authenticated_client.post("/api/v1/webhooks", json=webhook_data)
                    end_time = time.time()
                    
                    user_results.append({
                        "success": response.status_code == 201,
                        "response_time": end_time - start_time,
                        "status_code": response.status_code,
                        "request_id": request_id
                    })
                except Exception as e:
                    end_time = time.time()
                    user_results.append({
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": str(e),
                        "request_id": request_id
                    })
            
            return user_results
        
        # Execute webhook registration load test
        start_time = time.time()
        
        tasks = []
        for user_id in range(15):  # 15 concurrent users
            task = simulate_webhook_registration(user_id, 20)  # 20 requests each
            tasks.append(task)
        
        all_results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyze results
        total_requests = 15 * 20
        successful_requests = sum(len([r for r in user_results if r["success"]]) for user_results in all_results)
        success_rate = successful_requests / total_requests
        
        all_response_times = []
        for user_results in all_results:
            all_response_times.extend([r["response_time"] for r in user_results])
        
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        p95_response_time = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 20 else max(all_response_times) if all_response_times else 0
        requests_per_second = total_requests / (end_time - start_time)
        
        print(f"  Webhook Registration Results:")
        print(f"    Total Requests: {total_requests}")
        print(f"    Successful: {successful_requests} ({success_rate:.2%})")
        print(f"    Avg Response Time: {avg_response_time:.3f}s")
        print(f"    95th Percentile: {p95_response_time:.3f}s")
        print(f"    Requests/sec: {requests_per_second:.2f}")
        
        # Performance assertions
        assert success_rate > 0.85, f"Webhook registration success rate {success_rate:.2%} too low"
        assert avg_response_time < 2.0, f"Webhook registration response time {avg_response_time:.3f}s too high"
        assert requests_per_second > 50, f"Webhook registration requests per second {requests_per_second:.2f} too low"


class TestEnduranceTesting:
    """Endurance tests for long-running operations."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Endurance Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_endurance_payment_creation(self, authenticated_client):
        """Test payment creation endurance over time."""
        print("\nTesting payment creation endurance...")
        
        # Run endurance test for 5 minutes
        test_duration = 300  # 5 minutes
        start_time = time.time()
        
        async def endurance_worker(worker_id: int):
            """Worker for endurance testing."""
            worker_results = []
            request_count = 0
            
            while time.time() - start_time < test_duration:
                payment_data = {
                    "amount": f"{10 + (request_count % 50)}.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_endurance_{worker_id}_{request_count}",
                    "customer_email": f"endurance{worker_id}_{request_count}@example.com",
                    "customer_name": f"Endurance Test Customer {worker_id}-{request_count}",
                    "card_token": f"tok_endurance_{worker_id}_{request_count}",
                    "description": f"Endurance test payment {worker_id}-{request_count}",
                    "is_test": True
                }
                
                request_start_time = time.time()
                try:
                    response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                    request_end_time = time.time()
                    
                    worker_results.append({
                        "success": response.status_code == 201,
                        "response_time": request_end_time - request_start_time,
                        "timestamp": request_end_time,
                        "request_count": request_count
                    })
                except Exception as e:
                    request_end_time = time.time()
                    worker_results.append({
                        "success": False,
                        "response_time": request_end_time - request_start_time,
                        "timestamp": request_end_time,
                        "error": str(e),
                        "request_count": request_count
                    })
                
                request_count += 1
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            return worker_results
        
        # Start endurance workers
        workers = []
        for worker_id in range(5):  # 5 concurrent workers
            worker = endurance_worker(worker_id)
            workers.append(worker)
        
        # Wait for endurance test to complete
        all_results = await asyncio.gather(*workers)
        end_time = time.time()
        
        # Analyze endurance results
        total_requests = sum(len(worker_results) for worker_results in all_results)
        successful_requests = sum(len([r for r in worker_results if r["success"]]) for worker_results in all_results)
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        all_response_times = []
        for worker_results in all_results:
            all_response_times.extend([r["response_time"] for r in worker_results])
        
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        max_response_time = max(all_response_times) if all_response_times else 0
        min_response_time = min(all_response_times) if all_response_times else 0
        
        # Calculate requests per second over time
        requests_per_second = total_requests / (end_time - start_time)
        
        # Check for performance degradation over time
        time_windows = []
        window_size = 60  # 1 minute windows
        
        for window_start in range(0, int(end_time - start_time), window_size):
            window_end = window_start + window_size
            window_requests = []
            
            for worker_results in all_results:
                for result in worker_results:
                    result_time = result["timestamp"] - start_time
                    if window_start <= result_time < window_end:
                        window_requests.append(result)
            
            if window_requests:
                window_success_rate = len([r for r in window_requests if r["success"]]) / len(window_requests)
                window_avg_response_time = statistics.mean([r["response_time"] for r in window_requests])
                
                time_windows.append({
                    "window": f"{window_start}-{window_end}s",
                    "requests": len(window_requests),
                    "success_rate": window_success_rate,
                    "avg_response_time": window_avg_response_time
                })
        
        print(f"  Endurance Test Results ({test_duration}s):")
        print(f"    Total Requests: {total_requests}")
        print(f"    Successful: {successful_requests} ({success_rate:.2%})")
        print(f"    Avg Response Time: {avg_response_time:.3f}s")
        print(f"    Min Response Time: {min_response_time:.3f}s")
        print(f"    Max Response Time: {max_response_time:.3f}s")
        print(f"    Requests/sec: {requests_per_second:.2f}")
        
        print(f"  Performance Over Time:")
        for window in time_windows:
            print(f"    {window['window']}: {window['requests']} requests, {window['success_rate']:.2%} success, {window['avg_response_time']:.3f}s avg")
        
        # Performance assertions
        assert success_rate > 0.90, f"Endurance test success rate {success_rate:.2%} too low"
        assert avg_response_time < 3.0, f"Endurance test avg response time {avg_response_time:.3f}s too high"
        assert max_response_time < 10.0, f"Endurance test max response time {max_response_time:.3f}s too high"
        
        # Check for performance degradation
        if len(time_windows) > 1:
            first_window = time_windows[0]
            last_window = time_windows[-1]
            
            # Success rate should not degrade significantly
            success_rate_degradation = first_window["success_rate"] - last_window["success_rate"]
            assert success_rate_degradation < 0.1, f"Success rate degraded by {success_rate_degradation:.2%}"
            
            # Response time should not increase significantly
            response_time_increase = last_window["avg_response_time"] - first_window["avg_response_time"]
            assert response_time_increase < 2.0, f"Response time increased by {response_time_increase:.3f}s"


class TestScalabilityTesting:
    """Scalability tests for system growth."""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create API key for authentication
            api_key_data = {
                "name": "Scalability Test API Key",
                "environment": "sandbox",
                "permissions": ["payment:create", "payment:read"]
            }
            
            response = await client.post("/api/v1/auth/api-keys", json=api_key_data)
            assert response.status_code == 201
            api_key = response.json()["data"]["key"]
            
            client.headers.update({"Authorization": f"Bearer {api_key}"})
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_scalability_with_data_growth(self, authenticated_client):
        """Test system scalability as data grows."""
        print("\nTesting scalability with data growth...")
        
        # Create increasing amounts of data and test performance
        data_sizes = [100, 500, 1000, 2000]
        results = {}
        
        for data_size in data_sizes:
            print(f"Testing with {data_size} payments...")
            
            # Create test data
            test_payments = []
            for i in range(data_size):
                payment_data = {
                    "amount": f"{10 + (i % 50)}.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_scale_{i}",
                    "customer_email": f"scale{i}@example.com",
                    "customer_name": f"Scalability Test Customer {i}",
                    "card_token": f"tok_scale_{i}",
                    "description": f"Scalability test payment {i}",
                    "is_test": True
                }
                
                response = await authenticated_client.post("/api/v1/payments", json=payment_data)
                if response.status_code == 201:
                    test_payments.append(response.json()["data"])
            
            print(f"Created {len(test_payments)} payments")
            
            # Test read performance with current data size
            read_tests = [
                {
                    "name": "Individual Payment Read",
                    "operation": lambda: authenticated_client.get(f"/api/v1/payments/{test_payments[0]['id']}")
                },
                {
                    "name": "Payment List Read",
                    "operation": lambda: authenticated_client.get("/api/v1/payments")
                },
                {
                    "name": "Payment Search",
                    "operation": lambda: authenticated_client.get("/api/v1/payments/search?status=pending")
                }
            ]
            
            data_results = {}
            
            for test in read_tests:
                # Test multiple times for average
                response_times = []
                for _ in range(10):
                    start_time = time.time()
                    response = await test["operation"]()
                    end_time = time.time()
                    
                    response_times.append(end_time - start_time)
                    assert response.status_code == 200, f"{test['name']} failed with status {response.status_code}"
                
                avg_response_time = statistics.mean(response_times)
                data_results[test["name"]] = avg_response_time
                
                print(f"  {test['name']}: {avg_response_time:.3f}s")
            
            results[data_size] = data_results
        
        # Analyze scalability
        print(f"\nScalability Analysis:")
        for data_size, data_results in results.items():
            print(f"  {data_size} payments:")
            for test_name, response_time in data_results.items():
                print(f"    {test_name}: {response_time:.3f}s")
        
        # Check for linear scalability (response time should not increase dramatically)
        individual_read_times = [results[size]["Individual Payment Read"] for size in data_sizes]
        list_read_times = [results[size]["Payment List Read"] for size in data_sizes]
        search_times = [results[size]["Payment Search"] for size in data_sizes]
        
        # Individual reads should remain fast regardless of data size
        assert max(individual_read_times) < 1.0, "Individual payment reads should remain fast"
        
        # List reads may increase but should not be exponential
        list_read_increase = list_read_times[-1] / list_read_times[0] if list_read_times[0] > 0 else 1
        assert list_read_increase < 5.0, f"List read time increased by {list_read_increase:.1f}x, should be linear"
        
        # Search times should increase reasonably
        search_increase = search_times[-1] / search_times[0] if search_times[0] > 0 else 1
        assert search_increase < 10.0, f"Search time increased by {search_increase:.1f}x, should be reasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
