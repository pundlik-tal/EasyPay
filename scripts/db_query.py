#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Database Query Utility

This script provides a command-line interface for querying the database.
It can be used for testing, debugging, and data analysis.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click
from sqlalchemy import text

from src.infrastructure.database import get_db_session, init_database
from src.core.repositories import PaymentRepository, WebhookRepository, AuditLogRepository
from src.core.models.payment import PaymentStatus
from src.core.models.webhook import WebhookStatus, WebhookEventType
from src.core.models.audit_log import AuditLogLevel, AuditLogAction


class DatabaseQueryTool:
    """Database query tool for EasyPay."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        await init_database()
        self.session = get_db_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


@click.group()
def cli():
    """EasyPay Database Query Tool"""
    pass


@cli.group()
def payments():
    """Payment-related queries"""
    pass


@payments.command()
@click.option('--id', 'payment_id', help='Payment ID (UUID)')
@click.option('--external-id', 'external_id', help='External payment ID')
@click.option('--customer-id', 'customer_id', help='Customer ID')
@click.option('--status', 'status', help='Payment status')
@click.option('--limit', default=10, help='Number of results to return')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']))
async def list_payments(payment_id, external_id, customer_id, status, limit, output_format):
    """List payments with optional filters."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = PaymentRepository(session)
            
            if payment_id:
                payment = await repo.get_by_id(uuid.UUID(payment_id))
                if payment:
                    payments = [payment]
                else:
                    payments = []
            elif external_id:
                payment = await repo.get_by_external_id(external_id)
                if payment:
                    payments = [payment]
                else:
                    payments = []
            else:
                # Use list_payments with filters
                status_enum = None
                if status:
                    try:
                        status_enum = PaymentStatus(status)
                    except ValueError:
                        click.echo(f"Invalid status: {status}")
                        return
                
                result = await repo.list_payments(
                    customer_id=customer_id,
                    status=status_enum,
                    per_page=limit
                )
                payments = result['payments']
            
            if output_format == 'json':
                click.echo(json.dumps([_payment_to_dict(p) for p in payments], default=str, indent=2))
            else:
                _display_payments_table(payments)


@payments.command()
@click.option('--customer-id', required=True, help='Customer ID')
async def stats(customer_id):
    """Get payment statistics for a customer."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = PaymentRepository(session)
            
            stats = await repo.get_payment_stats(customer_id=customer_id)
            
            click.echo(f"Payment Statistics for Customer: {customer_id}")
            click.echo(f"Total Count: {stats['total_count']}")
            click.echo(f"Total Amount: ${stats['total_amount']:.2f}")
            click.echo(f"Average Amount: ${stats['average_amount']:.2f}")
            click.echo("\nStatus Breakdown:")
            for status, count in stats['status_counts'].items():
                click.echo(f"  {status}: {count}")


@payments.command()
@click.option('--search', required=True, help='Search term')
@click.option('--limit', default=10, help='Number of results to return')
async def search(search, limit):
    """Search payments by various fields."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = PaymentRepository(session)
            
            result = await repo.search_payments(search_term=search, per_page=limit)
            
            click.echo(f"Search Results for '{search}' ({result['total']} total)")
            _display_payments_table(result['payments'])


@cli.group()
def webhooks():
    """Webhook-related queries"""
    pass


@webhooks.command()
@click.option('--id', 'webhook_id', help='Webhook ID (UUID)')
@click.option('--event-id', 'event_id', help='Event ID')
@click.option('--status', 'status', help='Webhook status')
@click.option('--event-type', 'event_type', help='Event type')
@click.option('--limit', default=10, help='Number of results to return')
async def list_webhooks(webhook_id, event_id, status, event_type, limit):
    """List webhooks with optional filters."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = WebhookRepository(session)
            
            if webhook_id:
                webhook = await repo.get_by_id(uuid.UUID(webhook_id))
                if webhook:
                    webhooks = [webhook]
                else:
                    webhooks = []
            elif event_id:
                webhook = await repo.get_by_event_id(event_id)
                if webhook:
                    webhooks = [webhook]
                else:
                    webhooks = []
            else:
                # Use list_webhooks with filters
                status_enum = None
                if status:
                    try:
                        status_enum = WebhookStatus(status)
                    except ValueError:
                        click.echo(f"Invalid status: {status}")
                        return
                
                event_type_enum = None
                if event_type:
                    try:
                        event_type_enum = WebhookEventType(event_type)
                    except ValueError:
                        click.echo(f"Invalid event type: {event_type}")
                        return
                
                result = await repo.list_webhooks(
                    status=status_enum,
                    event_type=event_type_enum,
                    per_page=limit
                )
                webhooks = result['webhooks']
            
            _display_webhooks_table(webhooks)


@webhooks.command()
async def failed():
    """List failed webhooks that can be retried."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = WebhookRepository(session)
            
            failed_webhooks = await repo.get_failed_webhooks()
            
            click.echo(f"Failed Webhooks ({len(failed_webhooks)} total)")
            _display_webhooks_table(failed_webhooks)


@webhooks.command()
async def retry_ready():
    """List webhooks ready for retry."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = WebhookRepository(session)
            
            retry_webhooks = await repo.get_webhooks_ready_for_retry()
            
            click.echo(f"Webhooks Ready for Retry ({len(retry_webhooks)} total)")
            _display_webhooks_table(retry_webhooks)


@cli.group()
def audit():
    """Audit log queries"""
    pass


@audit.command()
@click.option('--action', help='Audit log action')
@click.option('--level', help='Log level')
@click.option('--entity-type', 'entity_type', help='Entity type')
@click.option('--user-id', 'user_id', help='User ID')
@click.option('--limit', default=10, help='Number of results to return')
async def list_logs(action, level, entity_type, user_id, limit):
    """List audit logs with optional filters."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = AuditLogRepository(session)
            
            action_enum = None
            if action:
                try:
                    action_enum = AuditLogAction(action)
                except ValueError:
                    click.echo(f"Invalid action: {action}")
                    return
            
            level_enum = None
            if level:
                try:
                    level_enum = AuditLogLevel(level)
                except ValueError:
                    click.echo(f"Invalid level: {level}")
                    return
            
            result = await repo.list_audit_logs(
                action=action_enum,
                level=level_enum,
                entity_type=entity_type,
                user_id=user_id,
                per_page=limit
            )
            
            _display_audit_logs_table(result['audit_logs'])


@audit.command()
async def stats():
    """Get audit log statistics."""
    async with DatabaseQueryTool() as tool:
        async for session in tool.session:
            repo = AuditLogRepository(session)
            
            stats = await repo.get_audit_log_stats()
            
            click.echo("Audit Log Statistics")
            click.echo(f"Total Count: {stats['total_count']}")
            click.echo("\nLevel Breakdown:")
            for level, count in stats['level_counts'].items():
                click.echo(f"  {level}: {count}")
            click.echo("\nAction Breakdown:")
            for action, count in stats['action_counts'].items():
                click.echo(f"  {action}: {count}")
            click.echo("\nEntity Type Breakdown:")
            for entity_type, count in stats['entity_type_counts'].items():
                click.echo(f"  {entity_type}: {count}")


@cli.command()
def health():
    """Check database health."""
    async def _health_check():
        async with DatabaseQueryTool() as tool:
            async for session in tool.session:
                try:
                    # Test basic query
                    result = await session.execute(text("SELECT 1"))
                    click.echo("✅ Database connection: OK")
                    
                    # Test table access
                    result = await session.execute(text("SELECT COUNT(*) FROM payments"))
                    payment_count = result.scalar()
                    click.echo(f"✅ Payments table: {payment_count} records")
                    
                    result = await session.execute(text("SELECT COUNT(*) FROM webhooks"))
                    webhook_count = result.scalar()
                    click.echo(f"✅ Webhooks table: {webhook_count} records")
                    
                    result = await session.execute(text("SELECT COUNT(*) FROM audit_logs"))
                    audit_count = result.scalar()
                    click.echo(f"✅ Audit logs table: {audit_count} records")
                    
                except Exception as e:
                    click.echo(f"❌ Database health check failed: {e}")
                break
    
    asyncio.run(_health_check())


def _payment_to_dict(payment):
    """Convert payment object to dictionary."""
    return {
        'id': str(payment.id),
        'external_id': payment.external_id,
        'amount': float(payment.amount),
        'currency': payment.currency,
        'status': payment.status,
        'payment_method': payment.payment_method,
        'customer_id': payment.customer_id,
        'customer_email': payment.customer_email,
        'created_at': payment.created_at.isoformat(),
        'updated_at': payment.updated_at.isoformat()
    }


def _display_payments_table(payments):
    """Display payments in table format."""
    if not payments:
        click.echo("No payments found.")
        return
    
    click.echo(f"{'ID':<36} {'External ID':<15} {'Amount':<10} {'Status':<15} {'Customer':<20} {'Created':<20}")
    click.echo("-" * 120)
    
    for payment in payments:
        customer = payment.customer_email or payment.customer_id or "N/A"
        if len(customer) > 20:
            customer = customer[:17] + "..."
        
        click.echo(f"{str(payment.id)[:8]}... {payment.external_id:<15} ${payment.amount:<9} {payment.status:<15} {customer:<20} {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


def _display_webhooks_table(webhooks):
    """Display webhooks in table format."""
    if not webhooks:
        click.echo("No webhooks found.")
        return
    
    click.echo(f"{'ID':<36} {'Event Type':<20} {'Status':<15} {'Retry':<5} {'Created':<20}")
    click.echo("-" * 100)
    
    for webhook in webhooks:
        click.echo(f"{str(webhook.id)[:8]}... {webhook.event_type:<20} {webhook.status:<15} {webhook.retry_count:<5} {webhook.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


def _display_audit_logs_table(audit_logs):
    """Display audit logs in table format."""
    if not audit_logs:
        click.echo("No audit logs found.")
        return
    
    click.echo(f"{'ID':<36} {'Action':<20} {'Level':<10} {'Message':<50} {'Created':<20}")
    click.echo("-" * 140)
    
    for log in audit_logs:
        message = log.message
        if len(message) > 50:
            message = message[:47] + "..."
        
        click.echo(f"{str(log.id)[:8]}... {log.action:<20} {log.level:<10} {message:<50} {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    cli()
