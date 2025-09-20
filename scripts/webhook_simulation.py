#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Webhook Simulation Script

This script simulates webhook events for testing webhook functionality:
- Payment Created
- Payment Updated
- Payment Cancelled
- Payment Refunded
- Subscription Created
- Subscription Updated
- Subscription Cancelled

Usage:
    python scripts/webhook_simulation.py [--base-url BASE_URL] [--webhook-url WEBHOOK_URL]
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebhookSimulator:
    """Webhook simulator for testing webhook functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000", webhook_url: str = None):
        """Initialize the webhook simulator."""
        self.base_url = base_url.rstrip('/')
        self.webhook_url = webhook_url or f"{self.base_url}/api/v1/webhooks/payments"
        self.client = None
        self.session_id = str(uuid.uuid4())
        
        # Webhook event templates
        self.webhook_templates = {
            "payment.created": {
                "event_type": "payment.created",
                "event_id": "evt_payment_created_{timestamp}",
                "data": {
                    "id": "pay_test_{random_id}",
                    "amount": "25.99",
                    "currency": "USD",
                    "status": "completed",
                    "payment_method": "credit_card",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "test@example.com",
                    "customer_name": "Test Customer",
                    "description": "Test payment",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}"
                    },
                    "created_at": "{timestamp}",
                    "is_test": True
                }
            },
            "payment.updated": {
                "event_type": "payment.updated",
                "event_id": "evt_payment_updated_{timestamp}",
                "data": {
                    "id": "pay_test_{random_id}",
                    "amount": "25.99",
                    "currency": "USD",
                    "status": "captured",
                    "payment_method": "credit_card",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "test@example.com",
                    "customer_name": "Test Customer",
                    "description": "Updated test payment",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}",
                        "updated_reason": "status_change"
                    },
                    "created_at": "{timestamp}",
                    "updated_at": "{timestamp}",
                    "is_test": True
                }
            },
            "payment.cancelled": {
                "event_type": "payment.cancelled",
                "event_id": "evt_payment_cancelled_{timestamp}",
                "data": {
                    "id": "pay_test_{random_id}",
                    "amount": "25.99",
                    "currency": "USD",
                    "status": "cancelled",
                    "payment_method": "credit_card",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "test@example.com",
                    "customer_name": "Test Customer",
                    "description": "Cancelled test payment",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}",
                        "cancellation_reason": "customer_request"
                    },
                    "created_at": "{timestamp}",
                    "cancelled_at": "{timestamp}",
                    "is_test": True
                }
            },
            "payment.refunded": {
                "event_type": "payment.refunded",
                "event_id": "evt_payment_refunded_{timestamp}",
                "data": {
                    "id": "pay_test_{random_id}",
                    "amount": "25.99",
                    "currency": "USD",
                    "status": "refunded",
                    "payment_method": "credit_card",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "test@example.com",
                    "customer_name": "Test Customer",
                    "description": "Refunded test payment",
                    "refund_amount": "25.99",
                    "refund_reason": "customer_request",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}",
                        "refund_type": "full"
                    },
                    "created_at": "{timestamp}",
                    "refunded_at": "{timestamp}",
                    "is_test": True
                }
            },
            "subscription.created": {
                "event_type": "subscription.created",
                "event_id": "evt_subscription_created_{timestamp}",
                "data": {
                    "id": "sub_test_{random_id}",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "subscriber@example.com",
                    "customer_name": "Test Subscriber",
                    "amount": 29.99,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "status": "active",
                    "description": "Test subscription",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}"
                    },
                    "created_at": "{timestamp}",
                    "current_period_start": "{timestamp}",
                    "current_period_end": "{next_month}",
                    "is_test": True
                }
            },
            "subscription.updated": {
                "event_type": "subscription.updated",
                "event_id": "evt_subscription_updated_{timestamp}",
                "data": {
                    "id": "sub_test_{random_id}",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "subscriber@example.com",
                    "customer_name": "Test Subscriber",
                    "amount": 39.99,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "status": "active",
                    "description": "Updated test subscription",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}",
                        "update_reason": "price_change"
                    },
                    "created_at": "{timestamp}",
                    "updated_at": "{timestamp}",
                    "current_period_start": "{timestamp}",
                    "current_period_end": "{next_month}",
                    "is_test": True
                }
            },
            "subscription.cancelled": {
                "event_type": "subscription.cancelled",
                "event_id": "evt_subscription_cancelled_{timestamp}",
                "data": {
                    "id": "sub_test_{random_id}",
                    "customer_id": "cust_test_{random_id}",
                    "customer_email": "subscriber@example.com",
                    "customer_name": "Test Subscriber",
                    "amount": 29.99,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "status": "cancelled",
                    "description": "Cancelled test subscription",
                    "metadata": {
                        "test": True,
                        "session_id": "{session_id}",
                        "cancellation_reason": "customer_request"
                    },
                    "created_at": "{timestamp}",
                    "cancelled_at": "{timestamp}",
                    "is_test": True
                }
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": self.session_id,
                "User-Agent": "EasyPay-WebhookSimulator/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _generate_webhook_data(self, event_type: str) -> Dict[str, Any]:
        """Generate webhook data for a specific event type."""
        if event_type not in self.webhook_templates:
            raise ValueError(f"Unknown event type: {event_type}")
        
        template = self.webhook_templates[event_type]
        timestamp = datetime.utcnow().isoformat() + "Z"
        next_month = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        random_id = random.randint(100000, 999999)
        
        # Convert template to JSON string and replace placeholders
        template_str = json.dumps(template)
        template_str = template_str.replace("{timestamp}", timestamp)
        template_str = template_str.replace("{next_month}", next_month)
        template_str = template_str.replace("{random_id}", str(random_id))
        template_str = template_str.replace("{session_id}", self.session_id)
        
        return json.loads(template_str)
    
    async def send_webhook(self, event_type: str) -> bool:
        """Send a webhook event."""
        logger.info(f"📡 Sending {event_type} webhook...")
        
        try:
            webhook_data = self._generate_webhook_data(event_type)
            
            response = await self.client.post(
                self.webhook_url,
                json=webhook_data,
                headers={
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Signature": f"sha256=test_signature_{random.randint(1000, 9999)}"
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ {event_type} webhook sent successfully")
                return True
            else:
                logger.error(f"❌ {event_type} webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {event_type} webhook failed: {str(e)}")
            return False
    
    async def simulate_payment_webhooks(self) -> Dict[str, bool]:
        """Simulate payment-related webhook events."""
        logger.info("💳 Simulating Payment Webhooks...")
        
        payment_events = [
            "payment.created",
            "payment.updated", 
            "payment.cancelled",
            "payment.refunded"
        ]
        
        results = {}
        for event_type in payment_events:
            results[event_type] = await self.send_webhook(event_type)
            await asyncio.sleep(1)  # Small delay between webhooks
        
        return results
    
    async def simulate_subscription_webhooks(self) -> Dict[str, bool]:
        """Simulate subscription-related webhook events."""
        logger.info("🔄 Simulating Subscription Webhooks...")
        
        subscription_events = [
            "subscription.created",
            "subscription.updated",
            "subscription.cancelled"
        ]
        
        results = {}
        for event_type in subscription_events:
            results[event_type] = await self.send_webhook(event_type)
            await asyncio.sleep(1)  # Small delay between webhooks
        
        return results
    
    async def simulate_webhook_sequence(self) -> Dict[str, bool]:
        """Simulate a complete webhook sequence."""
        logger.info("🔄 Simulating Complete Webhook Sequence...")
        
        # Simulate a payment lifecycle
        sequence_events = [
            "payment.created",
            "payment.updated",
            "payment.refunded"
        ]
        
        results = {}
        for event_type in sequence_events:
            results[event_type] = await self.send_webhook(event_type)
            await asyncio.sleep(2)  # Delay between events
        
        return results
    
    async def test_webhook_endpoint(self) -> bool:
        """Test webhook endpoint availability."""
        logger.info("🔍 Testing Webhook Endpoint...")
        
        try:
            # Send a simple test webhook
            test_data = {
                "event_type": "test",
                "event_id": f"test_{self.session_id}",
                "data": {
                    "test": True,
                    "session_id": self.session_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=test_data,
                headers={
                    "X-Webhook-Event": "test",
                    "X-Webhook-Signature": f"sha256=test_signature_{random.randint(1000, 9999)}"
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info("✅ Webhook endpoint is available")
                return True
            else:
                logger.error(f"❌ Webhook endpoint test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Webhook endpoint test failed: {str(e)}")
            return False
    
    async def run_webhook_simulation(self) -> Dict[str, Any]:
        """Run comprehensive webhook simulation."""
        logger.info("🚀 Starting Webhook Simulation")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Webhook URL: {self.webhook_url}")
        logger.info("=" * 60)
        
        results = {
            "session_id": self.session_id,
            "webhook_url": self.webhook_url,
            "base_url": self.base_url,
            "tests": {},
            "webhook_events": {}
        }
        
        # Test webhook endpoint
        results["tests"]["endpoint_test"] = await self.test_webhook_endpoint()
        
        # Simulate payment webhooks
        results["webhook_events"]["payment_webhooks"] = await self.simulate_payment_webhooks()
        
        # Simulate subscription webhooks
        results["webhook_events"]["subscription_webhooks"] = await self.simulate_subscription_webhooks()
        
        # Simulate webhook sequence
        results["webhook_events"]["sequence_webhooks"] = await self.simulate_webhook_sequence()
        
        # Calculate success rates
        all_webhook_results = []
        for category, events in results["webhook_events"].items():
            all_webhook_results.extend(events.values())
        
        total_webhooks = len(all_webhook_results)
        successful_webhooks = sum(1 for success in all_webhook_results if success)
        webhook_success_rate = (successful_webhooks / total_webhooks * 100) if total_webhooks > 0 else 0
        
        results["webhook_success_rate"] = webhook_success_rate
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 WEBHOOK SIMULATION COMPLETE")
        logger.info("=" * 60)
        
        logger.info(f"Total Webhooks Sent: {total_webhooks}")
        logger.info(f"Successful: {successful_webhooks}")
        logger.info(f"Failed: {total_webhooks - successful_webhooks}")
        logger.info(f"Success Rate: {webhook_success_rate:.1f}%")
        
        logger.info("\nWebhook Results:")
        for category, events in results["webhook_events"].items():
            logger.info(f"\n{category.replace('_', ' ').title()}:")
            for event_type, success in events.items():
                status = "✅ SUCCESS" if success else "❌ FAILED"
                logger.info(f"  {event_type}: {status}")
        
        return results


async def main():
    """Main function to run the webhook simulation."""
    parser = argparse.ArgumentParser(description="EasyPay Webhook Simulation")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL of the EasyPay API")
    parser.add_argument("--webhook-url", 
                       help="Webhook endpoint URL (defaults to {base-url}/api/v1/webhooks/payments)")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    parser.add_argument("--events", nargs="+", 
                       help="Specific events to simulate (e.g., payment.created subscription.created)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        async with WebhookSimulator(args.base_url, args.webhook_url) as simulator:
            if args.events:
                # Simulate specific events
                logger.info(f"Simulating specific events: {args.events}")
                results = {"session_id": simulator.session_id, "webhook_url": simulator.webhook_url}
                results["webhook_events"] = {}
                
                for event_type in args.events:
                    results["webhook_events"][event_type] = await simulator.send_webhook(event_type)
                    await asyncio.sleep(1)
                
                # Calculate success rate
                total_events = len(args.events)
                successful_events = sum(1 for success in results["webhook_events"].values() if success)
                results["webhook_success_rate"] = (successful_events / total_events * 100) if total_events > 0 else 0
                
            else:
                # Run full simulation
                results = await simulator.run_webhook_simulation()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}")
            
            # Exit with appropriate code
            if results["webhook_success_rate"] >= 80:
                logger.info("🎉 Webhook simulation completed successfully!")
                sys.exit(0)
            else:
                logger.warning("⚠️ Webhook simulation completed with some failures")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Simulation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
