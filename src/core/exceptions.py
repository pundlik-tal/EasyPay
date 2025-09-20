"""
EasyPay Payment Gateway - Core Exceptions
"""
from datetime import datetime
from typing import Optional


class EasyPayException(Exception):
    """Base exception class for EasyPay Payment Gateway."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        error_type: str = "api_error",
        status_code: int = 400,
        timestamp: Optional[datetime] = None
    ):
        self.message = message
        self.error_code = error_code
        self.error_type = error_type
        self.status_code = status_code
        self.timestamp = timestamp or datetime.utcnow()
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Return only the message without status code."""
        return self.message


class ValidationError(EasyPayException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, error_code: str = "validation_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="validation_error",
            status_code=400
        )


class AuthenticationError(EasyPayException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", error_code: str = "authentication_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="authentication_error",
            status_code=401
        )


class AuthorizationError(EasyPayException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied", error_code: str = "authorization_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="authorization_error",
            status_code=403
        )


class NotFoundError(EasyPayException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found", error_code: str = "not_found"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="not_found",
            status_code=404
        )


class ConflictError(EasyPayException):
    """Raised when there's a conflict with the current state."""
    
    def __init__(self, message: str = "Resource conflict", error_code: str = "conflict"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="conflict",
            status_code=409
        )


class RateLimitError(EasyPayException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", error_code: str = "rate_limit_exceeded"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="rate_limit_error",
            status_code=429
        )


class PaymentError(EasyPayException):
    """Raised when payment processing fails."""
    
    def __init__(self, message: str, error_code: str = "payment_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="payment_error",
            status_code=400
        )


class ExternalServiceError(EasyPayException):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str, error_code: str = "external_service_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="external_service_error",
            status_code=502
        )


class DatabaseError(EasyPayException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, error_code: str = "database_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="database_error",
            status_code=500
        )


class CacheError(EasyPayException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, error_code: str = "cache_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="cache_error",
            status_code=500
        )


class WebhookError(EasyPayException):
    """Raised when webhook processing fails."""
    
    def __init__(self, message: str, error_code: str = "webhook_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="webhook_error",
            status_code=400
        )


class PaymentNotFoundError(NotFoundError):
    """Raised when a payment is not found."""
    
    def __init__(self, message: str = "Payment not found", error_code: str = "payment_not_found"):
        super().__init__(
            message=message,
            error_code=error_code
        )


class WebhookNotFoundError(NotFoundError):
    """Raised when a webhook is not found."""
    
    def __init__(self, message: str = "Webhook not found", error_code: str = "webhook_not_found"):
        super().__init__(
            message=message,
            error_code=error_code
        )


class WebhookDeliveryError(WebhookError):
    """Raised when webhook delivery fails."""
    
    def __init__(self, message: str = "Webhook delivery failed", error_code: str = "webhook_delivery_error"):
        super().__init__(
            message=message,
            error_code=error_code
        )


class TransactionError(DatabaseError):
    """Raised when transaction operations fail."""
    
    def __init__(self, message: str, error_code: str = "transaction_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="transaction_error",
            status_code=500
        )


class MigrationError(DatabaseError):
    """Raised when migration operations fail."""
    
    def __init__(self, message: str, error_code: str = "migration_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="migration_error",
            status_code=500
        )