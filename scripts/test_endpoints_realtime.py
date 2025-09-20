#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Real-Time Endpoint Testing Script

This script tests all payment endpoints with the Authorize.net sandbox integration.
Run this script to verify that all endpoints are working correctly.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    AuthorizeNetCredentials, CreditCard, BillingAddress
)
from src.core.config import settings


class EndpointTester:
    """Test all payment endpoints with real Authorize.net sandbox."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    async def test_health_endpoint(self) -> bool:
        """Test health endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            success = response.status_code == 200
            self.log_test("Health Check", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False
    
    async def test_authorize_net_direct(self) -> bool:
        """Test Authorize.net client directly."""
        try:
            credentials = AuthorizeNetCredentials(
                api_login_id=settings.AUTHORIZE_NET_API_LOGIN_ID,
                transaction_key=settings.AUTHORIZE_NET_TRANSACTION_KEY,
                sandbox=settings.AUTHORIZE_NET_SANDBOX
            )
            
            client = AuthorizeNetClient(credentials)
            result = await client.test_authentication()
            
            self.log_test("Authorize.net Authentication", result, "Direct client test")
            return result
        except Exception as e:
            self.log_test("Authorize.net Authentication", False, f"Error: {str(e)}")
            return False
    
    async def test_create_payment(self) -> Optional[str]:
        """Test payment creation endpoint."""
        try:
            payment_data = {
                "amount": "10.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "test_customer_001",
                "customer_email": "test@example.com",
                "customer_name": "Test Customer",
                "card_token": "tok_visa_4242",
                "description": "Test payment",
                "metadata": {
                    "order_id": "test_order_001",
                    "test": True
                },
                "is_test": True
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/",
                json=payment_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                payment_response = response.json()
                payment_id = payment_response.get("id")
                self.log_test("Create Payment", True, f"Payment ID: {payment_id}")
                return payment_id
            else:
                self.log_test("Create Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Create Payment", False, f"Error: {str(e)}")
            return None
    
    async def test_authorize_payment(self) -> Optional[str]:
        """Test payment authorization endpoint."""
        try:
            payment_data = {
                "amount": "15.00",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "test_customer_002",
                "customer_email": "test2@example.com",
                "customer_name": "Test Customer 2",
                "card_token": "tok_mastercard_5555",
                "description": "Test authorization",
                "metadata": {
                    "order_id": "test_order_002",
                    "test": True
                },
                "is_test": True
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/authorize",
                json=payment_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                payment_response = response.json()
                payment_id = payment_response.get("id")
                self.log_test("Authorize Payment", True, f"Payment ID: {payment_id}")
                return payment_id
            else:
                self.log_test("Authorize Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Authorize Payment", False, f"Error: {str(e)}")
            return None
    
    async def test_get_payment(self, payment_id: str) -> bool:
        """Test get payment endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/payments/{payment_id}")
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                self.log_test("Get Payment", True, f"Status: {status}")
                return True
            else:
                self.log_test("Get Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Payment", False, f"Error: {str(e)}")
            return False
    
    async def test_capture_payment(self, payment_id: str) -> bool:
        """Test payment capture endpoint."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/capture",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                self.log_test("Capture Payment", True, f"Status: {status}")
                return True
            else:
                self.log_test("Capture Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Capture Payment", False, f"Error: {str(e)}")
            return False
    
    async def test_refund_payment(self, payment_id: str) -> bool:
        """Test payment refund endpoint."""
        try:
            refund_data = {
                "amount": "5.00",
                "reason": "Test refund",
                "metadata": {
                    "refund_reason": "test"
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/refund",
                json=refund_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                refunded_amount = payment_data.get("refunded_amount")
                self.log_test("Refund Payment", True, f"Refunded: {refunded_amount}")
                return True
            else:
                self.log_test("Refund Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Refund Payment", False, f"Error: {str(e)}")
            return False
    
    async def test_cancel_payment(self, payment_id: str) -> bool:
        """Test payment cancellation endpoint."""
        try:
            cancel_data = {
                "reason": "Test cancellation",
                "metadata": {
                    "cancel_reason": "test"
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/cancel",
                json=cancel_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                status = payment_data.get("status")
                self.log_test("Cancel Payment", True, f"Status: {status}")
                return True
            else:
                self.log_test("Cancel Payment", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Cancel Payment", False, f"Error: {str(e)}")
            return False
    
    async def test_list_payments(self) -> bool:
        """Test list payments endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/payments/?page=1&per_page=10")
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                self.log_test("List Payments", True, f"Total payments: {total}")
                return True
            else:
                self.log_test("List Payments", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("List Payments", False, f"Error: {str(e)}")
            return False
    
    async def test_subscription_endpoints(self) -> bool:
        """Test subscription endpoints (should return 501 Not Implemented)."""
        try:
            # Test create subscription
            subscription_data = {
                "customer_id": "test_customer_sub",
                "customer_email": "subscription@example.com",
                "customer_name": "Subscription Customer",
                "amount": 9.99,
                "currency": "USD",
                "interval": "monthly",
                "interval_count": 1,
                "card_token": "tok_visa_4242",
                "description": "Test subscription",
                "is_test": True
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions/",
                json=subscription_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 501 Not Implemented
            if response.status_code == 501:
                self.log_test("Subscription Endpoints", True, "Correctly returns 501 Not Implemented")
                return True
            else:
                self.log_test("Subscription Endpoints", False, f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Subscription Endpoints", False, f"Error: {str(e)}")
            return False
    
    async def test_webhook_endpoints(self) -> bool:
        """Test webhook endpoints."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/webhooks/webhooks")
            
            # Should return 401 Unauthorized or 200 OK
            if response.status_code in [200, 401]:
                self.log_test("Webhook Endpoints", True, f"Status: {response.status_code}")
                return True
            else:
                self.log_test("Webhook Endpoints", False, f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Webhook Endpoints", False, f"Error: {str(e)}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all endpoint tests."""
        print("🚀 Starting EasyPay Payment Gateway Endpoint Tests")
        print("=" * 60)
        
        # Test basic connectivity
        await self.test_health_endpoint()
        
        # Test Authorize.net integration
        await self.test_authorize_net_direct()
        
        # Test payment endpoints
        payment_id = await self.test_create_payment()
        if payment_id:
            await self.test_get_payment(payment_id)
            await self.test_refund_payment(payment_id)
        
        # Test authorization flow
        auth_payment_id = await self.test_authorize_payment()
        if auth_payment_id:
            await self.test_get_payment(auth_payment_id)
            await self.test_capture_payment(auth_payment_id)
        
        # Test other endpoints
        await self.test_list_payments()
        await self.test_subscription_endpoints()
        await self.test_webhook_endpoints()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "results": self.test_results
        }


async def main():
    """Main test function."""
    print("EasyPay Payment Gateway - Real-Time Endpoint Testing")
    print("=" * 60)
    
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
    print(f"📡 Testing against: http://localhost:8000")
    print(f"🔧 Authorize.net Sandbox: {os.getenv('AUTHORIZE_NET_SANDBOX', 'True')}")
    print()
    
    async with EndpointTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: test_results.json")
        
        return 0 if results["failed_tests"] == 0 else 1


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
