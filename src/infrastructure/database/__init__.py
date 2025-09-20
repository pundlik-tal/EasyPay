"""
EasyPay Payment Gateway - Database Package

This package contains all database-related infrastructure components including:
- Transaction management
- Migration management
- Data validation
- Error handling
"""

# Import from db_components since that's where the actual modules are
from ..db_components.transaction_manager import (
    TransactionManager,
    TransactionIsolationLevel,
    TransactionError,
    get_transaction_manager,
    init_transaction_manager,
    close_transaction_manager
)

from ..db_components.migration_manager import (
    MigrationManager,
    Migration,
    MigrationStatus,
    MigrationType,
    MigrationError
)

from ..db_components.data_validator import (
    DataValidator,
    ValidationLevel,
    ValidationRule
)

from ..db_components.error_handler import (
    DatabaseErrorHandler,
    DatabaseErrorInfo,
    ErrorSeverity,
    ErrorCategory
)

from ..db_components.base import Base

# Import database initialization functions from the renamed module
from ..database_config import (
    init_database,
    get_db_session,
    close_database,
    get_migration_manager,
    get_data_validator,
    get_error_handler
)

# Database initialization functions are available in the parent database.py module
# Import them directly from there to avoid circular imports

__all__ = [
    # Database initialization
    'init_database',
    'get_db_session',
    'close_database',
    'get_migration_manager',
    'get_data_validator',
    'get_error_handler',
    
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
