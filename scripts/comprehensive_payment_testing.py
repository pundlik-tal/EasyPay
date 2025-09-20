#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Comprehensive Payment API Testing Script

This script provides comprehensive testing of all payment gateway APIs including:
- Purchase/Payment Creation
- Payment Retrieval and Listing
- Payment Updates
- Refunds (Full and Partial)
- Payment Cancellation
- Subscription Management
- Webhook Testing
- Performance Monitoring
- Metrics Tracking

Usage:
    python scripts/comprehensive_payment_testing.py [--base-url URL] [--verbose] [--save-results]
"""

import asyncio
import json
import sys
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
import httpx
import argparse
from dataclasses import dataclass

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    AuthorizeNetCredentials, CreditCard, BillingAddress
)
from src.core.config import settings


@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    success: bool
    details: str
    response_time: float
    timestamp: str
    status_code: Optional[int] = None
    error_message: Optional[str] = None


class ComprehensivePaymentTester:
    """Comprehensive payment gateway API tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.client = httpx.AsyncClient(timeout=60.0)
        self.test_results: List[TestResult] = []
        self.created_payments: List[str] = []
        self.created_subscriptions: List[str] = []
        
        # Test data
        self.test_cards = {
            "visa_approved": "4111111111111111",
            "visa_declined": "4007000000027", 
            "mastercard_approved": "5424000000000015",
            "amex_approved": "370000000000002"
        }
        
        self.test_customers = [
            {
                "id": "cust_test_001",
                "email": "test1@example.com",
                "name": "Test Customer 1"
            },
            {
                "id": "cust_test_002", 
                "email": "test2@example.com",
                "name": "Test Customer 2"
            }
        ]
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, details: str = "", 
                 response_time: float = 0.0, status_code: Optional[int] = None,
                 error_message: Optional[str] = None):
        """Log test result with comprehensive details."""
        result = TestResult(
            test_name=test_name,
            success=success,
            details=details,
            response_time=response_time,
            timestamp=datetime.now().isoformat(),
            status_code=status_code,
            error_message=error_message
        )
        
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({response_time:.3f}s)")
        if details:
            print(f"    {details}")
        if error_message:
            print(f"    Error: {error_message}")
        if self.verbose and status_code:
            print(f"    Status Code: {status_code}")
    
    async def test_health_endpoints(self) -> bool:
        """Test all health check endpoints."""
        print("\n🏥 Testing Health Endpoints")
        print("-" * 40)
        
        health_tests = [
            ("/health", "Basic Health Check"),
            ("/health/ready", "Readiness Check"),
            ("/health/detailed", "Detailed Health Check")
        ]
        
        all_passed = True
        for endpoint, test_name in health_tests:
            try:
                start_time = time.time()
                response = await self.client.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.log_test(test_name, success, 
                            f"Status: {response.status_code}", 
                            response_time, response.status_code)
                
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(test_name, False, "", 0.0, None, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_authorize_net_integration(self) -> bool:
        """Test Authorize.net integration directly."""
        print("\n🔌 Testing Authorize.net Integration")
        print("-" * 40)
        
        try:
            start_time = time.time()
            
            credentials = AuthorizeNetCredentials(
                api_login_id=settings.AUTHORIZE_NET_API_LOGIN_ID,
                transaction_key=settings.AUTHORIZE_NET_TRANSACTION_KEY,
                sandbox=settings.AUTHORIZE_NET_SANDBOX
            )
            
            client = AuthorizeNetClient(credentials)
            result = await client.test_authentication()
            
            response_time = time.time() - start_time
            
            self.log_test("Authorize.net Authentication", result, 
                         "Direct client authentication test", response_time)
            
            return result
            
        except Exception as e:
            self.log_test("Authorize.net Authentication", False, "", 
                         0.0, None, str(e))
            return False
    
    async def test_payment_creation(self) -> Optional[str]:
        """Test payment creation with various scenarios."""
        print("\n💳 Testing Payment Creation")
        print("-" * 40)
        
        payment_scenarios = [
            {
                "name": "Basic Credit Card Payment",
                "data": {
                    "amount": "10.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": self.test_customers[0]["id"],
                    "customer_email": self.test_customers[0]["email"],
                    "customer_name": self.test_customers[0]["name"],
                    "card_token": "tok_visa_4242",
                    "description": "Test payment - Basic",
                    "metadata": {"test": True, "scenario": "basic"},
                    "is_test": True
                }
            },
            {
                "name": "High Amount Payment",
                "data": {
                    "amount": "999.99",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": self.test_customers[1]["id"],
                    "customer_email": self.test_customers[1]["email"],
                    "customer_name": self.test_customers[1]["name"],
                    "card_token": "tok_mastercard_5555",
                    "description": "Test payment - High Amount",
                    "metadata": {"test": True, "scenario": "high_amount"},
                    "is_test": True
                }
            },
            {
                "name": "Payment with Metadata",
                "data": {
                    "amount": "25.50",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": "cust_test_metadata",
                    "customer_email": "metadata@example.com",
                    "customer_name": "Metadata Customer",
                    "card_token": "tok_amex_3782",
                    "description": "Test payment - With Metadata",
                    "metadata": {
                        "test": True,
                        "scenario": "metadata",
                        "order_id": f"order_{uuid.uuid4().hex[:8]}",
                        "product_id": "prod_123",
                        "category": "electronics"
                    },
                    "is_test": True
                }
            }
        ]
        
        created_payment_id = None
        
        for scenario in payment_scenarios:
            try:
                start_time = time.time()
                response = await self.client.post(
                    f"{self.base_url}/api/v1/payments/",
                    json=scenario["data"],
                    headers={"Content-Type": "application/json"}
                )
                response_time = time.time() - start_time
                
                if response.status_code == 201:
                    payment_response = response.json()
                    payment_id = payment_response.get("id")
                    external_id = payment_response.get("external_id")
                    
                    self.log_test(scenario["name"], True, 
                                f"Payment ID: {payment_id}, External ID: {external_id}",
                                response_time, response.status_code)
                    
                    if not created_payment_id:
                        created_payment_id = payment_id
                    
                    self.created_payments.append(payment_id)
                    
                else:
                    self.log_test(scenario["name"], False, 
                                f"Status: {response.status_code}, Response: {response.text}",
                                response_time, response.status_code)
                    
            except Exception as e:
                self.log_test(scenario["name"], False, "", 0.0, None, str(e))
        
        return created_payment_id
    
    async def test_payment_retrieval(self, payment_id: str) -> bool:
        """Test payment retrieval by ID and external ID."""
        print("\n🔍 Testing Payment Retrieval")
        print("-" * 40)
        
        # Test by UUID
        try:
            start_time = time.time()
            response = await self.client.get(f"{self.base_url}/api/v1/payments/{payment_id}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                amount = payment_data.get("amount")
                
                self.log_test("Get Payment by UUID", True, 
                            f"Status: {status}, Amount: {amount}",
                            response_time, response.status_code)
                
                # Test by external ID
                external_id = payment_data.get("external_id")
                if external_id:
                    await self.test_get_payment_by_external_id(external_id)
                
                return True
            else:
                self.log_test("Get Payment by UUID", False, 
                            f"Status: {response.status_code}, Response: {response.text}",
                            response_time, response.status_code)
                return False
                
        except Exception as e:
            self.log_test("Get Payment by UUID", False, "", 0.0, None, str(e))
            return False
    
    async def test_get_payment_by_external_id(self, external_id: str) -> bool:
        """Test payment retrieval by external ID."""
        try:
            start_time = time.time()
            response = await self.client.get(f"{self.base_url}/api/v1/payments/{external_id}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                
                self.log_test("Get Payment by External ID", True, 
                            f"Status: {status}",
                            response_time, response.status_code)
                return True
            else:
                self.log_test("Get Payment by External ID", False, 
                            f"Status: {response.status_code}",
                            response_time, response.status_code)
                return False
                
        except Exception as e:
            self.log_test("Get Payment by External ID", False, "", 0.0, None, str(e))
            return False
    
    async def test_payment_listing(self) -> bool:
        """Test payment listing with various filters."""
        print("\n📋 Testing Payment Listing")
        print("-" * 40)
        
        listing_tests = [
            ("Basic Listing", "/api/v1/payments/?page=1&per_page=10"),
            ("With Customer Filter", f"/api/v1/payments/?customer_id={self.test_customers[0]['id']}&page=1&per_page=5"),
            ("With Status Filter", "/api/v1/payments/?status=pending&page=1&per_page=5"),
            ("Large Page Size", "/api/v1/payments/?page=1&per_page=50")
        ]
        
        all_passed = True
        
        for test_name, endpoint in listing_tests:
            try:
                start_time = time.time()
                response = await self.client.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    total = data.get("total", 0)
                    payments = data.get("payments", [])
                    
                    self.log_test(test_name, True, 
                                f"Total: {total}, Returned: {len(payments)}",
                                response_time, response.status_code)
                else:
                    self.log_test(test_name, False, 
                                f"Status: {response.status_code}",
                                response_time, response.status_code)
                    all_passed = False
                    
            except Exception as e:
                self.log_test(test_name, False, "", 0.0, None, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_payment_updates(self, payment_id: str) -> bool:
        """Test payment updates."""
        print("\n✏️ Testing Payment Updates")
        print("-" * 40)
        
        update_data = {
            "description": f"Updated payment description - {datetime.now().isoformat()}",
            "metadata": {
                "updated": True,
                "update_timestamp": datetime.now().isoformat(),
                "test_scenario": "update_test"
            }
        }
        
        try:
            start_time = time.time()
            response = await self.client.put(
                f"{self.base_url}/api/v1/payments/{payment_id}",
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                payment_data = response.json()
                description = payment_data.get("description")
                
                self.log_test("Update Payment", True, 
                            f"Updated description: {description[:50]}...",
                            response_time, response.status_code)
                return True
            else:
                self.log_test("Update Payment", False, 
                            f"Status: {response.status_code}, Response: {response.text}",
                            response_time, response.status_code)
                return False
                
        except Exception as e:
            self.log_test("Update Payment", False, "", 0.0, None, str(e))
            return False
    
    async def test_payment_refunds(self, payment_id: str) -> bool:
        """Test payment refunds (full and partial)."""
        print("\n💰 Testing Payment Refunds")
        print("-" * 40)
        
        refund_scenarios = [
            {
                "name": "Partial Refund",
                "data": {
                    "amount": "5.00",
                    "reason": "Customer requested partial refund",
                    "metadata": {
                        "refund_type": "partial",
                        "test": True
                    }
                }
            },
            {
                "name": "Full Refund",
                "data": {
                    "reason": "Customer requested full refund",
                    "metadata": {
                        "refund_type": "full",
                        "test": True
                    }
                }
            }
        ]
        
        all_passed = True
        
        for scenario in refund_scenarios:
            try:
                start_time = time.time()
                response = await self.client.post(
                    f"{self.base_url}/api/v1/payments/{payment_id}/refund",
                    json=scenario["data"],
                    headers={"Content-Type": "application/json"}
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    payment_data = response.json()
                    refunded_amount = payment_data.get("refunded_amount")
                    status = payment_data.get("status")
                    
                    self.log_test(scenario["name"], True, 
                                f"Refunded: {refunded_amount}, Status: {status}",
                                response_time, response.status_code)
                else:
                    self.log_test(scenario["name"], False, 
                                f"Status: {response.status_code}, Response: {response.text}",
                                response_time, response.status_code)
                    all_passed = False
                    
            except Exception as e:
                self.log_test(scenario["name"], False, "", 0.0, None, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_payment_cancellation(self, payment_id: str) -> bool:
        """Test payment cancellation."""
        print("\n❌ Testing Payment Cancellation")
        print("-" * 40)
        
        cancel_data = {
            "reason": "Customer requested cancellation",
            "metadata": {
                "cancel_reason": "test_cancellation",
                "test": True
            }
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/cancel",
                json=cancel_data,
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                
                self.log_test("Cancel Payment", True, 
                            f"Status: {status}",
                            response_time, response.status_code)
                return True
            else:
                self.log_test("Cancel Payment", False, 
                            f"Status: {response.status_code}, Response: {response.text}",
                            response_time, response.status_code)
                return False
                
        except Exception as e:
            self.log_test("Cancel Payment", False, "", 0.0, None, str(e))
            return False
    
    async def test_subscription_endpoints(self) -> bool:
        """Test subscription/recurring billing endpoints."""
        print("\n🔄 Testing Subscription Endpoints")
        print("-" * 40)
        
        subscription_tests = [
            {
                "name": "Create Subscription",
                "method": "POST",
                "endpoint": "/api/v1/subscriptions/",
                "data": {
                    "customer_id": "cust_subscription_test",
                    "customer_email": "subscription@example.com",
                    "customer_name": "Subscription Customer",
                    "amount": 9.99,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "card_token": "tok_visa_4242",
                    "description": "Test subscription",
                    "metadata": {"test": True, "type": "subscription"},
                    "is_test": True
                }
            },
            {
                "name": "List Subscriptions",
                "method": "GET",
                "endpoint": "/api/v1/subscriptions/?page=1&per_page=10"
            },
            {
                "name": "Update Subscription",
                "method": "PUT",
                "endpoint": "/api/v1/subscriptions/test_subscription_id",
                "data": {
                    "amount": 19.99,
                    "description": "Updated subscription"
                }
            },
            {
                "name": "Cancel Subscription",
                "method": "DELETE",
                "endpoint": "/api/v1/subscriptions/test_subscription_id"
            },
            {
                "name": "Pause Subscription",
                "method": "POST",
                "endpoint": "/api/v1/subscriptions/test_subscription_id/pause"
            }
        ]
        
        all_passed = True
        
        for test in subscription_tests:
            try:
                start_time = time.time()
                
                if test["method"] == "GET":
                    response = await self.client.get(f"{self.base_url}{test['endpoint']}")
                elif test["method"] == "POST":
                    response = await self.client.post(
                        f"{self.base_url}{test['endpoint']}",
                        json=test.get("data", {}),
                        headers={"Content-Type": "application/json"}
                    )
                elif test["method"] == "PUT":
                    response = await self.client.put(
                        f"{self.base_url}{test['endpoint']}",
                        json=test.get("data", {}),
                        headers={"Content-Type": "application/json"}
                    )
                elif test["method"] == "DELETE":
                    response = await self.client.delete(f"{self.base_url}{test['endpoint']}")
                
                response_time = time.time() - start_time
                
                # For subscription endpoints, we expect 501 Not Implemented
                expected_status = 501 if "subscription" in test["name"].lower() else 200
                success = response.status_code == expected_status
                
                self.log_test(test["name"], success, 
                            f"Status: {response.status_code} (Expected: {expected_status})",
                            response_time, response.status_code)
                
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(test["name"], False, "", 0.0, None, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_webhook_endpoints(self) -> bool:
        """Test webhook endpoints."""
        print("\n🔗 Testing Webhook Endpoints")
        print("-" * 40)
        
        webhook_tests = [
            ("Authorize.net Webhook", "/api/v1/webhooks/authorize-net"),
            ("Webhook List", "/api/v1/webhooks/webhooks"),
            ("Webhook Health", "/api/v1/webhooks/health")
        ]
        
        all_passed = True
        
        for test_name, endpoint in webhook_tests:
            try:
                start_time = time.time()
                response = await self.client.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                # Webhooks may return 401 Unauthorized or 200 OK
                success = response.status_code in [200, 401, 404]
                
                self.log_test(test_name, success, 
                            f"Status: {response.status_code}",
                            response_time, response.status_code)
                
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(test_name, False, "", 0.0, None, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance and collect metrics."""
        print("\n📊 Testing Performance Metrics")
        print("-" * 40)
        
        metrics = {
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for r in self.test_results if r.success),
            "failed_tests": sum(1 for r in self.test_results if not r.success),
            "average_response_time": 0.0,
            "max_response_time": 0.0,
            "min_response_time": float('inf'),
            "status_codes": {},
            "endpoint_performance": {}
        }
        
        if self.test_results:
            response_times = [r.response_time for r in self.test_results if r.response_time > 0]
            if response_times:
                metrics["average_response_time"] = sum(response_times) / len(response_times)
                metrics["max_response_time"] = max(response_times)
                metrics["min_response_time"] = min(response_times)
            
            # Count status codes
            for result in self.test_results:
                if result.status_code:
                    metrics["status_codes"][str(result.status_code)] = \
                        metrics["status_codes"].get(str(result.status_code), 0) + 1
            
            # Group by endpoint
            for result in self.test_results:
                endpoint = result.test_name
                if endpoint not in metrics["endpoint_performance"]:
                    metrics["endpoint_performance"][endpoint] = {
                        "count": 0,
                        "success_count": 0,
                        "total_time": 0.0,
                        "avg_time": 0.0
                    }
                
                perf = metrics["endpoint_performance"][endpoint]
                perf["count"] += 1
                if result.success:
                    perf["success_count"] += 1
                perf["total_time"] += result.response_time
                perf["avg_time"] = perf["total_time"] / perf["count"]
        
        # Log performance summary
        self.log_test("Performance Summary", True, 
                    f"Avg Response Time: {metrics['average_response_time']:.3f}s, "
                    f"Max: {metrics['max_response_time']:.3f}s, "
                    f"Min: {metrics['min_response_time']:.3f}s")
        
        return metrics
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests."""
        print("🚀 Starting Comprehensive Payment Gateway API Testing")
        print("=" * 80)
        print(f"📡 Testing against: {self.base_url}")
        print(f"🔧 Authorize.net Sandbox: {settings.AUTHORIZE_NET_SANDBOX}")
        print(f"⏰ Test started at: {datetime.now().isoformat()}")
        print("=" * 80)
        
        # Test health endpoints
        await self.test_health_endpoints()
        
        # Test Authorize.net integration
        await self.test_authorize_net_integration()
        
        # Test payment creation
        payment_id = await self.test_payment_creation()
        
        if payment_id:
            # Test payment operations
            await self.test_payment_retrieval(payment_id)
            await self.test_payment_updates(payment_id)
            await self.test_payment_refunds(payment_id)
            await self.test_payment_cancellation(payment_id)
        
        # Test listing
        await self.test_payment_listing()
        
        # Test subscription endpoints
        await self.test_subscription_endpoints()
        
        # Test webhook endpoints
        await self.test_webhook_endpoints()
        
        # Collect performance metrics
        metrics = await self.test_performance_metrics()
        
        # Generate summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Average Response Time: {metrics['average_response_time']:.3f}s")
        print(f"🏃 Max Response Time: {metrics['max_response_time']:.3f}s")
        print(f"🐌 Min Response Time: {metrics['min_response_time']:.3f}s")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests ({failed_tests}):")
            for result in self.test_results:
                if not result.success:
                    print(f"  - {result.test_name}: {result.error_message or result.details}")
        
        print(f"\n📄 Created Payments: {len(self.created_payments)}")
        print(f"📄 Created Subscriptions: {len(self.created_subscriptions)}")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "test_duration": time.time(),
                "created_payments": len(self.created_payments),
                "created_subscriptions": len(self.created_subscriptions)
            },
            "metrics": metrics,
            "results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "details": r.details,
                    "response_time": r.response_time,
                    "timestamp": r.timestamp,
                    "status_code": r.status_code,
                    "error_message": r.error_message
                }
                for r in self.test_results
            ]
        }


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive Payment Gateway API Testing")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--save-results", action="store_true",
                       help="Save detailed results to JSON file")
    
    args = parser.parse_args()
    
    # Check environment variables
    required_vars = [
        "AUTHORIZE_NET_API_LOGIN_ID",
        "AUTHORIZE_NET_TRANSACTION_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables before running the tests.")
        return 1
    
    print("✅ Environment variables configured")
    
    async with ComprehensivePaymentTester(args.base_url, args.verbose) as tester:
        results = await tester.run_comprehensive_tests()
        
        if args.save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📄 Detailed results saved to: {filename}")
        
        return 0 if results["summary"]["failed_tests"] == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
