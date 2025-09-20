"""
EasyPay Payment Gateway - Client Exceptions
"""


class EasyPayClientError(Exception):
    """Base exception for EasyPay client errors."""
    pass


class EasyPayAPIError(EasyPayClientError):
    """Exception raised for API-related errors."""
    
    def __init__(self, message: str, status_code: int = None, error_code: str = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(self.message)
    
    def __str__(self):
        return f"EasyPay API Error: {self.message} (Status: {self.status_code}, Code: {self.error_code})"


class EasyPayAuthError(EasyPayClientError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"EasyPay Auth Error: {self.message}"


class EasyPayValidationError(EasyPayClientError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, validation_errors: list = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.message)
    
    def __str__(self):
        return f"EasyPay Validation Error: {self.message}"


class EasyPayRateLimitError(EasyPayClientError):
    """Exception raised for rate limit errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
    
    def __str__(self):
        return f"EasyPay Rate Limit Error: {self.message}"


class EasyPayNetworkError(EasyPayClientError):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str = "Network error occurred"):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"EasyPay Network Error: {self.message}"
