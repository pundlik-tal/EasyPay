"""
EasyPay Payment Gateway - Database Package

This package contains all database-related infrastructure components including:
- Transaction management
- Migration management
- Data validation
- Error handling
"""

from .transaction_manager import (
    TransactionManager,
    TransactionIsolationLevel,
    TransactionError,
    get_transaction_manager,
    init_transaction_manager,
    close_transaction_manager
)

from .migration_manager import (
    MigrationManager,
    Migration,
    MigrationStatus,
    MigrationType,
    MigrationError
)

from .data_validator import (
    DataValidator,
    ValidationLevel,
    ValidationRule
)

from .error_handler import (
    DatabaseErrorHandler,
    DatabaseErrorInfo,
    ErrorSeverity,
    ErrorCategory
)

from .base import Base

__all__ = [
    # Database base
    'Base',
    
    # Transaction management
    'TransactionManager',
    'TransactionIsolationLevel',
    'TransactionError',
    'get_transaction_manager',
    'init_transaction_manager',
    'close_transaction_manager',
    
    # Migration management
    'MigrationManager',
    'Migration',
    'MigrationStatus',
    'MigrationType',
    'MigrationError',
    
    # Data validation
    'DataValidator',
    'ValidationLevel',
    'ValidationRule',
    
    # Error handling
    'DatabaseErrorHandler',
    'DatabaseErrorInfo',
    'ErrorSeverity',
    'ErrorCategory'
]
