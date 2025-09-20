"""
EasyPay Payment Gateway - Metrics Middleware
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.monitoring import (
    REQUEST_COUNT,
    REQUEST_DURATION,
    REQUEST_SIZE,
    RESPONSE_SIZE,
    ERROR_COUNT
)
import logging

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP metrics.
    
    This middleware automatically collects metrics for:
    - Request count by method, endpoint, and status code
    - Request duration
    - Request and response sizes
    - Error counts
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler
            
        Returns:
            FastAPI response object
        """
        # Record start time
        start_time = time.time()
        
        # Get request size
        request_size = 0
        if hasattr(request, '_body'):
            request_size = len(request._body) if request._body else 0
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Get response size
            response_size = 0
            if hasattr(response, 'body'):
                response_size = len(response.body) if response.body else 0
            
            # Record metrics
            self._record_metrics(
                request=request,
                response=response,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Record error metrics
            self._record_error_metrics(request, str(e), duration)
            
            # Re-raise the exception
            raise
    
    def _record_metrics(
        self,
        request: Request,
        response: Response,
        duration: float,
        request_size: int,
        response_size: int
    ) -> None:
        """
        Record HTTP metrics.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            duration: Request duration in seconds
            request_size: Request size in bytes
            response_size: Response size in bytes
        """
        try:
            # Extract endpoint (remove query parameters and fragments)
            endpoint = request.url.path
            method = request.method
            status_code = str(response.status_code)
            
            # Record request count
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            # Record request duration
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Record request size
            REQUEST_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
            
            # Record response size
            RESPONSE_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
            
            # Log request details
            logger.info(
                "HTTP request processed",
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {str(e)}")
    
    def _record_error_metrics(
        self,
        request: Request,
        error_message: str,
        duration: float
    ) -> None:
        """
        Record error metrics.
        
        Args:
            request: FastAPI request object
            error_message: Error message
            duration: Request duration in seconds
        """
        try:
            endpoint = request.url.path
            method = request.method
            
            # Record error count
            ERROR_COUNT.labels(
                error_type="http_error",
                severity="error"
            ).inc()
            
            # Record request count for failed requests
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code="500"
            ).inc()
            
            # Record request duration
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Log error details
            logger.error(
                "HTTP request failed",
                method=method,
                endpoint=endpoint,
                error=error_message,
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to record error metrics: {str(e)}")


class PaymentMetricsCollector:
    """Collector for payment-specific metrics."""
    
    @staticmethod
    def record_payment(
        status: str,
        currency: str,
        payment_method: str,
        amount: float,
        processing_time: float
    ) -> None:
        """
        Record payment metrics.
        
        Args:
            status: Payment status
            currency: Payment currency
            payment_method: Payment method used
            amount: Payment amount
            processing_time: Processing time in seconds
        """
        try:
            from src.infrastructure.monitoring import (
                PAYMENT_COUNT,
                PAYMENT_AMOUNT,
                PAYMENT_PROCESSING_TIME,
                REVENUE_TOTAL
            )
            
            # Record payment count
            PAYMENT_COUNT.labels(
                status=status,
                currency=currency,
                payment_method=payment_method
            ).inc()
            
            # Record payment amount
            PAYMENT_AMOUNT.labels(currency=currency).observe(amount)
            
            # Record processing time
            PAYMENT_PROCESSING_TIME.labels(status=status).observe(processing_time)
            
            # Record revenue (only for successful payments)
            if status in ['captured', 'settled']:
                REVENUE_TOTAL.labels(currency=currency).inc(amount)
            
            logger.info(
                "Payment metrics recorded",
                status=status,
                currency=currency,
                payment_method=payment_method,
                amount=amount,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to record payment metrics: {str(e)}")


class WebhookMetricsCollector:
    """Collector for webhook-specific metrics."""
    
    @staticmethod
    def record_webhook(
        event_type: str,
        status: str,
        source: str,
        delivery_time: float,
        retry_attempt: int = 0
    ) -> None:
        """
        Record webhook metrics.
        
        Args:
            event_type: Webhook event type
            status: Webhook processing status
            source: Webhook source
            delivery_time: Delivery time in seconds
            retry_attempt: Retry attempt number
        """
        try:
            from src.infrastructure.monitoring import (
                WEBHOOK_COUNT,
                WEBHOOK_DELIVERY_TIME,
                WEBHOOK_RETRY_COUNT
            )
            
            # Record webhook count
            WEBHOOK_COUNT.labels(
                event_type=event_type,
                status=status,
                source=source
            ).inc()
            
            # Record delivery time
            WEBHOOK_DELIVERY_TIME.labels(
                event_type=event_type,
                status=status
            ).observe(delivery_time)
            
            # Record retry count if applicable
            if retry_attempt > 0:
                WEBHOOK_RETRY_COUNT.labels(
                    event_type=event_type,
                    retry_attempt=str(retry_attempt)
                ).inc()
            
            logger.info(
                "Webhook metrics recorded",
                event_type=event_type,
                status=status,
                source=source,
                delivery_time=delivery_time,
                retry_attempt=retry_attempt
            )
            
        except Exception as e:
            logger.error(f"Failed to record webhook metrics: {str(e)}")


class AuthMetricsCollector:
    """Collector for authentication-specific metrics."""
    
    @staticmethod
    def record_auth_attempt(method: str, status: str) -> None:
        """
        Record authentication attempt.
        
        Args:
            method: Authentication method
            status: Authentication status
        """
        try:
            from src.infrastructure.monitoring import AUTH_ATTEMPTS
            
            AUTH_ATTEMPTS.labels(method=method, status=status).inc()
            
            logger.info(
                "Auth attempt recorded",
                method=method,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Failed to record auth metrics: {str(e)}")
    
    @staticmethod
    def record_auth_failure(method: str, reason: str) -> None:
        """
        Record authentication failure.
        
        Args:
            method: Authentication method
            reason: Failure reason
        """
        try:
            from src.infrastructure.monitoring import AUTH_FAILURES
            
            AUTH_FAILURES.labels(method=method, reason=reason).inc()
            
            logger.info(
                "Auth failure recorded",
                method=method,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Failed to record auth failure metrics: {str(e)}")


class DatabaseMetricsCollector:
    """Collector for database-specific metrics."""
    
    @staticmethod
    def record_query(operation: str, table: str, duration: float) -> None:
        """
        Record database query metrics.
        
        Args:
            operation: Database operation type
            table: Database table name
            duration: Query duration in seconds
        """
        try:
            from src.infrastructure.monitoring import DATABASE_QUERY_DURATION
            
            DATABASE_QUERY_DURATION.labels(
                operation=operation,
                table=table
            ).observe(duration)
            
            logger.debug(
                "Database query recorded",
                operation=operation,
                table=table,
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to record database metrics: {str(e)}")
    
    @staticmethod
    def record_error(operation: str, error_type: str) -> None:
        """
        Record database error.
        
        Args:
            operation: Database operation type
            error_type: Error type
        """
        try:
            from src.infrastructure.monitoring import DATABASE_ERRORS
            
            DATABASE_ERRORS.labels(
                operation=operation,
                error_type=error_type
            ).inc()
            
            logger.error(
                "Database error recorded",
                operation=operation,
                error_type=error_type
            )
            
        except Exception as e:
            logger.error(f"Failed to record database error metrics: {str(e)}")


class CacheMetricsCollector:
    """Collector for cache-specific metrics."""
    
    @staticmethod
    def record_hit(cache_type: str) -> None:
        """
        Record cache hit.
        
        Args:
            cache_type: Type of cache
        """
        try:
            from src.infrastructure.monitoring import CACHE_HITS
            
            CACHE_HITS.labels(cache_type=cache_type).inc()
            
            logger.debug("Cache hit recorded", cache_type=cache_type)
            
        except Exception as e:
            logger.error(f"Failed to record cache hit metrics: {str(e)}")
    
    @staticmethod
    def record_miss(cache_type: str) -> None:
        """
        Record cache miss.
        
        Args:
            cache_type: Type of cache
        """
        try:
            from src.infrastructure.monitoring import CACHE_MISSES
            
            CACHE_MISSES.labels(cache_type=cache_type).inc()
            
            logger.debug("Cache miss recorded", cache_type=cache_type)
            
        except Exception as e:
            logger.error(f"Failed to record cache miss metrics: {str(e)}")
    
    @staticmethod
    def record_operation(
        operation: str,
        cache_type: str,
        duration: float
    ) -> None:
        """
        Record cache operation metrics.
        
        Args:
            operation: Cache operation type
            cache_type: Type of cache
            duration: Operation duration in seconds
        """
        try:
            from src.infrastructure.monitoring import CACHE_OPERATION_DURATION
            
            CACHE_OPERATION_DURATION.labels(
                operation=operation,
                cache_type=cache_type
            ).observe(duration)
            
            logger.debug(
                "Cache operation recorded",
                operation=operation,
                cache_type=cache_type,
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to record cache operation metrics: {str(e)}")


class BusinessMetricsCollector:
    """Collector for business-specific metrics."""
    
    @staticmethod
    def record_fraud_detection(fraud_type: str, severity: str) -> None:
        """
        Record fraud detection.
        
        Args:
            fraud_type: Type of fraud detected
            severity: Severity level
        """
        try:
            from src.infrastructure.monitoring import FRAUD_DETECTIONS
            
            FRAUD_DETECTIONS.labels(
                fraud_type=fraud_type,
                severity=severity
            ).inc()
            
            logger.warning(
                "Fraud detection recorded",
                fraud_type=fraud_type,
                severity=severity
            )
            
        except Exception as e:
            logger.error(f"Failed to record fraud detection metrics: {str(e)}")
    
    @staticmethod
    def record_chargeback(reason: str, status: str) -> None:
        """
        Record chargeback.
        
        Args:
            reason: Chargeback reason
            status: Chargeback status
        """
        try:
            from src.infrastructure.monitoring import CHARGEBACK_COUNT
            
            CHARGEBACK_COUNT.labels(reason=reason, status=status).inc()
            
            logger.warning(
                "Chargeback recorded",
                reason=reason,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Failed to record chargeback metrics: {str(e)}")
