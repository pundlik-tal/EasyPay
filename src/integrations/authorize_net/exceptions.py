"""
EasyPay Payment Gateway - Authorize.net Exceptions
"""
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.exceptions import EasyPayException


class AuthorizeNetError(EasyPayException):
    """Base exception for Authorize.net related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "AUTHORIZE_NET_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            error_type="authorize_net_error",
            status_code=500,
            details=details or {}
        )


class AuthorizeNetAuthenticationError(AuthorizeNetError):
    """Exception for Authorize.net authentication errors."""
    
    def __init__(
        self,
        message: str = "Authorize.net authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZE_NET_AUTH_ERROR",
            details=details or {}
        )
        self.status_code = 401


class AuthorizeNetTransactionError(AuthorizeNetError):
    """Exception for Authorize.net transaction errors."""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        response_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if transaction_id:
            error_details["transaction_id"] = transaction_id
        if response_code:
            error_details["response_code"] = response_code
            
        super().__init__(
            message=message,
            error_code="AUTHORIZE_NET_TRANSACTION_ERROR",
            details=error_details
        )
        self.status_code = 400


class AuthorizeNetValidationError(AuthorizeNetError):
    """Exception for Authorize.net validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
            
        super().__init__(
            message=message,
            error_code="AUTHORIZE_NET_VALIDATION_ERROR",
            details=error_details
        )
        self.status_code = 422


class AuthorizeNetNetworkError(AuthorizeNetError):
    """Exception for Authorize.net network errors."""
    
    def __init__(
        self,
        message: str = "Network error communicating with Authorize.net",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZE_NET_NETWORK_ERROR",
            details=details or {}
        )
        self.status_code = 503
