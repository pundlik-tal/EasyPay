"""
EasyPay Payment Gateway - Error Response Schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "type": "validation_error",
                        "code": "invalid_amount",
                        "message": "Amount must be greater than 0",
                        "param": "amount",
                        "request_id": "req_123456789"
                    },
                    "timestamp": "2024-01-01T00:00:00Z"
                },
                {
                    "error": {
                        "type": "authentication_error",
                        "code": "invalid_api_key",
                        "message": "Invalid API key provided",
                        "request_id": "req_123456789"
                    },
                    "timestamp": "2024-01-01T00:00:00Z"
                },
                {
                    "error": {
                        "type": "payment_error",
                        "code": "payment_failed",
                        "message": "Payment processing failed",
                        "request_id": "req_123456789"
                    },
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
        }
    }
    
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "validation_error",
                    "code": "validation_failed",
                    "message": "Request validation failed",
                    "details": [
                        {
                            "field": "amount",
                            "message": "Amount must be greater than 0",
                            "code": "invalid_amount"
                        },
                        {
                            "field": "currency",
                            "message": "Currency must be a 3-character code",
                            "code": "invalid_currency"
                        }
                    ],
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }
    
    error: Dict[str, Any] = Field(..., description="Validation error details")


class AuthenticationErrorResponse(ErrorResponse):
    """Authentication error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "authentication_error",
                    "code": "invalid_credentials",
                    "message": "Invalid API key or secret provided",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class AuthorizationErrorResponse(ErrorResponse):
    """Authorization error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "authorization_error",
                    "code": "insufficient_permissions",
                    "message": "Insufficient permissions for this operation",
                    "required_permission": "payments:write",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class NotFoundErrorResponse(ErrorResponse):
    """Not found error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "not_found",
                    "code": "payment_not_found",
                    "message": "Payment with ID 'pay_123456789' not found",
                    "resource_id": "pay_123456789",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class RateLimitErrorResponse(ErrorResponse):
    """Rate limit error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                    "message": "Rate limit exceeded",
                    "retry_after": 60,
                    "limit": 100,
                    "window": "minute",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class PaymentErrorResponse(ErrorResponse):
    """Payment processing error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "payment_error",
                    "code": "card_declined",
                    "message": "Card was declined by the issuer",
                    "processor_response_code": "05",
                    "processor_response_message": "Do not honor",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class ExternalServiceErrorResponse(ErrorResponse):
    """External service error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "external_service_error",
                    "code": "authorize_net_unavailable",
                    "message": "Authorize.net service is temporarily unavailable",
                    "service": "authorize_net",
                    "retry_after": 30,
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


class InternalErrorResponse(ErrorResponse):
    """Internal server error response."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "type": "internal_error",
                    "code": "unexpected_error",
                    "message": "An unexpected error occurred",
                    "request_id": "req_123456789"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


# HTTP Status Code Documentation
HTTP_STATUS_CODES = {
    200: "OK - Request successful",
    201: "Created - Resource created successfully",
    204: "No Content - Request successful, no content returned",
    400: "Bad Request - Invalid request data",
    401: "Unauthorized - Authentication required",
    403: "Forbidden - Insufficient permissions",
    404: "Not Found - Resource not found",
    409: "Conflict - Resource conflict",
    422: "Unprocessable Entity - Validation error",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - Server error",
    502: "Bad Gateway - External service error",
    503: "Service Unavailable - Service temporarily unavailable"
}

# Error Code Documentation
ERROR_CODES = {
    # Validation Errors
    "validation_error": "Request data validation failed",
    "invalid_amount": "Payment amount is invalid",
    "invalid_currency": "Currency code is invalid",
    "invalid_payment_method": "Payment method is invalid",
    "invalid_customer_id": "Customer ID is invalid",
    "invalid_date_range": "Date range is invalid",
    
    # Authentication Errors
    "authentication_error": "Authentication failed",
    "invalid_api_key": "API key is invalid",
    "invalid_credentials": "Invalid credentials provided",
    "expired_token": "Token has expired",
    "revoked_token": "Token has been revoked",
    
    # Authorization Errors
    "authorization_error": "Authorization failed",
    "insufficient_permissions": "Insufficient permissions",
    "access_denied": "Access denied",
    
    # Payment Errors
    "payment_error": "Payment processing failed",
    "payment_not_found": "Payment not found",
    "payment_already_processed": "Payment already processed",
    "payment_cannot_be_refunded": "Payment cannot be refunded",
    "payment_cannot_be_cancelled": "Payment cannot be cancelled",
    "card_declined": "Card was declined",
    "insufficient_funds": "Insufficient funds",
    "expired_card": "Card has expired",
    "invalid_card": "Invalid card information",
    
    # External Service Errors
    "external_service_error": "External service error",
    "authorize_net_unavailable": "Authorize.net service unavailable",
    "authorize_net_timeout": "Authorize.net service timeout",
    "authorize_net_error": "Authorize.net processing error",
    
    # Rate Limiting
    "rate_limit_exceeded": "Rate limit exceeded",
    "quota_exceeded": "API quota exceeded",
    
    # System Errors
    "internal_error": "Internal server error",
    "database_error": "Database operation failed",
    "cache_error": "Cache operation failed",
    "service_unavailable": "Service temporarily unavailable"
}
