#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Quick Payment Test Script

This script provides a quick way to test basic payment gateway operations:
- Create Payment
- Cancel Payment  
- Refund Payment
- Create Subscription

Usage:
    python scripts/quick_payment_test.py [--base-url BASE_URL] [--api-key API_KEY]
"""

import asyncio
import json
import random
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import argparse
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import httpx
from httpx import AsyncClient, Response
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuickPaymentTester:
    """Quick payment gateway tester for basic operations."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """Initialize the quick payment tester."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = None
        self.session_id = str(uuid.uuid4())
        
        # Store created resources
        self.created_payment = None
        self.created_subscription = None
        
        # Test JWT token for development
        self.test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJleHAiOjE3NTgzOTA3MDMsImlhdCI6MTc1ODM4NzEwMywianRpIjoidGVzdF90b2tlbl8xMjMiLCJrZXlfaWQiOiJ0ZXN0X2tleV8xMjMiLCJwZXJtaXNzaW9ucyI6WyJwYXltZW50czpyZWFkIiwicGF5bWVudHM6d3JpdGUiLCJwYXltZW50czpkZWxldGUiLCJ3ZWJob29rczpyZWFkIiwid2ViaG9va3M6d3JpdGUiLCJhZG1pbjpyZWFkIiwiYWRtaW46d3JpdGUiXSwiaXNfYWRtaW4iOnRydWV9.Ejgal5Mo4EvJ1Sl7zkm_La2DLpaSIUeuo7WKa0csx-8"
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": self.session_id,
                "User-Agent": "EasyPay-QuickTest/1.0"
            }
        )
        
        # Add API key if provided, otherwise use test token
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Use test token for development
            self.client.headers["Authorization"] = f"Bearer {self.test_token}"
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Response:
        """Make HTTP request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await self.client.get(url)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data)
            elif method.upper() == "PUT":
                response = await self.client.put(url, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
            
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    async def test_health(self) -> bool:
        """Test API health endpoint."""
        logger.info("🔍 Testing API Health...")
        
        try:
            response = await self._make_request("GET", "/health")
            if response.status_code == 200:
                logger.info("✅ API is healthy")
                return True
            else:
                logger.error(f"❌ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return False
    
    async def create_payment(self) -> bool:
        """Create a test payment."""
        logger.info("💳 Creating Test Payment...")
        
        payment_data = {
            "amount": "25.99",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": f"cust_test_{random.randint(100000, 999999)}",
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "card_token": "tok_visa_4242",
            "description": "Quick test payment",
            "metadata": {
                "test": True,
                "session_id": self.session_id
            },
            "is_test": True
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/payments", payment_data)
            
            if response.status_code in [200, 201]:
                self.created_payment = response.json()
                logger.info(f"✅ Payment created successfully: {self.created_payment.get('id')}")
                return True
            else:
                logger.error(f"❌ Payment creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Payment creation failed: {str(e)}")
            return False
    
    async def cancel_payment(self) -> bool:
        """Cancel the created payment."""
        if not self.created_payment:
            logger.warning("⚠️ No payment to cancel")
            return False
        
        logger.info("❌ Cancelling Payment...")
        
        payment_id = self.created_payment.get("id")
        cancel_data = {
            "reason": "Test cancellation",
            "metadata": {
                "test": True,
                "cancelled_by": "quick_test"
            }
        }
        
        try:
            response = await self._make_request("POST", f"/api/v1/payments/{payment_id}/cancel", cancel_data)
            
            if response.status_code == 200:
                logger.info("✅ Payment cancelled successfully")
                return True
            else:
                logger.error(f"❌ Payment cancellation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Payment cancellation failed: {str(e)}")
            return False
    
    async def refund_payment(self) -> bool:
        """Refund the created payment."""
        if not self.created_payment:
            logger.warning("⚠️ No payment to refund")
            return False
        
        logger.info("💰 Refunding Payment...")
        
        payment_id = self.created_payment.get("id")
        refund_data = {
            "reason": "Test refund",
            "metadata": {
                "test": True,
                "refunded_by": "quick_test"
            }
        }
        
        try:
            response = await self._make_request("POST", f"/api/v1/payments/{payment_id}/refund", refund_data)
            
            if response.status_code == 200:
                logger.info("✅ Payment refunded successfully")
                return True
            else:
                logger.error(f"❌ Payment refund failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Payment refund failed: {str(e)}")
            return False
    
    async def create_subscription(self) -> bool:
        """Create a test subscription."""
        logger.info("🔄 Creating Test Subscription...")
        
        subscription_data = {
            "customer_id": f"sub_cust_test_{random.randint(100000, 999999)}",
            "customer_email": "subscriber@example.com",
            "customer_name": "Test Subscriber",
            "amount": 29.99,
            "currency": "USD",
            "interval": "monthly",
            "interval_count": 1,
            "card_token": "tok_visa_4242",
            "description": "Quick test subscription",
            "metadata": {
                "test": True,
                "session_id": self.session_id
            },
            "is_test": True
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/subscriptions", subscription_data)
            
            if response.status_code in [200, 201]:
                self.created_subscription = response.json()
                logger.info(f"✅ Subscription created successfully: {self.created_subscription.get('id')}")
                return True
            else:
                logger.error(f"❌ Subscription creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Subscription creation failed: {str(e)}")
            return False
    
    async def cancel_subscription(self) -> bool:
        """Cancel the created subscription."""
        if not self.created_subscription:
            logger.warning("⚠️ No subscription to cancel")
            return False
        
        logger.info("❌ Cancelling Subscription...")
        
        subscription_id = self.created_subscription.get("id")
        
        try:
            response = await self._make_request("POST", f"/api/v1/subscriptions/{subscription_id}/cancel")
            
            if response.status_code == 200:
                logger.info("✅ Subscription cancelled successfully")
                return True
            else:
                logger.error(f"❌ Subscription cancellation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Subscription cancellation failed: {str(e)}")
            return False
    
    async def list_payments(self) -> bool:
        """List payments."""
        logger.info("📋 Listing Payments...")
        
        try:
            response = await self._make_request("GET", "/api/v1/payments")
            
            if response.status_code == 200:
                payments_data = response.json()
                payment_count = len(payments_data.get("payments", []))
                logger.info(f"✅ Retrieved {payment_count} payments")
                return True
            else:
                logger.error(f"❌ Payment listing failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Payment listing failed: {str(e)}")
            return False
    
    async def list_subscriptions(self) -> bool:
        """List subscriptions."""
        logger.info("📋 Listing Subscriptions...")
        
        try:
            response = await self._make_request("GET", "/api/v1/subscriptions")
            
            if response.status_code == 200:
                subscriptions_data = response.json()
                subscription_count = len(subscriptions_data.get("subscriptions", []))
                logger.info(f"✅ Retrieved {subscription_count} subscriptions")
                return True
            else:
                logger.error(f"❌ Subscription listing failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Subscription listing failed: {str(e)}")
            return False
    
    async def run_quick_test(self) -> Dict[str, Any]:
        """Run quick payment gateway test."""
        logger.info("🚀 Starting Quick Payment Gateway Test")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info("=" * 50)
        
        results = {
            "session_id": self.session_id,
            "base_url": self.base_url,
            "tests": {},
            "created_resources": {}
        }
        
        # Test health
        results["tests"]["health"] = await self.test_health()
        
        # Test payment operations
        results["tests"]["create_payment"] = await self.create_payment()
        if self.created_payment:
            results["created_resources"]["payment"] = self.created_payment
        
        results["tests"]["cancel_payment"] = await self.cancel_payment()
        results["tests"]["refund_payment"] = await self.refund_payment()
        
        # Test subscription operations
        results["tests"]["create_subscription"] = await self.create_subscription()
        if self.created_subscription:
            results["created_resources"]["subscription"] = self.created_subscription
        
        results["tests"]["cancel_subscription"] = await self.cancel_subscription()
        
        # Test listing operations
        results["tests"]["list_payments"] = await self.list_payments()
        results["tests"]["list_subscriptions"] = await self.list_subscriptions()
        
        # Calculate success rate
        total_tests = len(results["tests"])
        passed_tests = sum(1 for success in results["tests"].values() if success)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        results["success_rate"] = success_rate
        
        # Print summary
        logger.info("=" * 50)
        logger.info("📊 QUICK TEST COMPLETE")
        logger.info("=" * 50)
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        logger.info("\nTest Results:")
        for test_name, success in results["tests"].items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        if results["created_resources"]:
            logger.info(f"\nCreated Resources:")
            for resource_type, resource_data in results["created_resources"].items():
                logger.info(f"  {resource_type}: {resource_data.get('id', 'N/A')}")
        
        return results


async def main():
    """Main function to run the quick payment test."""
    parser = argparse.ArgumentParser(description="EasyPay Quick Payment Test")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL of the EasyPay API")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        async with QuickPaymentTester(args.base_url, args.api_key) as tester:
            results = await tester.run_quick_test()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}")
            
            # Exit with appropriate code
            if results["success_rate"] >= 80:
                logger.info("🎉 Quick test completed successfully!")
                sys.exit(0)
            else:
                logger.warning("⚠️ Quick test completed with some failures")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
