"""
EasyPay Payment Gateway - Error Recovery System

This module provides comprehensive error recovery mechanisms including:
- Global error handling middleware
- Error recovery strategies
- Dead letter queues
- Circuit breaker patterns
- Graceful shutdown handling
- Error reporting and monitoring
"""

import asyncio
import logging
import signal
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.exceptions import (
    EasyPayException, ValidationError, AuthenticationError, 
    AuthorizationError, PaymentError, ExternalServiceError,
    DatabaseError, CacheError, RateLimitError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(str, Enum):
    """Error recovery strategies."""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    DEAD_LETTER = "dead_letter"
    GRACEFUL_DEGRADATION = "graceful_degradation"


@dataclass
class ErrorContext:
    """Error context information."""
    error: Exception
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadLetterMessage:
    """Dead letter queue message."""
    id: str
    original_request: Dict[str, Any]
    error_context: ErrorContext
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 5
    next_retry_at: Optional[datetime] = None


class ErrorRecoveryManager:
    """Manages error recovery strategies and dead letter queues."""
    
    def __init__(self):
        self.dead_letter_queue: List[DeadLetterMessage] = []
        self.max_queue_size = 1000
        self.recovery_handlers: Dict[Type[Exception], Callable] = {}
        self.circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
        self.error_statistics: Dict[str, int] = {}
        self.is_shutting_down = False
        
        # Initialize default recovery handlers
        self._initialize_recovery_handlers()
    
    def _initialize_recovery_handlers(self):
        """Initialize default error recovery handlers."""
        self.recovery_handlers = {
            ValidationError: self._handle_validation_error,
            AuthenticationError: self._handle_auth_error,
            AuthorizationError: self._handle_auth_error,
            PaymentError: self._handle_payment_error,
            ExternalServiceError: self._handle_external_service_error,
            DatabaseError: self._handle_database_error,
            CacheError: self._handle_cache_error,
            RateLimitError: self._handle_rate_limit_error,
        }
    
    async def handle_error(self, error_context: ErrorContext) -> Any:
        """Handle error with appropriate recovery strategy."""
        error_type = type(error_context.error)
        error_key = f"{error_type.__name__}_{error_context.endpoint}"
        
        # Update error statistics
        self.error_statistics[error_key] = self.error_statistics.get(error_key, 0) + 1
        
        # Get recovery handler
        handler = self.recovery_handlers.get(error_type, self._handle_generic_error)
        
        try:
            return await handler(error_context)
        except Exception as recovery_error:
            logger.error(f"Error recovery failed: {recovery_error}")
            return await self._handle_recovery_failure(error_context, recovery_error)
    
    async def _handle_validation_error(self, context: ErrorContext) -> Any:
        """Handle validation errors."""
        context.severity = ErrorSeverity.LOW
        context.recovery_strategy = RecoveryStrategy.FALLBACK
        
        logger.warning(f"Validation error: {context.error}")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "validation_error",
                    "message": str(context.error),
                    "request_id": context.request_id
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_auth_error(self, context: ErrorContext) -> Any:
        """Handle authentication/authorization errors."""
        context.severity = ErrorSeverity.MEDIUM
        context.recovery_strategy = RecoveryStrategy.FALLBACK
        
        logger.warning(f"Auth error: {context.error}")
        return JSONResponse(
            status_code=401 if isinstance(context.error, AuthenticationError) else 403,
            content={
                "error": {
                    "type": "auth_error",
                    "message": "Authentication or authorization failed",
                    "request_id": context.request_id
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_payment_error(self, context: ErrorContext) -> Any:
        """Handle payment processing errors."""
        context.severity = ErrorSeverity.HIGH
        context.recovery_strategy = RecoveryStrategy.DEAD_LETTER
        
        logger.error(f"Payment error: {context.error}")
        
        # Add to dead letter queue for manual review
        await self._add_to_dead_letter_queue(context)
        
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "payment_error",
                    "message": "Payment processing failed",
                    "request_id": context.request_id
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_external_service_error(self, context: ErrorContext) -> Any:
        """Handle external service errors."""
        context.severity = ErrorSeverity.HIGH
        context.recovery_strategy = RecoveryStrategy.CIRCUIT_BREAKER
        
        # Get or create circuit breaker for the service
        service_name = context.metadata.get('service_name', 'unknown')
        circuit_breaker = self._get_circuit_breaker(service_name)
        
        if circuit_breaker.state == CircuitState.OPEN:
            logger.warning(f"Circuit breaker OPEN for service {service_name}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "service_unavailable",
                        "message": f"Service {service_name} is temporarily unavailable",
                        "request_id": context.request_id
                    },
                    "timestamp": context.timestamp.isoformat()
                }
            )
        
        # Try with circuit breaker
        try:
            return circuit_breaker.call(lambda: None)
        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "external_service_error",
                        "message": "External service temporarily unavailable",
                        "request_id": context.request_id
                    },
                    "timestamp": context.timestamp.isoformat()
                }
            )
    
    async def _handle_database_error(self, context: ErrorContext) -> Any:
        """Handle database errors."""
        context.severity = ErrorSeverity.CRITICAL
        context.recovery_strategy = RecoveryStrategy.RETRY
        
        if context.retry_count < context.max_retries:
            context.retry_count += 1
            delay = min(2 ** context.retry_count, 30)  # Exponential backoff, max 30s
            
            logger.warning(f"Database error, retrying in {delay}s (attempt {context.retry_count})")
            await asyncio.sleep(delay)
            
            # This would typically retry the original operation
            # For now, we'll return a retry response
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "database_error",
                        "message": "Database temporarily unavailable, please retry",
                        "request_id": context.request_id,
                        "retry_after": delay
                    },
                    "timestamp": context.timestamp.isoformat()
                }
            )
        else:
            # Max retries exceeded, add to dead letter queue
            await self._add_to_dead_letter_queue(context)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "database_error",
                        "message": "Database error after multiple retries",
                        "request_id": context.request_id
                    },
                    "timestamp": context.timestamp.isoformat()
                }
            )
    
    async def _handle_cache_error(self, context: ErrorContext) -> Any:
        """Handle cache errors."""
        context.severity = ErrorSeverity.MEDIUM
        context.recovery_strategy = RecoveryStrategy.GRACEFUL_DEGRADATION
        
        logger.warning(f"Cache error: {context.error}")
        
        # Graceful degradation - continue without cache
        return JSONResponse(
            status_code=200,
            content={
                "message": "Request processed with degraded performance",
                "request_id": context.request_id,
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_rate_limit_error(self, context: ErrorContext) -> Any:
        """Handle rate limit errors."""
        context.severity = ErrorSeverity.MEDIUM
        context.recovery_strategy = RecoveryStrategy.FALLBACK
        
        logger.warning(f"Rate limit exceeded: {context.error}")
        
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "type": "rate_limit_exceeded",
                    "message": "Rate limit exceeded",
                    "request_id": context.request_id,
                    "retry_after": 60
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_generic_error(self, context: ErrorContext) -> Any:
        """Handle generic errors."""
        context.severity = ErrorSeverity.HIGH
        context.recovery_strategy = RecoveryStrategy.DEAD_LETTER
        
        logger.error(f"Generic error: {context.error}")
        
        # Add to dead letter queue
        await self._add_to_dead_letter_queue(context)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "internal_error",
                    "message": "An internal error occurred",
                    "request_id": context.request_id
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _handle_recovery_failure(self, context: ErrorContext, recovery_error: Exception) -> Any:
        """Handle recovery failure."""
        logger.critical(f"Recovery failed for error: {context.error}, recovery error: {recovery_error}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "recovery_failure",
                    "message": "System recovery failed",
                    "request_id": context.request_id
                },
                "timestamp": context.timestamp.isoformat()
            }
        )
    
    async def _add_to_dead_letter_queue(self, context: ErrorContext):
        """Add failed request to dead letter queue."""
        if len(self.dead_letter_queue) >= self.max_queue_size:
            # Remove oldest message
            self.dead_letter_queue.pop(0)
        
        message = DeadLetterMessage(
            id=f"dlq_{int(time.time())}_{len(self.dead_letter_queue)}",
            original_request=context.metadata.get('request_data', {}),
            error_context=context,
            retry_count=context.retry_count,
            next_retry_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        self.dead_letter_queue.append(message)
        logger.info(f"Added message {message.id} to dead letter queue")
    
    def _get_circuit_breaker(self, service_name: str) -> 'CircuitBreaker':
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60
            )
        return self.circuit_breakers[service_name]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "error_counts": self.error_statistics,
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "circuit_breakers": {
                name: cb.get_metrics() 
                for name, cb in self.circuit_breakers.items()
            }
        }
    
    async def process_dead_letter_queue(self):
        """Process dead letter queue messages."""
        if self.is_shutting_down:
            return
        
        current_time = datetime.utcnow()
        messages_to_retry = []
        
        for message in self.dead_letter_queue:
            if (message.next_retry_at and 
                message.next_retry_at <= current_time and 
                message.retry_count < message.max_retries):
                messages_to_retry.append(message)
        
        for message in messages_to_retry:
            try:
                logger.info(f"Retrying dead letter message {message.id}")
                # Here you would retry the original request
                # For now, we'll just log it
                message.retry_count += 1
                message.next_retry_at = datetime.utcnow() + timedelta(minutes=5 * message.retry_count)
            except Exception as e:
                logger.error(f"Failed to retry dead letter message {message.id}: {e}")
                if message.retry_count >= message.max_retries:
                    self.dead_letter_queue.remove(message)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Enhanced circuit breaker implementation."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0,
            "circuit_closes": 0
        }
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        self.metrics["total_calls"] += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise ExternalServiceError("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.metrics["circuit_closes"] += 1
            logger.info("Circuit breaker closed after successful call")
        
        self.failure_count = 0
        self.metrics["successful_calls"] += 1
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.metrics["failed_calls"] += 1
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.metrics["circuit_opens"] += 1
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            **self.metrics,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_rate": (
                self.metrics["successful_calls"] / self.metrics["total_calls"]
                if self.metrics["total_calls"] > 0 else 0
            )
        }


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.recovery_manager = ErrorRecoveryManager()
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with error handling."""
        start_time = time.time()
        request_id = getattr(request.state, "request_id", None)
        
        try:
            response = await call_next(request)
            
            # Log successful requests
            processing_time = time.time() - start_time
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Time: {processing_time:.3f}s"
            )
            
            return response
            
        except EasyPayException as e:
            # Handle known EasyPay exceptions
            error_context = ErrorContext(
                error=e,
                request_id=request_id,
                endpoint=request.url.path,
                method=request.method,
                metadata={
                    "request_data": await self._get_request_data(request),
                    "processing_time": time.time() - start_time
                }
            )
            
            return await self.recovery_manager.handle_error(error_context)
            
        except Exception as e:
            # Handle unexpected exceptions
            error_context = ErrorContext(
                error=e,
                request_id=request_id,
                endpoint=request.url.path,
                method=request.method,
                severity=ErrorSeverity.CRITICAL,
                metadata={
                    "request_data": await self._get_request_data(request),
                    "processing_time": time.time() - start_time,
                    "traceback": traceback.format_exc()
                }
            )
            
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return await self.recovery_manager.handle_error(error_context)
    
    async def _get_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract request data for error context."""
        try:
            body = await request.body()
            return {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": body.decode() if body else None
            }
        except Exception:
            return {"method": request.method, "url": str(request.url)}


class GracefulShutdownManager:
    """Manages graceful shutdown of the application."""
    
    def __init__(self):
        self.shutdown_handlers: List[Callable] = []
        self.is_shutting_down = False
        self.shutdown_timeout = 30  # seconds
        self.logger = logging.getLogger(__name__)
    
    def register_shutdown_handler(self, handler: Callable):
        """Register a shutdown handler."""
        self.shutdown_handlers.append(handler)
    
    async def shutdown(self):
        """Perform graceful shutdown."""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        self.logger.info("Starting graceful shutdown...")
        
        # Set shutdown timeout
        try:
            await asyncio.wait_for(self._execute_shutdown_handlers(), timeout=self.shutdown_timeout)
        except asyncio.TimeoutError:
            self.logger.warning("Shutdown timeout exceeded, forcing shutdown")
        
        self.logger.info("Graceful shutdown completed")
    
    async def _execute_shutdown_handlers(self):
        """Execute all registered shutdown handlers."""
        for handler in self.shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                self.logger.error(f"Shutdown handler failed: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)


class ErrorReportingService:
    """Service for error reporting and monitoring."""
    
    def __init__(self):
        self.error_reports: List[Dict[str, Any]] = []
        self.max_reports = 1000
        self.logger = logging.getLogger(__name__)
    
    async def report_error(self, error_context: ErrorContext):
        """Report error for monitoring and alerting."""
        report = {
            "timestamp": error_context.timestamp.isoformat(),
            "error_type": type(error_context.error).__name__,
            "error_message": str(error_context.error),
            "severity": error_context.severity.value,
            "request_id": error_context.request_id,
            "endpoint": error_context.endpoint,
            "method": error_context.method,
            "retry_count": error_context.retry_count,
            "metadata": error_context.metadata
        }
        
        self.error_reports.append(report)
        
        # Trim reports if too many
        if len(self.error_reports) > self.max_reports:
            self.error_reports = self.error_reports[-self.max_reports:]
        
        # Log based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error reported: {report}")
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error reported: {report}")
        else:
            self.logger.warning(f"Error reported: {report}")
    
    def get_error_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent error reports."""
        return self.error_reports[-limit:] if self.error_reports else []


# Global instances
error_recovery_manager = ErrorRecoveryManager()
graceful_shutdown_manager = GracefulShutdownManager()
error_reporting_service = ErrorReportingService()
