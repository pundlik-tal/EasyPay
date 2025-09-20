"""
EasyPay Payment Gateway - Database Error Handler

This module provides comprehensive database error handling including:
- Error classification and mapping
- Retry logic for transient errors
- Deadlock detection and handling
- Connection pool management
- Error reporting and monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Type
from enum import Enum

from sqlalchemy.exc import (
    OperationalError, IntegrityError, DataError, ProgrammingError,
    DisconnectionError, TimeoutError, InvalidRequestError
)
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text

from src.core.exceptions import DatabaseError, ValidationError, ConflictError

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories."""
    CONNECTION = "connection"
    TRANSACTION = "transaction"
    DATA_INTEGRITY = "data_integrity"
    VALIDATION = "validation"
    DEADLOCK = "deadlock"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    SYNTAX = "syntax"
    CONSTRAINT = "constraint"
    UNKNOWN = "unknown"


class DatabaseErrorInfo:
    """
    Information about a database error.
    
    Attributes:
        error: Original exception
        category: Error category
        severity: Error severity
        retryable: Whether error is retryable
        retry_delay: Delay before retry
        max_retries: Maximum retry attempts
        error_code: Database-specific error code
        error_message: Human-readable error message
        context: Additional context information
    """
    
    def __init__(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        retryable: bool = False,
        retry_delay: float = 1.0,
        max_retries: int = 3,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.category = category
        self.severity = severity
        self.retryable = retryable
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.error_code = error_code
        self.error_message = error_message or str(error)
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.retry_count = 0


class DatabaseErrorHandler:
    """
    Comprehensive database error handler.
    
    Provides error classification, retry logic, and recovery strategies
    for various database error scenarios.
    """
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.error_patterns = self._initialize_error_patterns()
        self.retry_strategies = self._initialize_retry_strategies()
        self.error_history: List[DatabaseErrorInfo] = []
        self.max_history_size = 1000
    
    def _initialize_error_patterns(self) -> Dict[Type[Exception], Callable[[Exception], DatabaseErrorInfo]]:
        """Initialize error pattern matching."""
        return {
            OperationalError: self._handle_operational_error,
            IntegrityError: self._handle_integrity_error,
            DataError: self._handle_data_error,
            ProgrammingError: self._handle_programming_error,
            DisconnectionError: self._handle_disconnection_error,
            TimeoutError: self._handle_timeout_error,
            InvalidRequestError: self._handle_invalid_request_error,
        }
    
    def _initialize_retry_strategies(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize retry strategies for different error categories."""
        return {
            ErrorCategory.CONNECTION: {
                "retryable": True,
                "retry_delay": 1.0,
                "max_retries": 5,
                "backoff_multiplier": 2.0
            },
            ErrorCategory.DEADLOCK: {
                "retryable": True,
                "retry_delay": 0.1,
                "max_retries": 3,
                "backoff_multiplier": 1.5
            },
            ErrorCategory.TIMEOUT: {
                "retryable": True,
                "retry_delay": 2.0,
                "max_retries": 3,
                "backoff_multiplier": 2.0
            },
            ErrorCategory.TRANSACTION: {
                "retryable": True,
                "retry_delay": 0.5,
                "max_retries": 2,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.DATA_INTEGRITY: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.VALIDATION: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.CONSTRAINT: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.PERMISSION: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.SYNTAX: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            },
            ErrorCategory.UNKNOWN: {
                "retryable": False,
                "retry_delay": 0.0,
                "max_retries": 0,
                "backoff_multiplier": 1.0
            }
        }
    
    def classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> DatabaseErrorInfo:
        """
        Classify a database error.
        
        Args:
            error: Exception to classify
            context: Additional context information
            
        Returns:
            DatabaseErrorInfo: Classified error information
        """
        try:
            # Try to match error type
            error_type = type(error)
            if error_type in self.error_patterns:
                error_info = self.error_patterns[error_type](error)
            else:
                # Unknown error type
                error_info = DatabaseErrorInfo(
                    error=error,
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.MEDIUM,
                    error_message=f"Unknown database error: {str(error)}",
                    context=context
                )
            
            # Add context information
            if context:
                error_info.context.update(context)
            
            # Store in history
            self._add_to_history(error_info)
            
            return error_info
            
        except Exception as e:
            logger.error(f"Error classification failed: {e}")
            # Return generic error info
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                error_message=f"Error classification failed: {str(e)}",
                context=context
            )
    
    def _handle_operational_error(self, error: OperationalError) -> DatabaseErrorInfo:
        """Handle operational errors."""
        error_str = str(error).lower()
        
        if "connection" in error_str or "connect" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.CONNECTION,
                severity=ErrorSeverity.HIGH,
                retryable=True,
                retry_delay=2.0,
                max_retries=5,
                error_message="Database connection error"
            )
        elif "deadlock" in error_str or "lock timeout" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.DEADLOCK,
                severity=ErrorSeverity.MEDIUM,
                retryable=True,
                retry_delay=0.1,
                max_retries=3,
                error_message="Database deadlock detected"
            )
        elif "timeout" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                retryable=True,
                retry_delay=1.0,
                max_retries=3,
                error_message="Database operation timeout"
            )
        else:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.CONNECTION,
                severity=ErrorSeverity.MEDIUM,
                retryable=True,
                retry_delay=1.0,
                max_retries=2,
                error_message="Database operational error"
            )
    
    def _handle_integrity_error(self, error: IntegrityError) -> DatabaseErrorInfo:
        """Handle integrity errors."""
        error_str = str(error).lower()
        
        if "unique" in error_str or "duplicate" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.CONSTRAINT,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Unique constraint violation"
            )
        elif "foreign key" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.CONSTRAINT,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Foreign key constraint violation"
            )
        elif "check" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.CONSTRAINT,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Check constraint violation"
            )
        else:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.DATA_INTEGRITY,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Data integrity violation"
            )
    
    def _handle_data_error(self, error: DataError) -> DatabaseErrorInfo:
        """Handle data errors."""
        error_str = str(error).lower()
        
        if "invalid" in error_str or "malformed" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Invalid data format"
            )
        elif "out of range" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Data value out of range"
            )
        else:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                error_message="Data validation error"
            )
    
    def _handle_programming_error(self, error: ProgrammingError) -> DatabaseErrorInfo:
        """Handle programming errors."""
        error_str = str(error).lower()
        
        if "syntax" in error_str or "parse" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.SYNTAX,
                severity=ErrorSeverity.HIGH,
                retryable=False,
                error_message="SQL syntax error"
            )
        elif "permission" in error_str or "access" in error_str:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                retryable=False,
                error_message="Database permission error"
            )
        else:
            return DatabaseErrorInfo(
                error=error,
                category=ErrorCategory.SYNTAX,
                severity=ErrorSeverity.HIGH,
                retryable=False,
                error_message="SQL programming error"
            )
    
    def _handle_disconnection_error(self, error: DisconnectionError) -> DatabaseErrorInfo:
        """Handle disconnection errors."""
        return DatabaseErrorInfo(
            error=error,
            category=ErrorCategory.CONNECTION,
            severity=ErrorSeverity.HIGH,
            retryable=True,
            retry_delay=2.0,
            max_retries=5,
            error_message="Database connection lost"
        )
    
    def _handle_timeout_error(self, error: TimeoutError) -> DatabaseErrorInfo:
        """Handle timeout errors."""
        return DatabaseErrorInfo(
            error=error,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            retry_delay=1.0,
            max_retries=3,
            error_message="Database operation timeout"
        )
    
    def _handle_invalid_request_error(self, error: InvalidRequestError) -> DatabaseErrorInfo:
        """Handle invalid request errors."""
        return DatabaseErrorInfo(
            error=error,
            category=ErrorCategory.SYNTAX,
            severity=ErrorSeverity.MEDIUM,
            retryable=False,
            error_message="Invalid database request"
        )
    
    async def execute_with_retry(
        self,
        operation: Callable,
        error_info: DatabaseErrorInfo,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Function to execute
            error_info: Error information
            context: Additional context
            
        Returns:
            Result of the operation
            
        Raises:
            DatabaseError: If operation fails after retries
        """
        if not error_info.retryable:
            raise self._create_database_error(error_info)
        
        retry_count = 0
        last_error = error_info.error
        
        while retry_count < error_info.max_retries:
            try:
                return await operation()
                
            except Exception as e:
                retry_count += 1
                last_error = e
                
                # Re-classify the new error
                new_error_info = self.classify_error(e, context)
                
                # Check if we should continue retrying
                if not new_error_info.retryable or retry_count >= new_error_info.max_retries:
                    break
                
                # Calculate retry delay with exponential backoff
                delay = error_info.retry_delay * (2 ** (retry_count - 1))
                
                logger.warning(
                    f"Database operation failed (attempt {retry_count}/{error_info.max_retries}), "
                    f"retrying in {delay}s: {str(e)}"
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        final_error_info = self.classify_error(last_error, context)
        raise self._create_database_error(final_error_info)
    
    def _create_database_error(self, error_info: DatabaseErrorInfo) -> DatabaseError:
        """
        Create appropriate database error from error info.
        
        Args:
            error_info: Error information
            
        Returns:
            DatabaseError: Appropriate exception
        """
        error_code = error_info.error_code or f"{error_info.category.value}_error"
        
        if error_info.category == ErrorCategory.CONSTRAINT:
            return ConflictError(
                message=error_info.error_message,
                error_code=error_code
            )
        elif error_info.category == ErrorCategory.VALIDATION:
            return ValidationError(
                message=error_info.error_message,
                error_code=error_code
            )
        else:
            return DatabaseError(
                message=error_info.error_message,
                error_code=error_code
            )
    
    def _add_to_history(self, error_info: DatabaseErrorInfo):
        """Add error to history."""
        self.error_history.append(error_info)
        
        # Trim history if it gets too large
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def get_error_statistics(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Args:
            time_window: Time window for statistics
            
        Returns:
            Dictionary with error statistics
        """
        try:
            if time_window:
                cutoff_time = datetime.utcnow() - time_window
                recent_errors = [
                    error for error in self.error_history
                    if error.timestamp >= cutoff_time
                ]
            else:
                recent_errors = self.error_history
            
            # Count errors by category
            category_counts = {}
            severity_counts = {}
            retryable_count = 0
            
            for error in recent_errors:
                category = error.category.value
                severity = error.severity.value
                
                category_counts[category] = category_counts.get(category, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                if error.retryable:
                    retryable_count += 1
            
            return {
                "total_errors": len(recent_errors),
                "category_counts": category_counts,
                "severity_counts": severity_counts,
                "retryable_count": retryable_count,
                "retryable_percentage": (retryable_count / len(recent_errors) * 100) if recent_errors else 0,
                "time_window": str(time_window) if time_window else "all_time"
            }
            
        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {"error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection.
        
        Returns:
            Dictionary with connection test results
        """
        try:
            async with self.engine.begin() as conn:
                # Test basic query
                result = await conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value == 1:
                    return {
                        "status": "success",
                        "message": "Database connection successful",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Database connection test failed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            error_info = self.classify_error(e)
            return {
                "status": "error",
                "message": f"Database connection failed: {error_info.error_message}",
                "error_category": error_info.category.value,
                "error_severity": error_info.severity.value,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool status.
        
        Returns:
            Dictionary with pool status information
        """
        try:
            pool = self.engine.pool
            
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "status": "healthy" if pool.checkedin() > 0 else "warning"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get pool status: {str(e)}"
            }
    
    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        logger.info("Error history cleared")
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error information
        """
        try:
            recent_errors = self.error_history[-limit:]
            
            return [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "retryable": error.retryable,
                    "error_message": error.error_message,
                    "error_code": error.error_code,
                    "context": error.context
                }
                for error in recent_errors
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
