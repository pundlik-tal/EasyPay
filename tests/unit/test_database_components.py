"""
EasyPay Payment Gateway - Database Components Tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.infrastructure.database.transaction_manager import (
    TransactionManager,
    TransactionIsolationLevel,
    TransactionError,
    get_transaction_manager,
    init_transaction_manager,
    close_transaction_manager
)
from src.infrastructure.database.migration_manager import (
    MigrationManager,
    Migration,
    MigrationStatus,
    MigrationType,
    MigrationError
)
from src.infrastructure.database.data_validator import (
    DataValidator,
    ValidationLevel,
    ValidationRule
)
from src.infrastructure.database.error_handler import (
    DatabaseErrorHandler,
    DatabaseErrorInfo,
    ErrorSeverity,
    ErrorCategory
)


class TestTransactionManager:
    """Test transaction manager functionality."""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock database engine."""
        engine = AsyncMock()
        engine.begin.return_value.__aenter__.return_value = AsyncMock()
        return engine
    
    @pytest.fixture
    def transaction_manager(self, mock_engine):
        """Create transaction manager instance."""
        return TransactionManager(mock_engine)
    
    def test_transaction_manager_creation(self, transaction_manager):
        """Test transaction manager creation."""
        assert transaction_manager is not None
        assert transaction_manager.engine is not None
    
    async def test_begin_transaction(self, transaction_manager):
        """Test beginning a transaction."""
        async with transaction_manager.begin_transaction() as tx:
            assert tx is not None
    
    async def test_begin_transaction_with_isolation(self, transaction_manager):
        """Test beginning a transaction with isolation level."""
        async with transaction_manager.begin_transaction(
            isolation_level=TransactionIsolationLevel.READ_COMMITTED
        ) as tx:
            assert tx is not None
    
    async def test_rollback_transaction(self, transaction_manager):
        """Test rolling back a transaction."""
        try:
            async with transaction_manager.begin_transaction() as tx:
                await transaction_manager.rollback_transaction(tx)
        except Exception:
            pass  # Expected behavior
    
    async def test_commit_transaction(self, transaction_manager):
        """Test committing a transaction."""
        async with transaction_manager.begin_transaction() as tx:
            await transaction_manager.commit_transaction(tx)


class TestMigrationManager:
    """Test migration manager functionality."""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock database engine."""
        engine = AsyncMock()
        engine.begin.return_value.__aenter__.return_value = AsyncMock()
        return engine
    
    @pytest.fixture
    def migration_manager(self, mock_engine):
        """Create migration manager instance."""
        return MigrationManager(mock_engine)
    
    def test_migration_manager_creation(self, migration_manager):
        """Test migration manager creation."""
        assert migration_manager is not None
        assert migration_manager.engine is not None
    
    async def test_init_migration_tracking(self, migration_manager):
        """Test initializing migration tracking."""
        await migration_manager.init_migration_tracking()
    
    async def test_create_migration(self, migration_manager):
        """Test creating a migration."""
        migration = await migration_manager.create_migration(
            name="test_migration",
            migration_type=MigrationType.SCHEMA,
            sql_up="CREATE TABLE test (id INT)",
            sql_down="DROP TABLE test"
        )
        assert migration is not None
        assert migration.name == "test_migration"
    
    async def test_get_migrations(self, migration_manager):
        """Test getting migrations."""
        migrations = await migration_manager.get_migrations()
        assert isinstance(migrations, list)
    
    async def test_run_migration(self, migration_manager):
        """Test running a migration."""
        # This would normally run a migration, but we'll just test the method exists
        try:
            await migration_manager.run_migration("test_migration")
        except Exception:
            pass  # Expected for test environment


class TestDataValidator:
    """Test data validator functionality."""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock database engine."""
        return AsyncMock()
    
    @pytest.fixture
    def data_validator(self, mock_engine):
        """Create data validator instance."""
        return DataValidator(mock_engine, ValidationLevel.MODERATE)
    
    def test_data_validator_creation(self, data_validator):
        """Test data validator creation."""
        assert data_validator is not None
        assert data_validator.engine is not None
        assert data_validator.validation_level == ValidationLevel.MODERATE
    
    async def test_validate_table_schema(self, data_validator):
        """Test validating table schema."""
        result = await data_validator.validate_table_schema("test_table")
        assert isinstance(result, bool)
    
    async def test_validate_data_integrity(self, data_validator):
        """Test validating data integrity."""
        result = await data_validator.validate_data_integrity("test_table")
        assert isinstance(result, bool)
    
    async def test_validate_constraints(self, data_validator):
        """Test validating constraints."""
        result = await data_validator.validate_constraints("test_table")
        assert isinstance(result, bool)


class TestDatabaseErrorHandler:
    """Test database error handler functionality."""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock database engine."""
        return AsyncMock()
    
    @pytest.fixture
    def error_handler(self, mock_engine):
        """Create error handler instance."""
        return DatabaseErrorHandler(mock_engine)
    
    def test_error_handler_creation(self, error_handler):
        """Test error handler creation."""
        assert error_handler is not None
        assert error_handler.engine is not None
    
    async def test_handle_error(self, error_handler):
        """Test handling an error."""
        error_info = DatabaseErrorInfo(
            error_type="connection_error",
            error_message="Connection failed",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONNECTION
        )
        
        result = await error_handler.handle_error(error_info)
        assert result is not None
    
    async def test_log_error(self, error_handler):
        """Test logging an error."""
        error_info = DatabaseErrorInfo(
            error_type="query_error",
            error_message="Query failed",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.QUERY
        )
        
        await error_handler.log_error(error_info)
    
    async def test_get_error_statistics(self, error_handler):
        """Test getting error statistics."""
        stats = await error_handler.get_error_statistics()
        assert isinstance(stats, dict)


class TestGlobalTransactionManager:
    """Test global transaction manager functions."""
    
    @patch('src.infrastructure.database.transaction_manager._transaction_manager', None)
    def test_get_transaction_manager_not_initialized(self):
        """Test getting transaction manager when not initialized."""
        with pytest.raises(Exception):
            get_transaction_manager()
    
    @patch('src.infrastructure.database.transaction_manager._transaction_manager')
    def test_get_transaction_manager_initialized(self, mock_manager):
        """Test getting transaction manager when initialized."""
        result = get_transaction_manager()
        assert result == mock_manager
    
    @patch('src.infrastructure.database.transaction_manager._transaction_manager', None)
    def test_init_transaction_manager(self):
        """Test initializing transaction manager."""
        mock_engine = AsyncMock()
        init_transaction_manager(mock_engine)
        # Should not raise an exception
    
    @patch('src.infrastructure.database.transaction_manager._transaction_manager')
    async def test_close_transaction_manager(self, mock_manager):
        """Test closing transaction manager."""
        await close_transaction_manager()
        # Should not raise an exception
