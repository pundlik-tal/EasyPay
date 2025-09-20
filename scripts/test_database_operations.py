#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Database Operations Test Script

This script tests all the advanced database operations including:
- Transaction management
- Cached repositories
- Data validation
- Error handling
- Migration management
"""

import asyncio
import uuid
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.infrastructure.database import (
    init_database, get_db_session, get_migration_manager, 
    get_data_validator, get_error_handler
)
from src.infrastructure.database.transaction_manager import (
    get_transaction_manager, TransactionIsolationLevel
)
from src.core.repositories.cached_payment_repository import CachedPaymentRepository
from src.core.repositories.payment_repository import PaymentRepository
from src.core.models.payment import PaymentStatus, PaymentMethod
from src.core.exceptions import DatabaseError, ValidationError, ConflictError


async def test_transaction_management():
    """Test transaction management features."""
    print("🔄 Testing Transaction Management...")
    
    try:
        transaction_manager = get_transaction_manager()
        
        # Test basic transaction
        async with transaction_manager.transaction() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            assert test_value == 1
            print("✅ Basic transaction test passed")
        
        # Test nested transaction
        async with transaction_manager.transaction() as session:
            async with transaction_manager.nested_transaction(session):
                result = await session.execute(text("SELECT 2 as test"))
                test_value = result.scalar()
                assert test_value == 2
            print("✅ Nested transaction test passed")
        
        # Test transaction with isolation level
        async with transaction_manager.transaction(
            isolation_level=TransactionIsolationLevel.READ_COMMITTED
        ) as session:
            result = await session.execute(text("SELECT 3 as test"))
            test_value = result.scalar()
            assert test_value == 3
            print("✅ Isolation level transaction test passed")
        
        # Test bulk operations
        test_data = [
            {
                'external_id': f'test_bulk_{i}',
                'amount': Decimal('10.00'),
                'currency': 'USD',
                'status': PaymentStatus.PENDING.value,
                'payment_method': PaymentMethod.CREDIT_CARD.value,
                'is_test': True
            }
            for i in range(5)
        ]
        
        inserted_objects = await transaction_manager.bulk_insert(
            Payment, test_data, batch_size=2
        )
        assert len(inserted_objects) == 5
        print("✅ Bulk insert test passed")
        
        # Clean up bulk test data
        ids = [obj.id for obj in inserted_objects]
        deleted_count = await transaction_manager.bulk_delete(Payment, ids)
        assert deleted_count == 5
        print("✅ Bulk delete test passed")
        
        print("🎉 Transaction management tests passed!")
        
    except Exception as e:
        print(f"❌ Transaction management test failed: {e}")
        raise


async def test_cached_repository():
    """Test cached payment repository."""
    print("\n💾 Testing Cached Payment Repository...")
    
    try:
        async for session in get_db_session():
            # Create cached repository
            cached_repo = CachedPaymentRepository(session)
            
            # Test create with caching
            test_payment_data = {
                'external_id': f'test_cached_{uuid.uuid4().hex[:8]}',
                'amount': Decimal('25.00'),
                'currency': 'USD',
                'status': PaymentStatus.PENDING.value,
                'payment_method': PaymentMethod.CREDIT_CARD.value,
                'customer_id': 'test_customer_cached',
                'customer_email': 'cached@example.com',
                'is_test': True
            }
            
            payment = await cached_repo.create(test_payment_data)
            print("✅ Cached payment creation test passed")
            
            # Test get by ID (should hit cache)
            cached_payment = await cached_repo.get_by_id(payment.id)
            assert cached_payment is not None
            assert cached_payment.external_id == test_payment_data['external_id']
            print("✅ Cached payment retrieval test passed")
            
            # Test get by external ID (should hit cache)
            cached_payment_by_external = await cached_repo.get_by_external_id(payment.external_id)
            assert cached_payment_by_external is not None
            assert cached_payment_by_external.id == payment.id
            print("✅ Cached external ID lookup test passed")
            
            # Test update with cache invalidation
            update_data = {
                'status': PaymentStatus.CAPTURED.value,
                'processed_at': datetime.utcnow()
            }
            
            updated_payment = await cached_repo.update(payment.id, update_data)
            assert updated_payment.status == PaymentStatus.CAPTURED.value
            print("✅ Cached payment update test passed")
            
            # Test list with caching
            payments_result = await cached_repo.list_payments(per_page=5)
            assert 'payments' in payments_result
            assert 'total' in payments_result
            print("✅ Cached payment listing test passed")
            
            # Test search with caching
            search_result = await cached_repo.search_payments('test_customer_cached', per_page=5)
            assert 'payments' in search_result
            assert 'total' in search_result
            print("✅ Cached payment search test passed")
            
            # Test stats with caching
            stats = await cached_repo.get_payment_stats()
            assert 'total_count' in stats
            assert 'total_amount' in stats
            print("✅ Cached payment stats test passed")
            
            # Test cache invalidation
            await cached_repo.invalidate_payment_cache(payment.id)
            print("✅ Cache invalidation test passed")
            
            # Clean up
            await cached_repo.delete(payment.id)
            print("✅ Cached payment deletion test passed")
            
            break
        
        print("🎉 Cached repository tests passed!")
        
    except Exception as e:
        print(f"❌ Cached repository test failed: {e}")
        raise


async def test_data_validation():
    """Test data validation system."""
    print("\n✅ Testing Data Validation...")
    
    try:
        validator = get_data_validator()
        
        # Test valid payment data
        valid_payment_data = {
            'external_id': 'test_valid_123',
            'amount': Decimal('50.00'),
            'currency': 'USD',
            'status': PaymentStatus.PENDING.value,
            'payment_method': PaymentMethod.CREDIT_CARD.value,
            'customer_id': 'valid_customer',
            'customer_email': 'valid@example.com',
            'customer_name': 'Valid Customer',
            'card_last_four': '4242',
            'card_brand': 'visa',
            'card_exp_month': '12',
            'card_exp_year': '2025',
            'refunded_amount': Decimal('0.00'),
            'refund_count': 0,
            'is_test': True
        }
        
        validation_result = await validator.validate_model_data("Payment", valid_payment_data)
        assert validation_result['valid'] == True
        assert len(validation_result['errors']) == 0
        print("✅ Valid payment data validation test passed")
        
        # Test invalid payment data
        invalid_payment_data = {
            'external_id': '',  # Invalid: empty string
            'amount': Decimal('-10.00'),  # Invalid: negative amount
            'currency': 'INVALID',  # Invalid: not a valid currency
            'status': 'invalid_status',  # Invalid: not a valid status
            'payment_method': 'invalid_method',  # Invalid: not a valid method
            'customer_email': 'invalid-email',  # Invalid: not a valid email
            'card_last_four': '123',  # Invalid: not 4 digits
            'card_brand': 'invalid_brand',  # Invalid: not a valid brand
            'card_exp_month': '13',  # Invalid: month > 12
            'card_exp_year': '2020',  # Invalid: expired year
            'refunded_amount': Decimal('-5.00'),  # Invalid: negative refund
            'refund_count': -1,  # Invalid: negative count
            'is_test': True
        }
        
        validation_result = await validator.validate_model_data("Payment", invalid_payment_data)
        assert validation_result['valid'] == False
        assert len(validation_result['errors']) > 0
        print("✅ Invalid payment data validation test passed")
        
        # Test webhook validation
        valid_webhook_data = {
            'event_type': 'payment.authorized',
            'event_id': 'evt_test_123',
            'status': 'pending',
            'url': 'https://example.com/webhook',
            'payload': {'test': 'data'},
            'retry_count': 0,
            'max_retries': 3,
            'is_test': True
        }
        
        validation_result = await validator.validate_model_data("Webhook", valid_webhook_data)
        assert validation_result['valid'] == True
        print("✅ Valid webhook data validation test passed")
        
        # Test audit log validation
        valid_audit_data = {
            'action': 'payment.created',
            'level': 'info',
            'message': 'Payment created successfully',
            'entity_type': 'payment',
            'entity_id': 'pay_123',
            'user_id': 'user_123',
            'ip_address': '192.168.1.1',
            'request_id': str(uuid.uuid4()),
            'correlation_id': str(uuid.uuid4()),
            'is_test': True
        }
        
        validation_result = await validator.validate_model_data("AuditLog", valid_audit_data)
        assert validation_result['valid'] == True
        print("✅ Valid audit log data validation test passed")
        
        print("🎉 Data validation tests passed!")
        
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        raise


async def test_error_handling():
    """Test error handling system."""
    print("\n🚨 Testing Error Handling...")
    
    try:
        error_handler = get_error_handler()
        
        # Test connection
        connection_test = await error_handler.test_connection()
        assert connection_test['status'] == 'success'
        print("✅ Connection test passed")
        
        # Test pool status
        pool_status = await error_handler.get_connection_pool_status()
        assert 'pool_size' in pool_status
        assert 'checked_in' in pool_status
        print("✅ Pool status test passed")
        
        # Test error classification
        test_error = DatabaseError("Test error")
        error_info = error_handler.classify_error(test_error)
        assert error_info.category.value == 'unknown'
        assert error_info.severity.value == 'medium'
        print("✅ Error classification test passed")
        
        # Test error statistics
        stats = error_handler.get_error_statistics()
        assert 'total_errors' in stats
        assert 'category_counts' in stats
        print("✅ Error statistics test passed")
        
        # Test recent errors
        recent_errors = error_handler.get_recent_errors(limit=5)
        assert isinstance(recent_errors, list)
        print("✅ Recent errors test passed")
        
        print("🎉 Error handling tests passed!")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        raise


async def test_migration_management():
    """Test migration management system."""
    print("\n📋 Testing Migration Management...")
    
    try:
        migration_manager = get_migration_manager()
        
        # Test migration tracking initialization
        await migration_manager.init_migration_tracking()
        print("✅ Migration tracking initialization test passed")
        
        # Test schema validation
        schema_validation = await migration_manager.validate_schema()
        assert 'tables' in schema_validation
        assert 'total_tables' in schema_validation
        assert 'valid' in schema_validation
        print("✅ Schema validation test passed")
        
        # Test migration history
        history = await migration_manager.get_migration_history()
        assert isinstance(history, list)
        print("✅ Migration history test passed")
        
        # Test completed migrations
        completed = await migration_manager.get_completed_migrations()
        assert isinstance(completed, list)
        print("✅ Completed migrations test passed")
        
        # Test pending migrations
        pending = await migration_manager.get_pending_migrations()
        assert isinstance(pending, list)
        print("✅ Pending migrations test passed")
        
        print("🎉 Migration management tests passed!")
        
    except Exception as e:
        print(f"❌ Migration management test failed: {e}")
        raise


async def test_integration():
    """Test integration of all components."""
    print("\n🔗 Testing Component Integration...")
    
    try:
        async for session in get_db_session():
            # Test cached repository with validation
            cached_repo = CachedPaymentRepository(session)
            validator = get_data_validator()
            
            # Create payment with validation
            payment_data = {
                'external_id': f'test_integration_{uuid.uuid4().hex[:8]}',
                'amount': Decimal('100.00'),
                'currency': 'USD',
                'status': PaymentStatus.PENDING.value,
                'payment_method': PaymentMethod.CREDIT_CARD.value,
                'customer_id': 'integration_customer',
                'customer_email': 'integration@example.com',
                'is_test': True
            }
            
            # Validate before creating
            validation_result = await validator.validate_model_data("Payment", payment_data, session)
            assert validation_result['valid'] == True
            
            # Create with caching
            payment = await cached_repo.create(payment_data)
            assert payment is not None
            
            # Test transaction with cached operations
            transaction_manager = get_transaction_manager()
            
            async with transaction_manager.transaction() as tx_session:
                cached_repo_tx = CachedPaymentRepository(tx_session)
                
                # Update within transaction
                update_data = {
                    'status': PaymentStatus.CAPTURED.value,
                    'processed_at': datetime.utcnow()
                }
                
                updated_payment = await cached_repo_tx.update(payment.id, update_data)
                assert updated_payment.status == PaymentStatus.CAPTURED.value
            
            print("✅ Integration test passed")
            
            # Clean up
            await cached_repo.delete(payment.id)
            
            break
        
        print("🎉 Integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise


async def main():
    """Run all database operation tests."""
    print("🚀 Starting EasyPay Database Operations Test Suite...")
    print("=" * 60)
    
    try:
        # Initialize database
        await init_database()
        print("✅ Database initialized successfully")
        
        # Run all tests
        await test_transaction_management()
        await test_cached_repository()
        await test_data_validation()
        await test_error_handling()
        await test_migration_management()
        await test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 All database operations tests passed successfully!")
        print("✅ Transaction management: Working")
        print("✅ Cached repositories: Working")
        print("✅ Data validation: Working")
        print("✅ Error handling: Working")
        print("✅ Migration management: Working")
        print("✅ Component integration: Working")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Database operations test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
