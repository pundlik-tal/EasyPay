#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Authorize.net Webhook Testing Script

This script tests the Authorize.net webhook implementation including:
- Webhook endpoint functionality
- Signature verification
- Event processing
- Deduplication
- Webhook replay
- Error handling

Usage:
    python test_authorize_net_webhooks.py
"""

import asyncio
import json
import uuid
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any
import httpx


class AuthorizeNetWebhookTester:
    """Test suite for Authorize.net webhook functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize webhook tester.
        
        Args:
            base_url: Base URL of the EasyPay API
        """
        self.base_url = base_url
        self.webhook_secret = "test-webhook-secret-key"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def _generate_signature(self, payload: bytes) -> str:
        """
        Generate HMAC-SHA512 signature for webhook payload.
        
        Args:
            payload: Webhook payload bytes
            
        Returns:
            Signature string
        """
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return f"sha512={signature}"
    
    def _create_test_payload(self, event_type: str, transaction_id: str = None) -> Dict[str, Any]:
        """
        Create test webhook payload.
        
        Args:
            event_type: Authorize.net event type
            transaction_id: Transaction ID (optional)
            
        Returns:
            Test payload dictionary
        """
        if not transaction_id:
            transaction_id = f"test_txn_{uuid.uuid4().hex[:8]}"
        
        return {
            "eventType": event_type,
            "eventId": f"test_evt_{uuid.uuid4().hex[:8]}",
            "payload": {
                "id": transaction_id,
                "amount": "10.00",
                "currency": "USD",
                "status": "capturedPending",
                "paymentMethod": {
                    "creditCard": {
                        "cardNumber": "****1111",
                        "expirationDate": "1225"
                    }
                },
                "billTo": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "address": "123 Test St",
                    "city": "Test City",
                    "state": "CA",
                    "zip": "12345",
                    "country": "US"
                }
            },
            "createdAt": datetime.utcnow().isoformat()
        }
    
    async def test_webhook_endpoint(self) -> Dict[str, Any]:
        """Test basic webhook endpoint functionality."""
        print("🧪 Testing webhook endpoint...")
        
        payload = self._create_test_payload("net.authorize.payment.authcapture.created")
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_signature(payload_bytes)
        
        headers = {
            "Content-Type": "application/json",
            "X-Anet-Signature": signature
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Webhook endpoint test passed: {result.get('message')}")
                return {"success": True, "data": result}
            else:
                print(f"❌ Webhook endpoint test failed: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ Webhook endpoint test error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_signature_verification(self) -> Dict[str, Any]:
        """Test webhook signature verification."""
        print("🔐 Testing signature verification...")
        
        payload = self._create_test_payload("net.authorize.payment.authcapture.created")
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Test with valid signature
        valid_signature = self._generate_signature(payload_bytes)
        headers = {
            "Content-Type": "application/json",
            "X-Anet-Signature": valid_signature
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ Valid signature test passed")
                valid_result = {"success": True, "data": response.json()}
            else:
                print(f"❌ Valid signature test failed: {response.status_code}")
                valid_result = {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ Valid signature test error: {str(e)}")
            valid_result = {"success": False, "error": str(e)}
        
        # Test with invalid signature
        invalid_signature = "sha512=invalid_signature"
        headers["X-Anet-Signature"] = invalid_signature
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response.status_code == 401:
                print("✅ Invalid signature test passed (correctly rejected)")
                invalid_result = {"success": True, "data": response.json()}
            else:
                print(f"❌ Invalid signature test failed: {response.status_code}")
                invalid_result = {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ Invalid signature test error: {str(e)}")
            invalid_result = {"success": False, "error": str(e)}
        
        return {
            "valid_signature": valid_result,
            "invalid_signature": invalid_result
        }
    
    async def test_event_processing(self) -> Dict[str, Any]:
        """Test different event type processing."""
        print("📋 Testing event processing...")
        
        event_types = [
            "net.authorize.payment.authcapture.created",
            "net.authorize.payment.authonly.created",
            "net.authorize.payment.refund.created",
            "net.authorize.payment.void.created",
            "net.authorize.payment.settlement.created",
            "net.authorize.payment.fraud.created",
            "net.authorize.payment.chargeback.created"
        ]
        
        results = {}
        
        for event_type in event_types:
            print(f"  Testing {event_type}...")
            
            payload = self._create_test_payload(event_type)
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = self._generate_signature(payload_bytes)
            
            headers = {
                "Content-Type": "application/json",
                "X-Anet-Signature": signature
            }
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/v1/webhooks/authorize-net",
                    content=payload_bytes,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"    ✅ {event_type} processed successfully")
                    results[event_type] = {"success": True, "data": result}
                else:
                    print(f"    ❌ {event_type} failed: {response.status_code}")
                    results[event_type] = {"success": False, "error": response.text}
                    
            except Exception as e:
                print(f"    ❌ {event_type} error: {str(e)}")
                results[event_type] = {"success": False, "error": str(e)}
        
        return results
    
    async def test_deduplication(self) -> Dict[str, Any]:
        """Test webhook deduplication."""
        print("🔄 Testing deduplication...")
        
        # Create a payload with fixed event ID
        event_id = f"dedup_test_{uuid.uuid4().hex[:8]}"
        payload = self._create_test_payload("net.authorize.payment.authcapture.created")
        payload["eventId"] = event_id
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_signature(payload_bytes)
        
        headers = {
            "Content-Type": "application/json",
            "X-Anet-Signature": signature
        }
        
        # Send first webhook
        try:
            response1 = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response1.status_code == 200:
                result1 = response1.json()
                print("✅ First webhook processed successfully")
                first_result = {"success": True, "data": result1}
            else:
                print(f"❌ First webhook failed: {response1.status_code}")
                first_result = {"success": False, "error": response1.text}
        except Exception as e:
            print(f"❌ First webhook error: {str(e)}")
            first_result = {"success": False, "error": str(e)}
        
        # Send duplicate webhook
        try:
            response2 = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                if result2.get('data', {}).get('is_duplicate'):
                    print("✅ Duplicate webhook correctly detected")
                    duplicate_result = {"success": True, "data": result2}
                else:
                    print("❌ Duplicate webhook not detected")
                    duplicate_result = {"success": False, "error": "Duplicate not detected"}
            else:
                print(f"❌ Duplicate webhook failed: {response2.status_code}")
                duplicate_result = {"success": False, "error": response2.text}
        except Exception as e:
            print(f"❌ Duplicate webhook error: {str(e)}")
            duplicate_result = {"success": False, "error": str(e)}
        
        return {
            "first_webhook": first_result,
            "duplicate_webhook": duplicate_result
        }
    
    async def test_webhook_replay(self) -> Dict[str, Any]:
        """Test webhook replay functionality."""
        print("🔄 Testing webhook replay...")
        
        # First, create a webhook to replay
        payload = self._create_test_payload("net.authorize.payment.authcapture.created")
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_signature(payload_bytes)
        
        headers = {
            "Content-Type": "application/json",
            "X-Anet-Signature": signature
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net",
                content=payload_bytes,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                webhook_id = result.get('data', {}).get('webhook_id')
                
                if webhook_id:
                    print(f"✅ Original webhook created: {webhook_id}")
                    
                    # Now replay the webhook
                    replay_response = await self.client.post(
                        f"{self.base_url}/api/v1/webhooks/authorize-net/replay/{webhook_id}"
                    )
                    
                    if replay_response.status_code == 200:
                        replay_result = replay_response.json()
                        print("✅ Webhook replay successful")
                        return {
                            "original_webhook": {"success": True, "data": result},
                            "replay_webhook": {"success": True, "data": replay_result}
                        }
                    else:
                        print(f"❌ Webhook replay failed: {replay_response.status_code}")
                        return {
                            "original_webhook": {"success": True, "data": result},
                            "replay_webhook": {"success": False, "error": replay_response.text}
                        }
                else:
                    print("❌ No webhook ID returned")
                    return {"success": False, "error": "No webhook ID returned"}
            else:
                print(f"❌ Original webhook creation failed: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ Webhook replay test error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_test_endpoint(self) -> Dict[str, Any]:
        """Test the test webhook endpoint."""
        print("🧪 Testing test webhook endpoint...")
        
        payload = self._create_test_payload("net.authorize.payment.authcapture.created")
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/webhooks/authorize-net/test",
                content=payload_bytes,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Test webhook endpoint successful")
                return {"success": True, "data": result}
            else:
                print(f"❌ Test webhook endpoint failed: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ Test webhook endpoint error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_supported_events(self) -> Dict[str, Any]:
        """Test getting supported events."""
        print("📋 Testing supported events endpoint...")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/webhooks/authorize-net/events"
            )
            
            if response.status_code == 200:
                result = response.json()
                events = result.get('data', {}).get('supported_events', [])
                print(f"✅ Supported events retrieved: {len(events)} events")
                return {"success": True, "data": result}
            else:
                print(f"❌ Supported events failed: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ Supported events error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all webhook tests."""
        print("🚀 Starting Authorize.net Webhook Tests")
        print("=" * 50)
        
        results = {}
        
        # Run all tests
        results["webhook_endpoint"] = await self.test_webhook_endpoint()
        results["signature_verification"] = await self.test_signature_verification()
        results["event_processing"] = await self.test_event_processing()
        results["deduplication"] = await self.test_deduplication()
        results["webhook_replay"] = await self.test_webhook_replay()
        results["test_endpoint"] = await self.test_test_endpoint()
        results["supported_events"] = await self.test_supported_events()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in results.items():
            if isinstance(result, dict) and result.get("success"):
                passed_tests += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
            total_tests += 1
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100
            },
            "results": results
        }


async def main():
    """Main test function."""
    async with AuthorizeNetWebhookTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        with open("webhook_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Test results saved to: webhook_test_results.json")
        
        return results


if __name__ == "__main__":
    asyncio.run(main())
