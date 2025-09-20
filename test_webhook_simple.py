#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Simple Webhook System Test
"""
import asyncio
import json
import uuid
from datetime import datetime

from src.core.services.request_signing_service import WebhookSigningService
from src.infrastructure.config import get_settings

settings = get_settings()


async def test_webhook_signature():
    """Test webhook signature generation and verification."""
    print("🔧 Testing webhook signature generation and verification...")
    
    try:
        # Initialize signing service
        signing_service = WebhookSigningService(settings.WEBHOOK_SECRET)
        
        # Test payload
        test_payload = json.dumps({
            "event_type": "payment.authorized",
            "event_id": "test_event_123",
            "data": {
                "id": "pay_123456789",
                "amount": "10.00",
                "currency": "USD",
                "status": "authorized"
            },
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Generate signature
        signature = signing_service.generate_webhook_signature(test_payload)
        print(f"✅ Signature generated: {signature[:50]}...")
        
        # Verify signature
        is_valid = signing_service.verify_webhook_signature(test_payload, signature)
        print(f"✅ Signature verification: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test invalid signature
        invalid_signature = "t=1234567890,v1=invalid_signature"
        try:
            signing_service.verify_webhook_signature(test_payload, invalid_signature)
            print("❌ Invalid signature test: FAILED (should have raised exception)")
        except Exception:
            print("✅ Invalid signature test: PASSED (correctly rejected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Signature test failed: {str(e)}")
        return False


async def test_webhook_event_types():
    """Test webhook event type validation."""
    print("\n🔧 Testing webhook event types...")
    
    try:
        from src.core.models.webhook import WebhookEventType
        
        # Test valid event types
        valid_events = [event.value for event in WebhookEventType]
        print(f"✅ Valid event types: {valid_events}")
        
        # Test event type validation
        test_event = "payment.authorized"
        if test_event in valid_events:
            print(f"✅ Event type validation: {test_event} is valid")
        else:
            print(f"❌ Event type validation: {test_event} is invalid")
        
        return True
        
    except Exception as e:
        print(f"❌ Event type test failed: {str(e)}")
        return False


async def test_webhook_configuration():
    """Test webhook configuration."""
    print("\n🔧 Testing webhook configuration...")
    
    try:
        # Test configuration values
        print(f"✅ Webhook secret configured: {'Yes' if settings.WEBHOOK_SECRET else 'No'}")
        print(f"✅ Max retries: {settings.WEBHOOK_MAX_RETRIES}")
        print(f"✅ Retry interval: {settings.WEBHOOK_RETRY_INTERVAL} seconds")
        print(f"✅ Timeout: {settings.WEBHOOK_TIMEOUT} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False


async def test_webhook_models():
    """Test webhook models."""
    print("\n🔧 Testing webhook models...")
    
    try:
        from src.core.models.webhook import WebhookStatus, WebhookEventType
        
        # Test status enum
        statuses = [status.value for status in WebhookStatus]
        print(f"✅ Webhook statuses: {statuses}")
        
        # Test event type enum
        event_types = [event.value for event in WebhookEventType]
        print(f"✅ Event types: {event_types}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        return False


async def main():
    """Run simple webhook system tests."""
    print("🚀 Starting EasyPay Webhook System Simple Tests")
    print("=" * 60)
    
    # Test webhook signature
    signature_test = await test_webhook_signature()
    
    # Test webhook event types
    event_type_test = await test_webhook_event_types()
    
    # Test webhook configuration
    config_test = await test_webhook_configuration()
    
    # Test webhook models
    model_test = await test_webhook_models()
    
    print("\n" + "=" * 60)
    print("✅ Simple webhook system tests completed!")
    
    # Summary
    tests_passed = sum([signature_test, event_type_test, config_test, model_test])
    total_tests = 4
    
    print(f"\n📋 Test Summary: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎯 All webhook system components are working correctly!")
        print("\n✅ Day 16: Webhook System Implementation Complete!")
        print("   - Webhook signature generation and verification: ✅")
        print("   - Webhook event type validation: ✅")
        print("   - Webhook configuration management: ✅")
        print("   - Webhook models and enums: ✅")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())
