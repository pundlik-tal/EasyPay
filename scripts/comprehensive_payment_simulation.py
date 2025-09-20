#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Comprehensive Payment Actions Simulation

This script simulates all payment gateway actions including:
- Purchase/Payment Creation
- Cancel Payment
- Refund Payment (Full & Partial)
- Subscription/Recurring Billing Management
- Additional Actions (Webhooks, Status Updates, etc.)

Usage:
    python scripts/comprehensive_payment_simulation.py [--base-url BASE_URL] [--api-key API_KEY]
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaymentGatewaySimulator:
    """
    Comprehensive payment gateway simulator for testing all payment actions.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """
        Initialize the payment gateway simulator.
        
        Args:
            base_url: Base URL of the EasyPay API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = None
        self.session_id = str(uuid.uuid4())
        
        # Test data storage
        self.created_payments: List[Dict[str, Any]] = []
        self.created_subscriptions: List[Dict[str, Any]] = []
        self.test_results: Dict[str, Any] = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": self.session_id,
                "User-Agent": "EasyPay-Simulator/1.0"
            }
        )
        
        # Add API key if provided
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result and update statistics."""
        self.test_results["total_tests"] += 1
        if success:
            self.test_results["passed"] += 1
            logger.info(f"✅ {test_name}: PASSED {details}")
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {details}")
            logger.error(f"❌ {test_name}: FAILED {details}")
    
    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Response:
        """Make HTTP request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"Making {method} request to {url}")
            
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
            
            logger.debug(f"Response status: {response.status_code}")
            return response
            
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    async def test_authentication(self) -> bool:
        """Test API authentication."""
        logger.info("🔐 Testing Authentication...")
        
        try:
            # Test health endpoint (no auth required)
            response = await self._make_request("GET", "/health")
            if response.status_code == 200:
                self._log_test_result("Health Check", True)
            else:
                self._log_test_result("Health Check", False, f"Status: {response.status_code}")
                return False
            
            # Test authenticated endpoint
            response = await self._make_request("GET", "/api/v1/payments")
            if response.status_code in [200, 401, 403]:
                self._log_test_result("Authentication", True, f"Status: {response.status_code}")
                return True
            else:
                self._log_test_result("Authentication", False, f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self._log_test_result("Authentication", False, str(e))
            return False
    
    async def simulate_purchase_creation(self) -> Optional[Dict[str, Any]]:
        """Simulate payment/purchase creation with various scenarios."""
        logger.info("💳 Simulating Purchase/Payment Creation...")
        
        test_scenarios = [
            {
                "name": "Basic Credit Card Payment",
                "data": {
                    "amount": "25.99",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_{random.randint(100000, 999999)}",
                    "customer_email": "john.doe@example.com",
                    "customer_name": "John Doe",
                    "card_token": "tok_visa_4242",
                    "description": "Test payment for simulation",
                    "metadata": {
                        "order_id": f"order_{random.randint(1000, 9999)}",
                        "product": "test_product",
                        "simulation": True
                    },
                    "is_test": True
                }
            },
            {
                "name": "High-Value Payment",
                "data": {
                    "amount": "999.99",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_enterprise_{random.randint(100, 999)}",
                    "customer_email": "enterprise@company.com",
                    "customer_name": "Enterprise Customer",
                    "card_token": "tok_amex_1234",
                    "description": "Enterprise license purchase",
                    "metadata": {
                        "order_id": f"enterprise_{random.randint(1000, 9999)}",
                        "product": "enterprise_license",
                        "simulation": True
                    },
                    "is_test": True
                }
            },
            {
                "name": "International Payment",
                "data": {
                    "amount": "150.00",
                    "currency": "EUR",
                    "payment_method": "credit_card",
                    "customer_id": f"cust_intl_{random.randint(100, 999)}",
                    "customer_email": "international@example.com",
                    "customer_name": "International Customer",
                    "card_token": "tok_mastercard_5555",
                    "description": "International payment test",
                    "metadata": {
                        "order_id": f"intl_{random.randint(1000, 9999)}",
                        "country": "DE",
                        "simulation": True
                    },
                    "is_test": True
                }
            }
        ]
        
        created_payments = []
        
        for scenario in test_scenarios:
            try:
                logger.info(f"  Creating {scenario['name']}...")
                response = await self._make_request("POST", "/api/v1/payments", scenario["data"])
                
                if response.status_code == 201:
                    payment_data = response.json()
                    created_payments.append(payment_data)
                    self.created_payments.append(payment_data)
                    self._log_test_result(f"Payment Creation - {scenario['name']}", True, 
                                        f"Payment ID: {payment_data.get('id', 'N/A')}")
                else:
                    error_detail = response.text
                    self._log_test_result(f"Payment Creation - {scenario['name']}", False, 
                                        f"Status: {response.status_code}, Error: {error_detail}")
                    
            except Exception as e:
                self._log_test_result(f"Payment Creation - {scenario['name']}", False, str(e))
        
        return created_payments[0] if created_payments else None
    
    async def simulate_payment_cancellation(self, payment_id: str = None) -> bool:
        """Simulate payment cancellation."""
        logger.info("❌ Simulating Payment Cancellation...")
        
        if not payment_id and self.created_payments:
            payment_id = self.created_payments[0].get("id")
        
        if not payment_id:
            self._log_test_result("Payment Cancellation", False, "No payment ID available")
            return False
        
        try:
            cancel_data = {
                "reason": "Customer requested cancellation",
                "metadata": {
                    "cancelled_by": "simulation",
                    "cancellation_type": "customer_request"
                }
            }
            
            response = await self._make_request("POST", f"/api/v1/payments/{payment_id}/cancel", cancel_data)
            
            if response.status_code == 200:
                payment_data = response.json()
                self._log_test_result("Payment Cancellation", True, 
                                    f"Payment {payment_id} cancelled successfully")
                return True
            else:
                error_detail = response.text
                self._log_test_result("Payment Cancellation", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
                return False
                
        except Exception as e:
            self._log_test_result("Payment Cancellation", False, str(e))
            return False
    
    async def simulate_payment_refund(self, payment_id: str = None, refund_type: str = "full") -> bool:
        """Simulate payment refund (full or partial)."""
        logger.info(f"💰 Simulating Payment Refund ({refund_type})...")
        
        if not payment_id and self.created_payments:
            payment_id = self.created_payments[0].get("id")
        
        if not payment_id:
            self._log_test_result("Payment Refund", False, "No payment ID available")
            return False
        
        try:
            refund_data = {
                "reason": "Customer requested refund",
                "metadata": {
                    "refund_type": refund_type,
                    "refunded_by": "simulation"
                }
            }
            
            # Add partial refund amount if needed
            if refund_type == "partial":
                refund_data["amount"] = "10.00"  # Partial refund amount
            
            response = await self._make_request("POST", f"/api/v1/payments/{payment_id}/refund", refund_data)
            
            if response.status_code == 200:
                payment_data = response.json()
                self._log_test_result(f"Payment Refund ({refund_type})", True, 
                                    f"Payment {payment_id} refunded successfully")
                return True
            else:
                error_detail = response.text
                self._log_test_result(f"Payment Refund ({refund_type})", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
                return False
                
        except Exception as e:
            self._log_test_result(f"Payment Refund ({refund_type})", False, str(e))
            return False
    
    async def simulate_subscription_creation(self) -> Optional[Dict[str, Any]]:
        """Simulate subscription/recurring billing creation."""
        logger.info("🔄 Simulating Subscription Creation...")
        
        subscription_scenarios = [
            {
                "name": "Monthly Subscription",
                "data": {
                    "customer_id": f"sub_cust_{random.randint(100000, 999999)}",
                    "customer_email": "subscriber@example.com",
                    "customer_name": "Subscription Customer",
                    "amount": 29.99,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "card_token": "tok_visa_4242",
                    "description": "Monthly premium subscription",
                    "metadata": {
                        "plan": "premium_monthly",
                        "simulation": True
                    },
                    "is_test": True
                }
            },
            {
                "name": "Yearly Subscription with Trial",
                "data": {
                    "customer_id": f"sub_cust_yearly_{random.randint(100, 999)}",
                    "customer_email": "yearly@example.com",
                    "customer_name": "Yearly Subscriber",
                    "amount": 299.99,
                    "currency": "USD",
                    "interval": "yearly",
                    "interval_count": 1,
                    "trial_period_days": 14,
                    "card_token": "tok_amex_1234",
                    "description": "Yearly subscription with 14-day trial",
                    "metadata": {
                        "plan": "premium_yearly",
                        "trial": True,
                        "simulation": True
                    },
                    "is_test": True
                }
            },
            {
                "name": "Weekly Subscription",
                "data": {
                    "customer_id": f"sub_cust_weekly_{random.randint(100, 999)}",
                    "customer_email": "weekly@example.com",
                    "customer_name": "Weekly Subscriber",
                    "amount": 9.99,
                    "currency": "USD",
                    "interval": "weekly",
                    "interval_count": 1,
                    "card_token": "tok_mastercard_5555",
                    "description": "Weekly subscription",
                    "metadata": {
                        "plan": "basic_weekly",
                        "simulation": True
                    },
                    "is_test": True
                }
            }
        ]
        
        created_subscriptions = []
        
        for scenario in subscription_scenarios:
            try:
                logger.info(f"  Creating {scenario['name']}...")
                response = await self._make_request("POST", "/api/v1/subscriptions", scenario["data"])
                
                if response.status_code == 201:
                    subscription_data = response.json()
                    created_subscriptions.append(subscription_data)
                    self.created_subscriptions.append(subscription_data)
                    self._log_test_result(f"Subscription Creation - {scenario['name']}", True, 
                                        f"Subscription ID: {subscription_data.get('id', 'N/A')}")
                else:
                    error_detail = response.text
                    self._log_test_result(f"Subscription Creation - {scenario['name']}", False, 
                                        f"Status: {response.status_code}, Error: {error_detail}")
                    
            except Exception as e:
                self._log_test_result(f"Subscription Creation - {scenario['name']}", False, str(e))
        
        return created_subscriptions[0] if created_subscriptions else None
    
    async def simulate_subscription_management(self, subscription_id: str = None) -> bool:
        """Simulate subscription management operations."""
        logger.info("🔧 Simulating Subscription Management...")
        
        if not subscription_id and self.created_subscriptions:
            subscription_id = self.created_subscriptions[0].get("id")
        
        if not subscription_id:
            self._log_test_result("Subscription Management", False, "No subscription ID available")
            return False
        
        success_count = 0
        total_operations = 0
        
        # Test subscription update
        try:
            total_operations += 1
            update_data = {
                "amount": 39.99,
                "description": "Updated subscription amount",
                "metadata": {
                    "updated_by": "simulation",
                    "update_reason": "price_increase"
                }
            }
            
            response = await self._make_request("PUT", f"/api/v1/subscriptions/{subscription_id}", update_data)
            
            if response.status_code == 200:
                self._log_test_result("Subscription Update", True, "Subscription updated successfully")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Subscription Update", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Subscription Update", False, str(e))
        
        # Test subscription cancellation
        try:
            total_operations += 1
            response = await self._make_request("POST", f"/api/v1/subscriptions/{subscription_id}/cancel")
            
            if response.status_code == 200:
                self._log_test_result("Subscription Cancellation", True, "Subscription cancelled successfully")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Subscription Cancellation", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Subscription Cancellation", False, str(e))
        
        # Test subscription resume (if cancellation was successful)
        try:
            total_operations += 1
            response = await self._make_request("POST", f"/api/v1/subscriptions/{subscription_id}/resume")
            
            if response.status_code == 200:
                self._log_test_result("Subscription Resume", True, "Subscription resumed successfully")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Subscription Resume", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Subscription Resume", False, str(e))
        
        return success_count > 0
    
    async def simulate_additional_actions(self) -> bool:
        """Simulate additional payment gateway actions."""
        logger.info("🔍 Simulating Additional Actions...")
        
        success_count = 0
        total_operations = 0
        
        # Test payment listing
        try:
            total_operations += 1
            response = await self._make_request("GET", "/api/v1/payments")
            
            if response.status_code == 200:
                payments_data = response.json()
                payment_count = len(payments_data.get("payments", []))
                self._log_test_result("Payment Listing", True, f"Retrieved {payment_count} payments")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Payment Listing", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Payment Listing", False, str(e))
        
        # Test subscription listing
        try:
            total_operations += 1
            response = await self._make_request("GET", "/api/v1/subscriptions")
            
            if response.status_code == 200:
                subscriptions_data = response.json()
                subscription_count = len(subscriptions_data.get("subscriptions", []))
                self._log_test_result("Subscription Listing", True, f"Retrieved {subscription_count} subscriptions")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Subscription Listing", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Subscription Listing", False, str(e))
        
        # Test payment retrieval by ID
        if self.created_payments:
            try:
                total_operations += 1
                payment_id = self.created_payments[0].get("id")
                response = await self._make_request("GET", f"/api/v1/payments/{payment_id}")
                
                if response.status_code == 200:
                    payment_data = response.json()
                    self._log_test_result("Payment Retrieval", True, f"Retrieved payment {payment_id}")
                    success_count += 1
                else:
                    error_detail = response.text
                    self._log_test_result("Payment Retrieval", False, 
                                        f"Status: {response.status_code}, Error: {error_detail}")
            except Exception as e:
                self._log_test_result("Payment Retrieval", False, str(e))
        
        # Test webhook endpoint (if available)
        try:
            total_operations += 1
            webhook_data = {
                "event_type": "payment.created",
                "payment_id": self.created_payments[0].get("id") if self.created_payments else "test_payment",
                "data": {
                    "amount": "25.99",
                    "currency": "USD",
                    "status": "completed"
                }
            }
            
            response = await self._make_request("POST", "/api/v1/webhooks/payments", webhook_data)
            
            if response.status_code in [200, 201]:
                self._log_test_result("Webhook Processing", True, "Webhook processed successfully")
                success_count += 1
            else:
                error_detail = response.text
                self._log_test_result("Webhook Processing", False, 
                                    f"Status: {response.status_code}, Error: {error_detail}")
        except Exception as e:
            self._log_test_result("Webhook Processing", False, str(e))
        
        return success_count > 0
    
    async def simulate_error_scenarios(self) -> bool:
        """Simulate error scenarios and edge cases."""
        logger.info("⚠️ Simulating Error Scenarios...")
        
        success_count = 0
        total_operations = 0
        
        # Test invalid payment creation
        try:
            total_operations += 1
            invalid_data = {
                "amount": "-10.00",  # Invalid negative amount
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "test_customer",
                "customer_email": "invalid-email",  # Invalid email format
                "customer_name": "Test Customer",
                "card_token": "invalid_token",
                "is_test": True
            }
            
            response = await self._make_request("POST", "/api/v1/payments", invalid_data)
            
            if response.status_code == 400:  # Expected validation error
                self._log_test_result("Invalid Payment Creation", True, "Correctly rejected invalid data")
                success_count += 1
            else:
                self._log_test_result("Invalid Payment Creation", False, 
                                    f"Expected 400, got {response.status_code}")
        except Exception as e:
            self._log_test_result("Invalid Payment Creation", False, str(e))
        
        # Test non-existent payment operations
        try:
            total_operations += 1
            fake_payment_id = str(uuid.uuid4())
            response = await self._make_request("GET", f"/api/v1/payments/{fake_payment_id}")
            
            if response.status_code == 404:  # Expected not found error
                self._log_test_result("Non-existent Payment", True, "Correctly returned 404")
                success_count += 1
            else:
                self._log_test_result("Non-existent Payment", False, 
                                    f"Expected 404, got {response.status_code}")
        except Exception as e:
            self._log_test_result("Non-existent Payment", False, str(e))
        
        # Test unauthorized access
        try:
            total_operations += 1
            # Temporarily remove auth header
            original_auth = self.client.headers.get("Authorization")
            if original_auth:
                del self.client.headers["Authorization"]
            
            response = await self._make_request("GET", "/api/v1/payments")
            
            # Restore auth header
            if original_auth:
                self.client.headers["Authorization"] = original_auth
            
            if response.status_code == 401:  # Expected unauthorized error
                self._log_test_result("Unauthorized Access", True, "Correctly returned 401")
                success_count += 1
            else:
                self._log_test_result("Unauthorized Access", False, 
                                    f"Expected 401, got {response.status_code}")
        except Exception as e:
            self._log_test_result("Unauthorized Access", False, str(e))
        
        return success_count > 0
    
    async def run_comprehensive_simulation(self) -> Dict[str, Any]:
        """Run comprehensive payment gateway simulation."""
        logger.info("🚀 Starting Comprehensive Payment Gateway Simulation")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info("=" * 60)
        
        # Test authentication first
        auth_success = await self.test_authentication()
        if not auth_success:
            logger.warning("Authentication test failed, but continuing with simulation...")
        
        # Simulate all payment actions
        await self.simulate_purchase_creation()
        await self.simulate_payment_cancellation()
        await self.simulate_payment_refund(refund_type="full")
        await self.simulate_payment_refund(refund_type="partial")
        await self.simulate_subscription_creation()
        await self.simulate_subscription_management()
        await self.simulate_additional_actions()
        await self.simulate_error_scenarios()
        
        # Generate final report
        logger.info("=" * 60)
        logger.info("📊 SIMULATION COMPLETE - FINAL RESULTS")
        logger.info("=" * 60)
        
        total_tests = self.test_results["total_tests"]
        passed_tests = self.test_results["passed"]
        failed_tests = self.test_results["failed"]
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results["errors"]:
            logger.info("\n❌ Failed Tests:")
            for error in self.test_results["errors"]:
                logger.info(f"  - {error}")
        
        logger.info(f"\n📈 Created Resources:")
        logger.info(f"  - Payments: {len(self.created_payments)}")
        logger.info(f"  - Subscriptions: {len(self.created_subscriptions)}")
        
        return {
            "session_id": self.session_id,
            "base_url": self.base_url,
            "test_results": self.test_results,
            "created_payments": self.created_payments,
            "created_subscriptions": self.created_subscriptions,
            "success_rate": success_rate
        }


async def main():
    """Main function to run the payment gateway simulation."""
    parser = argparse.ArgumentParser(description="EasyPay Payment Gateway Simulation")
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
        async with PaymentGatewaySimulator(args.base_url, args.api_key) as simulator:
            results = await simulator.run_comprehensive_simulation()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}")
            
            # Exit with appropriate code
            if results["success_rate"] >= 80:
                logger.info("🎉 Simulation completed successfully!")
                sys.exit(0)
            else:
                logger.warning("⚠️ Simulation completed with some failures")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Simulation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
