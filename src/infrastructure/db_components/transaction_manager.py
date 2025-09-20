"""
EasyPay Payment Gateway - Database Transaction Manager

This module provides advanced transaction management capabilities including:
- Nested transactions
- Transaction rollback handling
- Deadlock detection and retry
- Transaction isolation levels
- Bulk operations
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from src.core.exceptions import DatabaseError, TransactionError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionIsolationLevel(str, Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionManager:
    """
    Advanced transaction manager for database operations.
    
    Provides support for nested transactions, deadlock retry,
    and various isolation levels.
    """
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.session_factory = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[TransactionIsolationLevel] = None,
        retry_on_deadlock: bool = True,
        max_retries: int = 3
    ):
        """
        Create a database transaction context manager.
        
        Args:
            isolation_level: Transaction isolation level
            retry_on_deadlock: Whether to retry on deadlock
            max_retries: Maximum number of retries
            
        Yields:
            AsyncSession: Database session within transaction
        """
        session = None
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                session = self.session_factory()
                
                # Set isolation level if specified
                if isolation_level:
                    await session.execute(
                        text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}")
                    )
                
                # Begin transaction
                await session.begin()
                
                try:
                    yield session
                    await session.commit()
                    logger.debug("Transaction committed successfully")
                    break
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Transaction rolled back due to error: {e}")
                    
                    # Check if it's a deadlock and retry is enabled
                    if (retry_on_deadlock and 
                        retry_count < max_retries and 
                        self._is_deadlock_error(e)):
                        
                        retry_count += 1
                        logger.warning(f"Deadlock detected, retrying (attempt {retry_count})")
                        await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
                        continue
                    
                    raise TransactionError(f"Transaction failed: {str(e)}")
                    
            except Exception as e:
                if session:
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                raise TransactionError(f"Transaction setup failed: {str(e)}")
            
            finally:
                if session:
                    try:
                        await session.close()
                    except Exception:
                        pass
        
        if retry_count > max_retries:
            raise TransactionError(f"Transaction failed after {max_retries} retries")
    
    @asynccontextmanager
    async def nested_transaction(self, session: AsyncSession):
        """
        Create a nested transaction (savepoint) within an existing transaction.
        
        Args:
            session: Existing database session
            
        Yields:
            AsyncSession: Session with nested transaction
        """
        savepoint = await session.begin_nested()
        
        try:
            yield session
            await savepoint.commit()
            logger.debug("Nested transaction committed successfully")
            
        except Exception as e:
            await savepoint.rollback()
            logger.error(f"Nested transaction rolled back: {e}")
            raise TransactionError(f"Nested transaction failed: {str(e)}")
    
    async def execute_in_transaction(
        self,
        operation: Callable[[AsyncSession], T],
        isolation_level: Optional[TransactionIsolationLevel] = None,
        retry_on_deadlock: bool = True,
        max_retries: int = 3
    ) -> T:
        """
        Execute an operation within a transaction.
        
        Args:
            operation: Function to execute within transaction
            isolation_level: Transaction isolation level
            retry_on_deadlock: Whether to retry on deadlock
            max_retries: Maximum number of retries
            
        Returns:
            Result of the operation
            
        Raises:
            TransactionError: If transaction fails
        """
        async with self.transaction(
            isolation_level=isolation_level,
            retry_on_deadlock=retry_on_deadlock,
            max_retries=max_retries
        ) as session:
            return await operation(session)
    
    async def bulk_insert(
        self,
        model_class: Any,
        data_list: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> List[Any]:
        """
        Perform bulk insert operation.
        
        Args:
            model_class: SQLAlchemy model class
            data_list: List of data dictionaries
            batch_size: Number of records per batch
            
        Returns:
            List of inserted model instances
            
        Raises:
            TransactionError: If bulk insert fails
        """
        async with self.transaction() as session:
            inserted_objects = []
            
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                objects = [model_class(**data) for data in batch]
                session.add_all(objects)
                inserted_objects.extend(objects)
                
                # Commit batch to avoid memory issues
                await session.flush()
            
            await session.commit()
            return inserted_objects
    
    async def bulk_update(
        self,
        model_class: Any,
        updates: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Perform bulk update operation.
        
        Args:
            model_class: SQLAlchemy model class
            updates: List of update dictionaries with 'id' and update fields
            batch_size: Number of records per batch
            
        Returns:
            Number of updated records
            
        Raises:
            TransactionError: If bulk update fails
        """
        async with self.transaction() as session:
            updated_count = 0
            
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                
                for update_data in batch:
                    record_id = update_data.pop('id')
                    update_data.pop('id', None)  # Remove id from update data
                    
                    result = await session.execute(
                        text(f"UPDATE {model_class.__tablename__} SET "
                             f"{', '.join([f'{k} = :{k}' for k in update_data.keys()])} "
                             f"WHERE id = :id"),
                        {**update_data, 'id': record_id}
                    )
                    updated_count += result.rowcount
                
                await session.flush()
            
            await session.commit()
            return updated_count
    
    async def bulk_delete(
        self,
        model_class: Any,
        ids: List[Any],
        batch_size: int = 1000
    ) -> int:
        """
        Perform bulk delete operation.
        
        Args:
            model_class: SQLAlchemy model class
            ids: List of IDs to delete
            batch_size: Number of records per batch
            
        Returns:
            Number of deleted records
            
        Raises:
            TransactionError: If bulk delete fails
        """
        async with self.transaction() as session:
            deleted_count = 0
            
            for i in range(0, len(ids), batch_size):
                batch = ids[i:i + batch_size]
                
                result = await session.execute(
                    text(f"DELETE FROM {model_class.__tablename__} WHERE id = ANY(:ids)"),
                    {'ids': batch}
                )
                deleted_count += result.rowcount
                
                await session.flush()
            
            await session.commit()
            return deleted_count
    
    def _is_deadlock_error(self, error: Exception) -> bool:
        """
        Check if the error is a deadlock error.
        
        Args:
            error: Exception to check
            
        Returns:
            True if it's a deadlock error
        """
        error_str = str(error).lower()
        deadlock_indicators = [
            'deadlock',
            'lock timeout',
            'could not serialize access',
            'serialization failure'
        ]
        
        return any(indicator in error_str for indicator in deadlock_indicators)
    
    async def get_transaction_status(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Get current transaction status.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with transaction status information
        """
        try:
            # Get transaction isolation level
            result = await session.execute(
                text("SHOW transaction_isolation")
            )
            isolation_level = result.scalar()
            
            # Get current transaction ID
            result = await session.execute(
                text("SELECT txid_current()")
            )
            transaction_id = result.scalar()
            
            # Check if in transaction
            result = await session.execute(
                text("SELECT pg_backend_pid()")
            )
            backend_pid = result.scalar()
            
            return {
                'isolation_level': isolation_level,
                'transaction_id': transaction_id,
                'backend_pid': backend_pid,
                'in_transaction': session.in_transaction()
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {'error': str(e)}




# Global transaction manager instance
_transaction_manager: Optional[TransactionManager] = None


def get_transaction_manager() -> TransactionManager:
    """
    Get the global transaction manager instance.
    
    Returns:
        TransactionManager: Global transaction manager
        
    Raises:
        DatabaseError: If transaction manager is not initialized
    """
    global _transaction_manager
    
    if _transaction_manager is None:
        raise DatabaseError("Transaction manager not initialized")
    
    return _transaction_manager


def init_transaction_manager(engine: AsyncEngine) -> None:
    """
    Initialize the global transaction manager.
    
    Args:
        engine: SQLAlchemy async engine
        
    Raises:
        DatabaseError: If initialization fails
    """
    global _transaction_manager
    
    try:
        _transaction_manager = TransactionManager(engine)
        logger.info("Transaction manager initialized successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to initialize transaction manager: {str(e)}")


async def close_transaction_manager() -> None:
    """
    Close the transaction manager.
    
    Raises:
        DatabaseError: If closure fails
    """
    global _transaction_manager
    
    try:
        if _transaction_manager:
            _transaction_manager = None
            logger.info("Transaction manager closed successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to close transaction manager: {str(e)}")
