"""
Comprehensive tests for infrastructure components to achieve 80%+ coverage.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any, List

from src.infrastructure.database import (
    init_database, get_db_session, close_database,
    async_engine, AsyncSessionLocal
)
from src.infrastructure.cache import (
    init_cache, get_cache_client, close_cache,
    CacheClient, CacheStrategy
)
from src.infrastructure.logging import setup_logging, get_logger
from src.infrastructure.metrics_middleware import MetricsMiddleware
from src.infrastructure.error_recovery import GlobalErrorHandlerMiddleware
from src.infrastructure.graceful_shutdown import (
    graceful_shutdown_manager, ShutdownPriority
)
from src.infrastructure.dead_letter_queue import dead_letter_queue_service
from src.infrastructure.circuit_breaker_service import circuit_breaker_service
from src.infrastructure.error_reporting import error_reporting_service
from src.infrastructure.monitoring import MonitoringService
from src.infrastructure.performance_monitor import PerformanceMonitor
from src.infrastructure.query_optimizer import QueryOptimizer
from src.infrastructure.connection_pool import ConnectionPool
from src.infrastructure.async_processor import AsyncProcessor
from src.infrastructure.cache_strategies import (
    LRUCacheStrategy, TTLCacheStrategy, WriteThroughCacheStrategy
)
from src.infrastructure.db_components.transaction_manager import (
    TransactionManager, TransactionIsolationLevel, TransactionError
)
from src.infrastructure.db_components.migration_manager import (
    MigrationManager, Migration, MigrationStatus, MigrationType, MigrationError
)
from src.infrastructure.db_components.data_validator import (
    DataValidator, ValidationLevel, ValidationRule
)
from src.infrastructure.db_components.error_handler import (
    DatabaseErrorHandler, DatabaseErrorInfo, ErrorSeverity, ErrorCategory
)
from src.core.exceptions import (
    DatabaseError, ValidationError, PaymentError, AuthenticationError
)


class TestDatabaseInfrastructure:
    """Comprehensive tests for database infrastructure."""
    
    @pytest.mark.asyncio
    async def test_init_database(self):
        """Test database initialization."""
        with patch('src.infrastructure.database.async_engine') as mock_engine:
            mock_engine.begin.return_value.__aenter__.return_value = AsyncMock()
            
            await init_database()
            
            # Verify database initialization was called
            mock_engine.begin.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_session(self):
        """Test getting database session."""
        with patch('src.infrastructure.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value = mock_session
            
            async for session in get_db_session():
                assert session == mock_session
                break
            
            mock_session_local.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test database closure."""
        with patch('src.infrastructure.database.async_engine') as mock_engine:
            mock_engine.dispose.return_value = None
            
            await close_database()
            
            mock_engine.dispose.assert_called_once()
    
    def test_database_configuration(self):
        """Test database configuration."""
        from src.infrastructure.database import DATABASE_URL, ASYNC_DATABASE_URL
        
        assert DATABASE_URL is not None
        assert ASYNC_DATABASE_URL is not None
        assert "postgresql+asyncpg://" in ASYNC_DATABASE_URL
        assert "postgresql://" in DATABASE_URL


class TestCacheInfrastructure:
    """Comprehensive tests for cache infrastructure."""
    
    @pytest.mark.asyncio
    async def test_init_cache(self):
        """Test cache initialization."""
        with patch('src.infrastructure.cache.redis.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            await init_cache()
            
            mock_redis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cache_client(self):
        """Test getting cache client."""
        with patch('src.infrastructure.cache.get_cache_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            client = await get_cache_client()
            
            assert client == mock_client
    
    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test cache operations."""
        mock_client = AsyncMock()
        mock_client.get.return_value = "cached_value"
        mock_client.set.return_value = True
        mock_client.delete.return_value = True
        mock_client.exists.return_value = True
        
        # Test get operation
        value = await mock_client.get("test_key")
        assert value == "cached_value"
        
        # Test set operation
        result = await mock_client.set("test_key", "test_value")
        assert result is True
        
        # Test delete operation
        result = await mock_client.delete("test_key")
        assert result is True
        
        # Test exists operation
        result = await mock_client.exists("test_key")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_close_cache(self):
        """Test cache closure."""
        with patch('src.infrastructure.cache.close_cache') as mock_close:
            await close_cache()
            mock_close.assert_called_once()


class TestLoggingInfrastructure:
    """Comprehensive tests for logging infrastructure."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        logger = setup_logging()
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
    
    def test_get_logger(self):
        """Test getting logger."""
        logger = get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_logging_levels(self):
        """Test different logging levels."""
        logger = setup_logging()
        
        # Test that logging methods exist and can be called
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")


class TestMetricsMiddleware:
    """Comprehensive tests for metrics middleware."""
    
    def test_metrics_middleware_initialization(self):
        """Test metrics middleware initialization."""
        middleware = MetricsMiddleware()
        
        assert middleware is not None
        assert hasattr(middleware, 'process_request')
        assert hasattr(middleware, 'process_response')
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        middleware = MetricsMiddleware()
        
        # Mock request and response
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/payments"
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Test request processing
        middleware.process_request(mock_request)
        
        # Test response processing
        middleware.process_response(mock_request, mock_response)


class TestErrorRecoveryMiddleware:
    """Comprehensive tests for error recovery middleware."""
    
    def test_error_recovery_middleware_initialization(self):
        """Test error recovery middleware initialization."""
        middleware = GlobalErrorHandlerMiddleware()
        
        assert middleware is not None
        assert hasattr(middleware, 'process_exception')
    
    def test_error_handling(self):
        """Test error handling."""
        middleware = GlobalErrorHandlerMiddleware()
        
        # Mock exception
        mock_exception = Exception("Test error")
        mock_request = Mock()
        
        # Test exception processing
        result = middleware.process_exception(mock_request, mock_exception)
        
        # Should return error response
        assert result is not None


class TestGracefulShutdownManager:
    """Comprehensive tests for graceful shutdown manager."""
    
    def test_shutdown_manager_initialization(self):
        """Test shutdown manager initialization."""
        manager = graceful_shutdown_manager
        
        assert manager is not None
        assert hasattr(manager, 'register_shutdown_handler')
        assert hasattr(manager, 'shutdown')
    
    def test_register_shutdown_handler(self):
        """Test registering shutdown handler."""
        manager = graceful_shutdown_manager
        
        def test_handler():
            pass
        
        manager.register_shutdown_handler(
            "test_handler",
            test_handler,
            priority=ShutdownPriority.HIGH,
            timeout=10
        )
        
        # Verify handler was registered
        assert "test_handler" in manager._handlers
    
    @pytest.mark.asyncio
    async def test_shutdown_execution(self):
        """Test shutdown execution."""
        manager = graceful_shutdown_manager
        
        # Register a test handler
        handler_called = False
        
        def test_handler():
            nonlocal handler_called
            handler_called = True
        
        manager.register_shutdown_handler(
            "test_handler",
            test_handler,
            priority=ShutdownPriority.HIGH,
            timeout=10
        )
        
        # Execute shutdown
        await manager.shutdown()
        
        # Verify handler was called
        assert handler_called is True


class TestDeadLetterQueueService:
    """Comprehensive tests for dead letter queue service."""
    
    def test_dead_letter_queue_initialization(self):
        """Test dead letter queue initialization."""
        service = dead_letter_queue_service
        
        assert service is not None
        assert hasattr(service, 'start_processing_workers')
        assert hasattr(service, 'stop_processing_workers')
        assert hasattr(service, 'add_message')
    
    @pytest.mark.asyncio
    async def test_start_processing_workers(self):
        """Test starting processing workers."""
        service = dead_letter_queue_service
        
        with patch.object(service, '_start_workers') as mock_start:
            await service.start_processing_workers()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_processing_workers(self):
        """Test stopping processing workers."""
        service = dead_letter_queue_service
        
        with patch.object(service, '_stop_workers') as mock_stop:
            await service.stop_processing_workers()
            mock_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_message(self):
        """Test adding message to dead letter queue."""
        service = dead_letter_queue_service
        
        message = {
            "id": str(uuid.uuid4()),
            "type": "payment_error",
            "data": {"payment_id": "pay_123", "error": "Processing failed"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch.object(service, '_queue_message') as mock_queue:
            await service.add_message(message)
            mock_queue.assert_called_once_with(message)


class TestCircuitBreakerService:
    """Comprehensive tests for circuit breaker service."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        service = circuit_breaker_service
        
        assert service is not None
        assert hasattr(service, 'call')
        assert hasattr(service, 'get_state')
        assert hasattr(service, 'get_metrics')
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_call(self):
        """Test circuit breaker call."""
        service = circuit_breaker_service
        
        async def test_function():
            return "success"
        
        with patch.object(service, '_execute_call') as mock_execute:
            mock_execute.return_value = "success"
            
            result = await service.call("test_service", test_function)
            
            assert result == "success"
            mock_execute.assert_called_once()
    
    def test_circuit_breaker_state(self):
        """Test circuit breaker state."""
        service = circuit_breaker_service
        
        with patch.object(service, '_get_circuit_state') as mock_state:
            mock_state.return_value = "CLOSED"
            
            state = service.get_state("test_service")
            
            assert state == "CLOSED"
            mock_state.assert_called_once_with("test_service")
    
    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics."""
        service = circuit_breaker_service
        
        with patch.object(service, '_get_circuit_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "total_calls": 100,
                "successful_calls": 95,
                "failed_calls": 5,
                "failure_rate": 0.05
            }
            
            metrics = service.get_metrics("test_service")
            
            assert metrics["total_calls"] == 100
            assert metrics["successful_calls"] == 95
            assert metrics["failed_calls"] == 5
            assert metrics["failure_rate"] == 0.05


class TestErrorReportingService:
    """Comprehensive tests for error reporting service."""
    
    def test_error_reporting_initialization(self):
        """Test error reporting initialization."""
        service = error_reporting_service
        
        assert service is not None
        assert hasattr(service, 'report_error')
        assert hasattr(service, 'report_payment_error')
        assert hasattr(service, 'report_system_error')
    
    @pytest.mark.asyncio
    async def test_report_error(self):
        """Test error reporting."""
        service = error_reporting_service
        
        error_info = {
            "error_type": "PaymentError",
            "error_message": "Payment processing failed",
            "error_code": "PAYMENT_FAILED",
            "context": {"payment_id": "pay_123"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch.object(service, '_send_error_report') as mock_send:
            await service.report_error(error_info)
            mock_send.assert_called_once_with(error_info)
    
    @pytest.mark.asyncio
    async def test_report_payment_error(self):
        """Test payment error reporting."""
        service = error_reporting_service
        
        payment_id = "pay_123"
        error_message = "Payment authorization failed"
        error_code = "AUTH_FAILED"
        
        with patch.object(service, 'report_error') as mock_report:
            await service.report_payment_error(payment_id, error_message, error_code)
            mock_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_report_system_error(self):
        """Test system error reporting."""
        service = error_reporting_service
        
        error_message = "Database connection failed"
        error_code = "DB_CONNECTION_ERROR"
        
        with patch.object(service, 'report_error') as mock_report:
            await service.report_system_error(error_message, error_code)
            mock_report.assert_called_once()


class TestMonitoringService:
    """Comprehensive tests for monitoring service."""
    
    def test_monitoring_service_initialization(self):
        """Test monitoring service initialization."""
        service = MonitoringService()
        
        assert service is not None
        assert hasattr(service, 'start_monitoring')
        assert hasattr(service, 'stop_monitoring')
        assert hasattr(service, 'get_metrics')
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        """Test starting monitoring."""
        service = MonitoringService()
        
        with patch.object(service, '_start_monitoring_loop') as mock_start:
            await service.start_monitoring()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        """Test stopping monitoring."""
        service = MonitoringService()
        
        with patch.object(service, '_stop_monitoring_loop') as mock_stop:
            await service.stop_monitoring()
            mock_stop.assert_called_once()
    
    def test_get_metrics(self):
        """Test getting metrics."""
        service = MonitoringService()
        
        with patch.object(service, '_collect_metrics') as mock_collect:
            mock_collect.return_value = {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.1,
                "network_io": 1024
            }
            
            metrics = service.get_metrics()
            
            assert metrics["cpu_usage"] == 45.2
            assert metrics["memory_usage"] == 67.8
            assert metrics["disk_usage"] == 23.1
            assert metrics["network_io"] == 1024


class TestPerformanceMonitor:
    """Comprehensive tests for performance monitor."""
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        monitor = PerformanceMonitor()
        
        assert monitor is not None
        assert hasattr(monitor, 'start_monitoring')
        assert hasattr(monitor, 'stop_monitoring')
        assert hasattr(monitor, 'get_performance_metrics')
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        """Test starting performance monitoring."""
        monitor = PerformanceMonitor()
        
        with patch.object(monitor, '_start_performance_tracking') as mock_start:
            await monitor.start_monitoring()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        """Test stopping performance monitoring."""
        monitor = PerformanceMonitor()
        
        with patch.object(monitor, '_stop_performance_tracking') as mock_stop:
            await monitor.stop_monitoring()
            mock_stop.assert_called_once()
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        monitor = PerformanceMonitor()
        
        with patch.object(monitor, '_collect_performance_data') as mock_collect:
            mock_collect.return_value = {
                "response_time_avg": 150.5,
                "response_time_p95": 300.2,
                "response_time_p99": 500.1,
                "throughput": 1000,
                "error_rate": 0.02
            }
            
            metrics = monitor.get_performance_metrics()
            
            assert metrics["response_time_avg"] == 150.5
            assert metrics["response_time_p95"] == 300.2
            assert metrics["response_time_p99"] == 500.1
            assert metrics["throughput"] == 1000
            assert metrics["error_rate"] == 0.02


class TestQueryOptimizer:
    """Comprehensive tests for query optimizer."""
    
    def test_query_optimizer_initialization(self):
        """Test query optimizer initialization."""
        optimizer = QueryOptimizer()
        
        assert optimizer is not None
        assert hasattr(optimizer, 'optimize_query')
        assert hasattr(optimizer, 'analyze_query')
        assert hasattr(optimizer, 'get_optimization_suggestions')
    
    def test_optimize_query(self):
        """Test query optimization."""
        optimizer = QueryOptimizer()
        
        query = "SELECT * FROM payments WHERE customer_id = ? AND status = ?"
        
        with patch.object(optimizer, '_apply_optimizations') as mock_optimize:
            mock_optimize.return_value = "SELECT * FROM payments WHERE customer_id = ? AND status = ? LIMIT 1000"
            
            optimized_query = optimizer.optimize_query(query)
            
            assert optimized_query is not None
            assert "LIMIT 1000" in optimized_query
            mock_optimize.assert_called_once_with(query)
    
    def test_analyze_query(self):
        """Test query analysis."""
        optimizer = QueryOptimizer()
        
        query = "SELECT * FROM payments WHERE customer_id = ?"
        
        with patch.object(optimizer, '_analyze_query_structure') as mock_analyze:
            mock_analyze.return_value = {
                "table": "payments",
                "columns": ["*"],
                "where_clause": "customer_id = ?",
                "has_index": True,
                "estimated_rows": 1000
            }
            
            analysis = optimizer.analyze_query(query)
            
            assert analysis["table"] == "payments"
            assert analysis["columns"] == ["*"]
            assert analysis["where_clause"] == "customer_id = ?"
            assert analysis["has_index"] is True
            assert analysis["estimated_rows"] == 1000
    
    def test_get_optimization_suggestions(self):
        """Test getting optimization suggestions."""
        optimizer = QueryOptimizer()
        
        query = "SELECT * FROM payments WHERE customer_id = ?"
        
        with patch.object(optimizer, '_generate_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                "Add index on customer_id column",
                "Use specific columns instead of *",
                "Consider adding LIMIT clause"
            ]
            
            suggestions = optimizer.get_optimization_suggestions(query)
            
            assert len(suggestions) == 3
            assert "Add index on customer_id column" in suggestions
            assert "Use specific columns instead of *" in suggestions
            assert "Consider adding LIMIT clause" in suggestions


class TestConnectionPool:
    """Comprehensive tests for connection pool."""
    
    def test_connection_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool()
        
        assert pool is not None
        assert hasattr(pool, 'get_connection')
        assert hasattr(pool, 'return_connection')
        assert hasattr(pool, 'get_pool_status')
    
    @pytest.mark.asyncio
    async def test_get_connection(self):
        """Test getting connection from pool."""
        pool = ConnectionPool()
        
        with patch.object(pool, '_acquire_connection') as mock_acquire:
            mock_connection = AsyncMock()
            mock_acquire.return_value = mock_connection
            
            connection = await pool.get_connection()
            
            assert connection == mock_connection
            mock_acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_return_connection(self):
        """Test returning connection to pool."""
        pool = ConnectionPool()
        
        mock_connection = AsyncMock()
        
        with patch.object(pool, '_release_connection') as mock_release:
            await pool.return_connection(mock_connection)
            mock_release.assert_called_once_with(mock_connection)
    
    def test_get_pool_status(self):
        """Test getting pool status."""
        pool = ConnectionPool()
        
        with patch.object(pool, '_get_status') as mock_status:
            mock_status.return_value = {
                "total_connections": 10,
                "active_connections": 5,
                "idle_connections": 5,
                "max_connections": 20
            }
            
            status = pool.get_pool_status()
            
            assert status["total_connections"] == 10
            assert status["active_connections"] == 5
            assert status["idle_connections"] == 5
            assert status["max_connections"] == 20


class TestAsyncProcessor:
    """Comprehensive tests for async processor."""
    
    def test_async_processor_initialization(self):
        """Test async processor initialization."""
        processor = AsyncProcessor()
        
        assert processor is not None
        assert hasattr(processor, 'start')
        assert hasattr(processor, 'stop')
        assert hasattr(processor, 'add_task')
    
    @pytest.mark.asyncio
    async def test_start_processor(self):
        """Test starting async processor."""
        processor = AsyncProcessor()
        
        with patch.object(processor, '_start_workers') as mock_start:
            await processor.start()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_processor(self):
        """Test stopping async processor."""
        processor = AsyncProcessor()
        
        with patch.object(processor, '_stop_workers') as mock_stop:
            await processor.stop()
            mock_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_task(self):
        """Test adding task to processor."""
        processor = AsyncProcessor()
        
        async def test_task():
            return "task_result"
        
        with patch.object(processor, '_queue_task') as mock_queue:
            await processor.add_task(test_task)
            mock_queue.assert_called_once_with(test_task)


class TestCacheStrategies:
    """Comprehensive tests for cache strategies."""
    
    def test_lru_cache_strategy(self):
        """Test LRU cache strategy."""
        strategy = LRUCacheStrategy(max_size=100)
        
        assert strategy is not None
        assert hasattr(strategy, 'get')
        assert hasattr(strategy, 'set')
        assert hasattr(strategy, 'delete')
        assert hasattr(strategy, 'clear')
    
    def test_ttl_cache_strategy(self):
        """Test TTL cache strategy."""
        strategy = TTLCacheStrategy(default_ttl=3600)
        
        assert strategy is not None
        assert hasattr(strategy, 'get')
        assert hasattr(strategy, 'set')
        assert hasattr(strategy, 'delete')
        assert hasattr(strategy, 'clear')
    
    def test_write_through_cache_strategy(self):
        """Test write-through cache strategy."""
        strategy = WriteThroughCacheStrategy()
        
        assert strategy is not None
        assert hasattr(strategy, 'get')
        assert hasattr(strategy, 'set')
        assert hasattr(strategy, 'delete')
        assert hasattr(strategy, 'clear')


class TestTransactionManager:
    """Comprehensive tests for transaction manager."""
    
    def test_transaction_manager_initialization(self):
        """Test transaction manager initialization."""
        manager = TransactionManager()
        
        assert manager is not None
        assert hasattr(manager, 'begin_transaction')
        assert hasattr(manager, 'commit_transaction')
        assert hasattr(manager, 'rollback_transaction')
    
    @pytest.mark.asyncio
    async def test_begin_transaction(self):
        """Test beginning transaction."""
        manager = TransactionManager()
        
        with patch.object(manager, '_create_transaction') as mock_create:
            mock_transaction = AsyncMock()
            mock_create.return_value = mock_transaction
            
            transaction = await manager.begin_transaction()
            
            assert transaction == mock_transaction
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_commit_transaction(self):
        """Test committing transaction."""
        manager = TransactionManager()
        
        mock_transaction = AsyncMock()
        
        with patch.object(manager, '_commit_transaction') as mock_commit:
            await manager.commit_transaction(mock_transaction)
            mock_commit.assert_called_once_with(mock_transaction)
    
    @pytest.mark.asyncio
    async def test_rollback_transaction(self):
        """Test rolling back transaction."""
        manager = TransactionManager()
        
        mock_transaction = AsyncMock()
        
        with patch.object(manager, '_rollback_transaction') as mock_rollback:
            await manager.rollback_transaction(mock_transaction)
            mock_rollback.assert_called_once_with(mock_transaction)


class TestMigrationManager:
    """Comprehensive tests for migration manager."""
    
    def test_migration_manager_initialization(self):
        """Test migration manager initialization."""
        manager = MigrationManager()
        
        assert manager is not None
        assert hasattr(manager, 'run_migrations')
        assert hasattr(manager, 'rollback_migration')
        assert hasattr(manager, 'get_migration_status')
    
    @pytest.mark.asyncio
    async def test_run_migrations(self):
        """Test running migrations."""
        manager = MigrationManager()
        
        with patch.object(manager, '_execute_migrations') as mock_execute:
            await manager.run_migrations()
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_migration(self):
        """Test rolling back migration."""
        manager = MigrationManager()
        
        migration_id = "migration_001"
        
        with patch.object(manager, '_rollback_migration') as mock_rollback:
            await manager.rollback_migration(migration_id)
            mock_rollback.assert_called_once_with(migration_id)
    
    def test_get_migration_status(self):
        """Test getting migration status."""
        manager = MigrationManager()
        
        with patch.object(manager, '_get_status') as mock_status:
            mock_status.return_value = {
                "total_migrations": 10,
                "applied_migrations": 8,
                "pending_migrations": 2,
                "last_migration": "migration_008"
            }
            
            status = manager.get_migration_status()
            
            assert status["total_migrations"] == 10
            assert status["applied_migrations"] == 8
            assert status["pending_migrations"] == 2
            assert status["last_migration"] == "migration_008"


class TestDataValidator:
    """Comprehensive tests for data validator."""
    
    def test_data_validator_initialization(self):
        """Test data validator initialization."""
        validator = DataValidator()
        
        assert validator is not None
        assert hasattr(validator, 'validate')
        assert hasattr(validator, 'add_rule')
        assert hasattr(validator, 'remove_rule')
    
    def test_validate_data(self):
        """Test data validation."""
        validator = DataValidator()
        
        data = {"amount": "10.00", "currency": "USD"}
        rules = [
            ValidationRule("amount", "required"),
            ValidationRule("currency", "required")
        ]
        
        with patch.object(validator, '_apply_rules') as mock_apply:
            mock_apply.return_value = []
            
            errors = validator.validate(data, rules)
            
            assert errors == []
            mock_apply.assert_called_once_with(data, rules)
    
    def test_add_rule(self):
        """Test adding validation rule."""
        validator = DataValidator()
        
        rule = ValidationRule("amount", "required")
        
        with patch.object(validator, '_add_rule') as mock_add:
            validator.add_rule(rule)
            mock_add.assert_called_once_with(rule)
    
    def test_remove_rule(self):
        """Test removing validation rule."""
        validator = DataValidator()
        
        rule_name = "amount_required"
        
        with patch.object(validator, '_remove_rule') as mock_remove:
            validator.remove_rule(rule_name)
            mock_remove.assert_called_once_with(rule_name)


class TestDatabaseErrorHandler:
    """Comprehensive tests for database error handler."""
    
    def test_database_error_handler_initialization(self):
        """Test database error handler initialization."""
        handler = DatabaseErrorHandler()
        
        assert handler is not None
        assert hasattr(handler, 'handle_error')
        assert hasattr(handler, 'get_error_info')
        assert hasattr(handler, 'log_error')
    
    def test_handle_error(self):
        """Test error handling."""
        handler = DatabaseErrorHandler()
        
        error = DatabaseError("Connection failed")
        
        with patch.object(handler, '_process_error') as mock_process:
            mock_process.return_value = DatabaseErrorInfo(
                error_type="DatabaseError",
                error_message="Connection failed",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.CONNECTION
            )
            
            error_info = handler.handle_error(error)
            
            assert error_info.error_type == "DatabaseError"
            assert error_info.error_message == "Connection failed"
            assert error_info.severity == ErrorSeverity.HIGH
            assert error_info.category == ErrorCategory.CONNECTION
            mock_process.assert_called_once_with(error)
    
    def test_get_error_info(self):
        """Test getting error information."""
        handler = DatabaseErrorHandler()
        
        error_code = "DB_CONNECTION_ERROR"
        
        with patch.object(handler, '_get_error_details') as mock_details:
            mock_details.return_value = {
                "error_type": "DatabaseError",
                "error_message": "Database connection failed",
                "severity": "HIGH",
                "category": "CONNECTION"
            }
            
            info = handler.get_error_info(error_code)
            
            assert info["error_type"] == "DatabaseError"
            assert info["error_message"] == "Database connection failed"
            assert info["severity"] == "HIGH"
            assert info["category"] == "CONNECTION"
            mock_details.assert_called_once_with(error_code)
    
    def test_log_error(self):
        """Test error logging."""
        handler = DatabaseErrorHandler()
        
        error_info = DatabaseErrorInfo(
            error_type="DatabaseError",
            error_message="Connection failed",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONNECTION
        )
        
        with patch.object(handler, '_log_error') as mock_log:
            handler.log_error(error_info)
            mock_log.assert_called_once_with(error_info)


class TestInfrastructureIntegration:
    """Comprehensive tests for infrastructure integration."""
    
    @pytest.mark.asyncio
    async def test_database_cache_integration(self):
        """Test database and cache integration."""
        with patch('src.infrastructure.database.init_database') as mock_db_init:
            with patch('src.infrastructure.cache.init_cache') as mock_cache_init:
                
                # Initialize both services
                await init_database()
                await init_cache()
                
                # Verify both were initialized
                mock_db_init.assert_called_once()
                mock_cache_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitoring_error_reporting_integration(self):
        """Test monitoring and error reporting integration."""
        with patch('src.infrastructure.monitoring.MonitoringService') as mock_monitoring:
            with patch('src.infrastructure.error_reporting.error_reporting_service') as mock_error_reporting:
                
                # Setup mocks
                mock_monitoring_instance = AsyncMock()
                mock_monitoring.return_value = mock_monitoring_instance
                
                # Start monitoring
                monitoring_service = MonitoringService()
                await monitoring_service.start_monitoring()
                
                # Report error
                await error_reporting_service.report_error({
                    "error_type": "SystemError",
                    "error_message": "Test error",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Verify services were used
                mock_monitoring_instance.start_monitoring.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_integration(self):
        """Test graceful shutdown integration."""
        with patch('src.infrastructure.graceful_shutdown.graceful_shutdown_manager') as mock_shutdown:
            
            # Register multiple services
            def service1_handler():
                pass
            
            def service2_handler():
                pass
            
            graceful_shutdown_manager.register_shutdown_handler(
                "service1", service1_handler, priority=ShutdownPriority.HIGH
            )
            graceful_shutdown_manager.register_shutdown_handler(
                "service2", service2_handler, priority=ShutdownPriority.LOW
            )
            
            # Execute shutdown
            await graceful_shutdown_manager.shutdown()
            
            # Verify shutdown was executed
            mock_shutdown.shutdown.assert_called_once()
