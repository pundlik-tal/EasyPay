# EasyPay Database Access Guide

## Overview

This guide provides comprehensive information on how to access and query the EasyPay database. The database layer is fully implemented with repositories, models, and query utilities.

## Database Schema

### Tables

1. **payments** - Core payment transaction data
2. **webhooks** - Webhook delivery tracking
3. **audit_logs** - System audit trail

### Key Features

- ✅ **UUID Primary Keys** - All tables use UUID primary keys
- ✅ **Foreign Key Relationships** - Proper relationships between tables
- ✅ **Indexes** - Performance indexes on frequently queried columns
- ✅ **Timestamps** - Created/updated timestamps on all records
- ✅ **Soft Deletes** - Audit trail preservation
- ✅ **JSON Fields** - Flexible metadata storage

## Repository Layer

### PaymentRepository

Located at `src/core/repositories/payment_repository.py`

**Key Methods:**
- `create(payment_data)` - Create new payment
- `get_by_id(payment_id)` - Get payment by UUID
- `get_by_external_id(external_id)` - Get payment by external ID
- `get_by_authorize_net_id(authorize_net_id)` - Get payment by Authorize.net ID
- `update(payment_id, update_data)` - Update payment
- `delete(payment_id)` - Delete payment
- `list_payments(filters)` - List payments with filtering and pagination
- `search_payments(search_term)` - Search payments by various fields
- `get_payment_stats()` - Get payment statistics
- `get_payments_by_customer(customer_id)` - Get customer payments
- `get_payments_by_status(status)` - Get payments by status

**Example Usage:**
```python
from src.core.repositories import PaymentRepository
from src.infrastructure.database import get_db_session

async for session in get_db_session():
    repo = PaymentRepository(session)
    
    # Create payment
    payment_data = {
        'external_id': 'pay_123',
        'amount': Decimal('10.00'),
        'currency': 'USD',
        'status': 'pending',
        'payment_method': 'credit_card',
        'customer_id': 'cust_123',
        'customer_email': 'customer@example.com'
    }
    payment = await repo.create(payment_data)
    
    # Get payment
    payment = await repo.get_by_id(payment.id)
    
    # List payments
    result = await repo.list_payments(
        customer_id='cust_123',
        per_page=20
    )
    payments = result['payments']
```

### WebhookRepository

Located at `src/core/repositories/webhook_repository.py`

**Key Methods:**
- `create(webhook_data)` - Create new webhook
- `get_by_id(webhook_id)` - Get webhook by UUID
- `get_by_event_id(event_id)` - Get webhook by event ID
- `update(webhook_id, update_data)` - Update webhook
- `delete(webhook_id)` - Delete webhook
- `list_webhooks(filters)` - List webhooks with filtering
- `get_failed_webhooks()` - Get webhooks that failed and can be retried
- `get_webhooks_ready_for_retry()` - Get webhooks ready for retry
- `mark_as_delivered()` - Mark webhook as delivered
- `mark_as_failed()` - Mark webhook as failed
- `schedule_retry()` - Schedule webhook for retry

### AuditLogRepository

Located at `src/core/repositories/audit_log_repository.py`

**Key Methods:**
- `create(audit_log_data)` - Create new audit log
- `get_by_id(audit_log_id)` - Get audit log by UUID
- `list_audit_logs(filters)` - List audit logs with filtering
- `get_audit_logs_by_payment(payment_id)` - Get payment audit logs
- `get_audit_logs_by_user(user_id)` - Get user audit logs
- `log_payment_action()` - Log payment-related action
- `log_security_action()` - Log security-related action
- `get_audit_log_stats()` - Get audit log statistics

## Database Query Utilities

### Simple Database Query Tool

Located at `scripts/simple_db_query.py`

**Available Commands:**

1. **Health Check**
   ```bash
   python scripts/simple_db_query.py health
   ```
   - Tests database connection
   - Shows table record counts
   - Verifies database health

2. **List Payments**
   ```bash
   python scripts/simple_db_query.py payments
   ```
   - Shows recent payments
   - Displays key payment information
   - Includes pagination

3. **List Webhooks**
   ```bash
   python scripts/simple_db_query.py webhooks
   ```
   - Shows recent webhooks
   - Displays webhook status and retry info

4. **List Audit Logs**
   ```bash
   python scripts/simple_db_query.py audit
   ```
   - Shows recent audit logs
   - Displays action and level information

5. **Get Statistics**
   ```bash
   python scripts/simple_db_query.py stats
   ```
   - Shows comprehensive database statistics
   - Includes payment, webhook, and audit log stats

### Advanced Database Query Tool

Located at `scripts/db_query.py`

A more comprehensive CLI tool with advanced filtering and querying capabilities.

## Database Models

### Payment Model

Located at `src/core/models/payment.py`

**Key Fields:**
- `id` - UUID primary key
- `external_id` - External payment identifier
- `authorize_net_transaction_id` - Authorize.net transaction ID
- `amount` - Payment amount (Decimal)
- `currency` - Currency code (3 chars)
- `status` - Payment status enum
- `payment_method` - Payment method enum
- `customer_id` - Customer identifier
- `customer_email` - Customer email
- `customer_name` - Customer name
- `card_token` - Tokenized card data
- `card_last_four` - Last 4 digits of card
- `card_brand` - Card brand (Visa, MasterCard, etc.)
- `description` - Payment description
- `payment_metadata` - JSON metadata
- `processor_response_code` - Processor response code
- `processor_response_message` - Processor response message
- `refunded_amount` - Amount refunded
- `refund_count` - Number of refunds
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `processed_at` - Processing timestamp
- `settled_at` - Settlement timestamp
- `is_test` - Test mode flag

**Business Logic Methods:**
- `is_refundable` - Check if payment can be refunded
- `is_voidable` - Check if payment can be voided
- `remaining_refund_amount` - Calculate remaining refundable amount

### Webhook Model

Located at `src/core/models/webhook.py`

**Key Fields:**
- `id` - UUID primary key
- `event_type` - Event type enum
- `event_id` - Unique event identifier
- `status` - Webhook status enum
- `payment_id` - Related payment UUID
- `url` - Webhook endpoint URL
- `headers` - Request headers (JSON)
- `payload` - Event payload (JSON)
- `response_status_code` - HTTP response status
- `response_body` - Response body
- `response_headers` - Response headers (JSON)
- `retry_count` - Number of retry attempts
- `max_retries` - Maximum retry attempts
- `next_retry_at` - Next retry timestamp
- `delivered_at` - Delivery timestamp
- `failed_at` - Failure timestamp
- `signature_verified` - Signature verification flag

**Business Logic Methods:**
- `can_retry` - Check if webhook can be retried
- `is_expired` - Check if webhook has expired
- `mark_as_delivered()` - Mark as successfully delivered
- `mark_as_failed()` - Mark as failed
- `schedule_retry()` - Schedule for retry

### AuditLog Model

Located at `src/core/models/audit_log.py`

**Key Fields:**
- `id` - UUID primary key
- `action` - Action type enum
- `level` - Log level enum
- `message` - Log message
- `entity_type` - Entity type (payment, webhook, etc.)
- `entity_id` - Entity identifier
- `payment_id` - Related payment UUID
- `user_id` - User identifier
- `api_key_id` - API key identifier
- `ip_address` - IP address
- `user_agent` - User agent string
- `request_id` - Request identifier
- `correlation_id` - Correlation identifier
- `audit_metadata` - Additional metadata (JSON)
- `old_values` - Previous values (JSON)
- `new_values` - New values (JSON)
- `created_at` - Creation timestamp

**Factory Methods:**
- `create_payment_log()` - Create payment-related audit log
- `create_webhook_log()` - Create webhook-related audit log
- `create_security_log()` - Create security-related audit log

## Database Testing

### Test Script

Located at `scripts/test_db.py`

**Test Coverage:**
- ✅ Database connection
- ✅ Payment CRUD operations
- ✅ Webhook CRUD operations
- ✅ Audit log creation
- ✅ Repository methods
- ✅ Search functionality
- ✅ Statistics generation
- ✅ Data cleanup

**Run Tests:**
```bash
python -m scripts.test_db
```

## Database Migrations

### Alembic Integration

- Migration files: `migrations/versions/`
- Current migration: `001_initial_schema.py`
- Migration commands:
  ```bash
  # Check current migration
  python -m alembic current
  
  # Apply migrations
  python -m alembic upgrade head
  
  # Create new migration
  python -m alembic revision --autogenerate -m "description"
  ```

## Performance Considerations

### Indexes

All tables have appropriate indexes for:
- Primary keys (automatic)
- Foreign keys
- Frequently queried columns
- Status fields
- Timestamps
- External identifiers

### Connection Pooling

- Pool size: 10 connections
- Max overflow: 20 connections
- Pre-ping enabled for connection health
- Async connection handling

### Query Optimization

- Repository pattern for consistent queries
- Pagination support
- Filtering capabilities
- Search functionality
- Statistics aggregation

## Security Features

### Data Protection

- ✅ **No Sensitive Data Storage** - Card numbers are tokenized
- ✅ **Audit Trail** - All operations logged
- ✅ **Foreign Key Constraints** - Data integrity
- ✅ **Input Validation** - Pydantic models
- ✅ **SQL Injection Protection** - SQLAlchemy ORM

### Access Control

- Repository pattern limits direct database access
- Session management with proper cleanup
- Transaction handling with rollback support

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check database URL in environment variables
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Migration Issues**
   - Ensure database exists
   - Check migration history
   - Verify schema compatibility

3. **Foreign Key Violations**
   - Delete dependent records first
   - Check cascade settings
   - Verify data integrity

### Debug Commands

```bash
# Check database health
python scripts/simple_db_query.py health

# View recent data
python scripts/simple_db_query.py payments
python scripts/simple_db_query.py webhooks
python scripts/simple_db_query.py audit

# Get statistics
python scripts/simple_db_query.py stats

# Run full test suite
python -m scripts.test_db
```

## Next Steps

With the database layer complete, you can now proceed to:

1. **Day 3: Authorize.net Integration** - Implement payment processing
2. **Day 4: Basic Payment Service** - Create business logic layer
3. **Day 5: API Endpoints** - Build REST API

The database foundation is solid and ready to support the payment gateway functionality.
