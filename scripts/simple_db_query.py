#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Simple Database Query Utility

This script provides a simple command-line interface for querying the database.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import get_db_session, init_database
from src.core.repositories import PaymentRepository, WebhookRepository, AuditLogRepository
from sqlalchemy import text


async def health_check():
    """Check database health."""
    print("🔍 Checking database health...")
    
    try:
        await init_database()
        print("✅ Database initialized successfully")
        
        async for session in get_db_session():
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection: OK")
            
            # Test table access
            result = await session.execute(text("SELECT COUNT(*) FROM payments"))
            payment_count = result.scalar()
            print(f"✅ Payments table: {payment_count} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM webhooks"))
            webhook_count = result.scalar()
            print(f"✅ Webhooks table: {webhook_count} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM audit_logs"))
            audit_count = result.scalar()
            print(f"✅ Audit logs table: {audit_count} records")
            
            break
            
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        import traceback
        traceback.print_exc()


async def list_payments():
    """List recent payments."""
    print("📋 Listing recent payments...")
    
    try:
        await init_database()
        
        async for session in get_db_session():
            repo = PaymentRepository(session)
            
            result = await repo.list_payments(per_page=10)
            payments = result['payments']
            
            if not payments:
                print("No payments found.")
                return
            
            print(f"\nFound {result['total']} payments (showing {len(payments)}):")
            print("-" * 80)
            print(f"{'ID':<36} {'External ID':<15} {'Amount':<10} {'Status':<15} {'Customer':<20}")
            print("-" * 80)
            
            for payment in payments:
                customer = payment.customer_email or payment.customer_id or "N/A"
                if len(customer) > 20:
                    customer = customer[:17] + "..."
                
                print(f"{str(payment.id)[:8]}... {payment.external_id:<15} ${payment.amount:<9} {payment.status:<15} {customer:<20}")
            
            break
            
    except Exception as e:
        print(f"❌ Failed to list payments: {e}")
        import traceback
        traceback.print_exc()


async def list_webhooks():
    """List recent webhooks."""
    print("🔗 Listing recent webhooks...")
    
    try:
        await init_database()
        
        async for session in get_db_session():
            repo = WebhookRepository(session)
            
            result = await repo.list_webhooks(per_page=10)
            webhooks = result['webhooks']
            
            if not webhooks:
                print("No webhooks found.")
                return
            
            print(f"\nFound {result['total']} webhooks (showing {len(webhooks)}):")
            print("-" * 80)
            print(f"{'ID':<36} {'Event Type':<20} {'Status':<15} {'Retry':<5} {'Created':<20}")
            print("-" * 80)
            
            for webhook in webhooks:
                print(f"{str(webhook.id)[:8]}... {webhook.event_type:<20} {webhook.status:<15} {webhook.retry_count:<5} {webhook.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            break
            
    except Exception as e:
        print(f"❌ Failed to list webhooks: {e}")
        import traceback
        traceback.print_exc()


async def list_audit_logs():
    """List recent audit logs."""
    print("📋 Listing recent audit logs...")
    
    try:
        await init_database()
        
        async for session in get_db_session():
            repo = AuditLogRepository(session)
            
            result = await repo.list_audit_logs(per_page=10)
            audit_logs = result['audit_logs']
            
            if not audit_logs:
                print("No audit logs found.")
                return
            
            print(f"\nFound {result['total']} audit logs (showing {len(audit_logs)}):")
            print("-" * 100)
            print(f"{'ID':<36} {'Action':<20} {'Level':<10} {'Message':<50}")
            print("-" * 100)
            
            for log in audit_logs:
                message = log.message
                if len(message) > 50:
                    message = message[:47] + "..."
                
                print(f"{str(log.id)[:8]}... {log.action:<20} {log.level:<10} {message:<50}")
            
            break
            
    except Exception as e:
        print(f"❌ Failed to list audit logs: {e}")
        import traceback
        traceback.print_exc()


async def get_stats():
    """Get database statistics."""
    print("📊 Getting database statistics...")
    
    try:
        await init_database()
        
        async for session in get_db_session():
            payment_repo = PaymentRepository(session)
            webhook_repo = WebhookRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Payment stats
            payment_stats = await payment_repo.get_payment_stats()
            print(f"\n💳 Payment Statistics:")
            print(f"  Total Count: {payment_stats['total_count']}")
            print(f"  Total Amount: ${payment_stats['total_amount']:.2f}")
            print(f"  Average Amount: ${payment_stats['average_amount']:.2f}")
            print(f"  Status Breakdown:")
            for status, count in payment_stats['status_counts'].items():
                print(f"    {status}: {count}")
            
            # Webhook stats
            webhook_stats = await webhook_repo.get_webhook_stats()
            print(f"\n🔗 Webhook Statistics:")
            print(f"  Total Count: {webhook_stats['total_count']}")
            print(f"  Status Breakdown:")
            for status, count in webhook_stats['status_counts'].items():
                print(f"    {status}: {count}")
            
            # Audit log stats
            audit_stats = await audit_repo.get_audit_log_stats()
            print(f"\n📋 Audit Log Statistics:")
            print(f"  Total Count: {audit_stats['total_count']}")
            print(f"  Level Breakdown:")
            for level, count in audit_stats['level_counts'].items():
                print(f"    {level}: {count}")
            
            break
            
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python simple_db_query.py <command>")
        print("Commands:")
        print("  health     - Check database health")
        print("  payments   - List recent payments")
        print("  webhooks   - List recent webhooks")
        print("  audit      - List recent audit logs")
        print("  stats      - Get database statistics")
        return
    
    command = sys.argv[1].lower()
    
    if command == "health":
        asyncio.run(health_check())
    elif command == "payments":
        asyncio.run(list_payments())
    elif command == "webhooks":
        asyncio.run(list_webhooks())
    elif command == "audit":
        asyncio.run(list_audit_logs())
    elif command == "stats":
        asyncio.run(get_stats())
    else:
        print(f"Unknown command: {command}")
        print("Available commands: health, payments, webhooks, audit, stats")


if __name__ == '__main__':
    main()
