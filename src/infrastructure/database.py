"""
EasyPay Payment Gateway - Database Infrastructure
"""
import os
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.infrastructure.database.base import Base

from src.core.exceptions import DatabaseError
from src.infrastructure.database.transaction_manager import init_transaction_manager, close_transaction_manager
from src.infrastructure.database.migration_manager import MigrationManager
from src.infrastructure.database.data_validator import DataValidator, ValidationLevel
from src.infrastructure.database.error_handler import DatabaseErrorHandler

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://easypay:password@localhost:5432/easypay")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    echo=os.getenv("DEBUG", "false").lower() == "true"
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Note: Base is imported from src.infrastructure.database.base

# Global instances
_migration_manager: Optional[MigrationManager] = None
_data_validator: Optional[DataValidator] = None
_error_handler: Optional[DatabaseErrorHandler] = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If session creation fails
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Database session error: {str(e)}")
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database connection and create tables.
    
    Raises:
        DatabaseError: If database initialization fails
    """
    try:
        # Test connection
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Initialize transaction manager
        init_transaction_manager(async_engine)
        
        # Initialize migration manager
        global _migration_manager
        _migration_manager = MigrationManager(async_engine)
        await _migration_manager.init_migration_tracking()
        
        # Initialize data validator
        global _data_validator
        _data_validator = DataValidator(async_engine, ValidationLevel.MODERATE)
        
        # Initialize error handler
        global _error_handler
        _error_handler = DatabaseErrorHandler(async_engine)
        
        # Log successful initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {str(e)}")


async def close_database() -> None:
    """
    Close database connections.
    
    Raises:
        DatabaseError: If database closure fails
    """
    try:
        # Close transaction manager
        await close_transaction_manager()
        
        # Clear global instances
        global _migration_manager, _data_validator, _error_handler
        _migration_manager = None
        _data_validator = None
        _error_handler = None
        
        # Dispose engine
        await async_engine.dispose()
        
        # Log successful closure
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to close database connections: {str(e)}")


def get_migration_manager() -> MigrationManager:
    """
    Get the global migration manager instance.
    
    Returns:
        MigrationManager: Global migration manager
        
    Raises:
        DatabaseError: If migration manager is not initialized
    """
    global _migration_manager
    
    if _migration_manager is None:
        raise DatabaseError("Migration manager not initialized")
    
    return _migration_manager


def get_data_validator() -> DataValidator:
    """
    Get the global data validator instance.
    
    Returns:
        DataValidator: Global data validator
        
    Raises:
        DatabaseError: If data validator is not initialized
    """
    global _data_validator
    
    if _data_validator is None:
        raise DatabaseError("Data validator not initialized")
    
    return _data_validator


def get_error_handler() -> DatabaseErrorHandler:
    """
    Get the global error handler instance.
    
    Returns:
        DatabaseErrorHandler: Global error handler
        
    Raises:
        DatabaseError: If error handler is not initialized
    """
    global _error_handler
    
    if _error_handler is None:
        raise DatabaseError("Error handler not initialized")
    
    return _error_handler
