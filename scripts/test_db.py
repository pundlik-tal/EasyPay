#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Database Test Script

This script tests database connectivity and basic operations.
"""

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from src.infrastructure.database import init_database, get_db_session
from src.core.repositories import PaymentRepository, WebhookRepository, AuditLogRepository
from src.core.models.payment import PaymentStatus, PaymentMethod
from src.core.models.webhook import WebhookStatus, WebhookEventType
from src.core.models.audit_log import AuditLogLevel, AuditLogAction


async def test_database():
    """Test database operations."""
    print("🚀 Starting EasyPay Database Tests...")
    
    try:
        # Initialize database
        await init_database()
        print("✅ Database initialized successfully")
        
        # Get database session
        async for session in get_db_session():
            print("✅ Database session created")
            
            # Test repositories
            payment_repo = PaymentRepository(session)
            webhook_repo = WebhookRepository(session)
            audit_repo = AuditLogRepository(session)
            
            print("✅ Repositories initialized")
            
            # Test 1: Create a test payment
            print("\n📝 Test 1: Creating test payment...")
            test_payment_data = {
                'external_id': f'test_pay_{uuid.uuid4().hex[:8]}',
                'amount': Decimal('10.00'),
                'currency': 'USD',
                'status': PaymentStatus.PENDING.value,
                'payment_method': PaymentMethod.CREDIT_CARD.value,
                'customer_id': 'test_customer_123',
                'customer_email': 'test@example.com',
                'customer_name': 'Test Customer',
                'description': 'Test payment for database testing',
                'is_test': True
            }
            
            test_payment = await payment_repo.create(test_payment_data)
            print(f"✅ Test payment created: {test_payment.id}")
            
            # Test 2: Retrieve the payment
            print("\n📖 Test 2: Retrieving test payment...")
            retrieved_payment = await payment_repo.get_by_id(test_payment.id)
            if retrieved_payment:
                print(f"✅ Payment retrieved: {retrieved_payment.external_id}")
            else:
                print("❌ Failed to retrieve payment")
                return
            
            # Test 3: Update the payment
            print("\n✏️ Test 3: Updating test payment...")
            update_data = {
                'status': PaymentStatus.CAPTURED.value,
                'processed_at': datetime.utcnow(),
                'processor_transaction_id': 'test_txn_123'
            }
            
            updated_payment = await payment_repo.update(test_payment.id, update_data)
            if updated_payment and updated_payment.status == PaymentStatus.CAPTURED.value:
                print(f"✅ Payment updated: {updated_payment.status}")
            else:
                print("❌ Failed to update payment")
                return
            
            # Test 4: Create a test webhook
            print("\n🔗 Test 4: Creating test webhook...")
            test_webhook_data = {
                'event_type': WebhookEventType.PAYMENT_CAPTURED.value,
                'event_id': f'test_evt_{uuid.uuid4().hex[:8]}',
                'status': WebhookStatus.PENDING.value,
                'payment_id': test_payment.id,
                'url': 'https://example.com/webhook',
                'payload': {'payment_id': str(test_payment.id), 'status': 'captured'},
                'is_test': True
            }
            
            test_webhook = await webhook_repo.create(test_webhook_data)
            print(f"✅ Test webhook created: {test_webhook.id}")
            
            # Test 5: Create an audit log
            print("\n📋 Test 5: Creating audit log...")
            test_audit_log = await audit_repo.log_payment_action(
                action=AuditLogAction.PAYMENT_UPDATED,
                payment_id=test_payment.id,
                message=f"Payment {test_payment.external_id} status updated to captured",
                metadata={'test': True, 'updated_by': 'test_script'},
                old_values={'status': PaymentStatus.PENDING.value},
                new_values={'status': PaymentStatus.CAPTURED.value}
            )
            print(f"✅ Audit log created: {test_audit_log.id}")
            
            # Test 6: List payments
            print("\n📊 Test 6: Listing payments...")
            payments_result = await payment_repo.list_payments(per_page=5)
            print(f"✅ Found {payments_result['total']} payments")
            
            # Test 7: Search payments
            print("\n🔍 Test 7: Searching payments...")
            search_result = await payment_repo.search_payments('test', per_page=5)
            print(f"✅ Search found {search_result['total']} payments")
            
            # Test 8: Get payment statistics
            print("\n📈 Test 8: Getting payment statistics...")
            stats = await payment_repo.get_payment_stats()
            print(f"✅ Payment stats: {stats['total_count']} total, ${stats['total_amount']:.2f} total amount")
            
            # Test 9: List webhooks
            print("\n🔗 Test 9: Listing webhooks...")
            webhooks_result = await webhook_repo.list_webhooks(per_page=5)
            print(f"✅ Found {webhooks_result['total']} webhooks")
            
            # Test 10: List audit logs
            print("\n📋 Test 10: Listing audit logs...")
            audit_result = await audit_repo.list_audit_logs(per_page=5)
            print(f"✅ Found {audit_result['total']} audit logs")
            
            # Test 11: Clean up test data
            print("\n🧹 Test 11: Cleaning up test data...")
            
            # Delete webhook
            await webhook_repo.delete(test_webhook.id)
            print("✅ Test webhook deleted")
            
            # Delete audit logs first (due to foreign key constraint)
            audit_logs = await audit_repo.get_audit_logs_by_payment(test_payment.id)
            for audit_log in audit_logs:
                await session.delete(audit_log)
            await session.commit()
            print("✅ Test audit logs deleted")
            
            # Delete payment
            await payment_repo.delete(test_payment.id)
            print("✅ Test payment deleted")
            
            print("\n🎉 All database tests passed successfully!")
            break
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_connection():
    """Test basic database connection."""
    print("🔌 Testing database connection...")
    
    try:
        await init_database()
        print("✅ Database connection successful")
        
        async for session in get_db_session():
            # Test basic query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                print("✅ Basic query test passed")
            else:
                print("❌ Basic query test failed")
            
            break
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("EasyPay Database Test Suite")
    print("=" * 50)
    
    # Run connection test first
    asyncio.run(test_connection())
    
    print("\n" + "=" * 50)
    
    # Run full test suite
    asyncio.run(test_database())
