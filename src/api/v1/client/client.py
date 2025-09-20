"""
EasyPay Payment Gateway - Python Client SDK
"""
import asyncio
import json
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
import httpx
from httpx import AsyncClient, Response

from .exceptions import (
    EasyPayClientError,
    EasyPayAPIError,
    EasyPayAuthError,
    EasyPayValidationError,
    EasyPayRateLimitError,
    EasyPayNetworkError
)


class EasyPayClient:
    """
    EasyPay Payment Gateway Python Client SDK
    
    This client provides a simple interface to interact with the EasyPay Payment Gateway API.
    It handles authentication, request/response serialization, and error handling.
    
    Example:
        ```python
        import asyncio
        from easypay import EasyPayClient
        
        async def main():
            # Initialize client
            client = EasyPayClient(
                api_key_id="ak_123456789",
                api_key_secret="sk_123456789",
                base_url="https://api.easypay.com"
            )
            
            # Create a payment
            payment = await client.payments.create({
                "amount": "25.99",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": "cust_123",
                "customer_email": "customer@example.com",
                "card_token": "tok_visa_4242",
                "description": "Test payment"
            })
            
            print(f"Payment created: {payment['id']}")
            
            # Get payment details
            payment_details = await client.payments.get(payment['id'])
            print(f"Payment status: {payment_details['status']}")
        
        asyncio.run(main())
        ```
    """
    
    def __init__(
        self,
        api_key_id: str,
        api_key_secret: str,
        base_url: str = "https://api.easypay.com",
        api_version: str = "v1",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the EasyPay client.
        
        Args:
            api_key_id: Your API key ID
            api_key_secret: Your API key secret
            base_url: Base URL for the API (default: https://api.easypay.com)
            api_version: API version to use (default: v1)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.base_url = base_url.rstrip('/')
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize HTTP client
        self._client: Optional[AsyncClient] = None
        
        # Initialize sub-clients
        self.payments = PaymentClient(self)
        self.auth = AuthClient(self)
        self.health = HealthClient(self)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "EasyPay-Python-SDK/1.0.0",
                    "Content-Type": "application/json",
                    "API-Version": self.api_version
                }
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict containing the response data
            
        Raises:
            EasyPayAPIError: For API errors
            EasyPayAuthError: For authentication errors
            EasyPayRateLimitError: For rate limit errors
            EasyPayNetworkError: For network errors
        """
        await self._ensure_client()
        
        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Prepare request data
        request_data = None
        if data:
            request_data = json.dumps(data, default=self._json_serializer)
        
        # Make request with retries
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    content=request_data,
                    params=params,
                    headers=request_headers
                )
                
                return await self._handle_response(response)
                
            except httpx.TimeoutException as e:
                last_exception = EasyPayNetworkError(f"Request timeout: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise last_exception
                
            except httpx.ConnectError as e:
                last_exception = EasyPayNetworkError(f"Connection error: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise last_exception
                
            except httpx.HTTPError as e:
                raise EasyPayNetworkError(f"HTTP error: {str(e)}")
        
        raise last_exception
    
    async def _handle_response(self, response: Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"message": response.text}
        
        # Handle different status codes
        if response.status_code == 200 or response.status_code == 201:
            return response_data
        
        elif response.status_code == 400:
            error_data = response_data.get("error", {})
            if "details" in error_data:
                raise EasyPayValidationError(
                    error_data.get("message", "Validation error"),
                    error_data.get("details", [])
                )
            else:
                raise EasyPayAPIError(
                    error_data.get("message", "Bad request"),
                    status_code=400,
                    error_code=error_data.get("code"),
                    response_data=response_data
                )
        
        elif response.status_code == 401:
            error_data = response_data.get("error", {})
            raise EasyPayAuthError(error_data.get("message", "Authentication failed"))
        
        elif response.status_code == 403:
            error_data = response_data.get("error", {})
            raise EasyPayAPIError(
                error_data.get("message", "Access denied"),
                status_code=403,
                error_code=error_data.get("code"),
                response_data=response_data
            )
        
        elif response.status_code == 404:
            error_data = response_data.get("error", {})
            raise EasyPayAPIError(
                error_data.get("message", "Resource not found"),
                status_code=404,
                error_code=error_data.get("code"),
                response_data=response_data
            )
        
        elif response.status_code == 429:
            error_data = response_data.get("error", {})
            retry_after = error_data.get("retry_after")
            raise EasyPayRateLimitError(
                error_data.get("message", "Rate limit exceeded"),
                retry_after=retry_after
            )
        
        elif response.status_code >= 500:
            error_data = response_data.get("error", {})
            raise EasyPayAPIError(
                error_data.get("message", "Internal server error"),
                status_code=response.status_code,
                error_code=error_data.get("code"),
                response_data=response_data
            )
        
        else:
            error_data = response_data.get("error", {})
            raise EasyPayAPIError(
                error_data.get("message", "Unknown error"),
                status_code=response.status_code,
                error_code=error_data.get("code"),
                response_data=response_data
            )
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for special types."""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with the API and get JWT tokens.
        
        Returns:
            Dict containing access and refresh tokens
        """
        data = {
            "api_key_id": self.api_key_id,
            "api_key_secret": self.api_key_secret
        }
        
        return await self._make_request(
            "POST",
            f"/api/{self.api_version}/auth/tokens",
            data=data
        )


class PaymentClient:
    """Client for payment-related operations."""
    
    def __init__(self, client: EasyPayClient):
        self._client = client
    
    async def create(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new payment.
        
        Args:
            payment_data: Payment creation data
            
        Returns:
            Dict containing the created payment
        """
        return await self._client._make_request(
            "POST",
            f"/api/{self._client.api_version}/payments",
            data=payment_data
        )
    
    async def get(self, payment_id: str) -> Dict[str, Any]:
        """
        Get a payment by ID.
        
        Args:
            payment_id: Payment ID (UUID or external ID)
            
        Returns:
            Dict containing the payment data
        """
        return await self._client._make_request(
            "GET",
            f"/api/{self._client.api_version}/payments/{payment_id}"
        )
    
    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List payments with optional filtering.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page (1-100)
            customer_id: Filter by customer ID
            status: Filter by payment status
            
        Returns:
            Dict containing the list of payments
        """
        params = {
            "page": page,
            "per_page": per_page
        }
        if customer_id:
            params["customer_id"] = customer_id
        if status:
            params["status"] = status
        
        return await self._client._make_request(
            "GET",
            f"/api/{self._client.api_version}/payments",
            params=params
        )
    
    async def update(self, payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a payment.
        
        Args:
            payment_id: Payment ID to update
            update_data: Update data
            
        Returns:
            Dict containing the updated payment
        """
        return await self._client._make_request(
            "PUT",
            f"/api/{self._client.api_version}/payments/{payment_id}",
            data=update_data
        )
    
    async def refund(
        self,
        payment_id: str,
        amount: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment.
        
        Args:
            payment_id: Payment ID to refund
            amount: Refund amount (optional, defaults to full refund)
            reason: Refund reason
            metadata: Additional metadata
            
        Returns:
            Dict containing the updated payment
        """
        refund_data = {}
        if amount:
            refund_data["amount"] = amount
        if reason:
            refund_data["reason"] = reason
        if metadata:
            refund_data["metadata"] = metadata
        
        return await self._client._make_request(
            "POST",
            f"/api/{self._client.api_version}/payments/{payment_id}/refund",
            data=refund_data
        )
    
    async def cancel(
        self,
        payment_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cancel a payment.
        
        Args:
            payment_id: Payment ID to cancel
            reason: Cancellation reason
            metadata: Additional metadata
            
        Returns:
            Dict containing the updated payment
        """
        cancel_data = {}
        if reason:
            cancel_data["reason"] = reason
        if metadata:
            cancel_data["metadata"] = metadata
        
        return await self._client._make_request(
            "POST",
            f"/api/{self._client.api_version}/payments/{payment_id}/cancel",
            data=cancel_data
        )


class AuthClient:
    """Client for authentication-related operations."""
    
    def __init__(self, client: EasyPayClient):
        self._client = client
    
    async def create_api_key(self, api_key_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            api_key_data: API key creation data
            
        Returns:
            Dict containing the created API key
        """
        return await self._client._make_request(
            "POST",
            f"/api/{self._client.api_version}/auth/api-keys",
            data=api_key_data
        )
    
    async def list_api_keys(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List API keys.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            
        Returns:
            Dict containing the list of API keys
        """
        params = {
            "skip": skip,
            "limit": limit
        }
        if status:
            params["status"] = status
        
        return await self._client._make_request(
            "GET",
            f"/api/{self._client.api_version}/auth/api-keys",
            params=params
        )
    
    async def get_api_key(self, api_key_id: str) -> Dict[str, Any]:
        """
        Get an API key by ID.
        
        Args:
            api_key_id: API key ID
            
        Returns:
            Dict containing the API key data
        """
        return await self._client._make_request(
            "GET",
            f"/api/{self._client.api_version}/auth/api-keys/{api_key_id}"
        )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict containing new tokens
        """
        data = {"refresh_token": refresh_token}
        return await self._client._make_request(
            "POST",
            f"/api/{self._client.api_version}/auth/tokens/refresh",
            data=data
        )


class HealthClient:
    """Client for health check operations."""
    
    def __init__(self, client: EasyPayClient):
        self._client = client
    
    async def check(self) -> Dict[str, Any]:
        """
        Perform a basic health check.
        
        Returns:
            Dict containing health status
        """
        return await self._client._make_request(
            "GET",
            "/health"
        )
    
    async def readiness(self) -> Dict[str, Any]:
        """
        Perform a readiness check.
        
        Returns:
            Dict containing readiness status
        """
        return await self._client._make_request(
            "GET",
            "/health/ready"
        )
    
    async def liveness(self) -> Dict[str, Any]:
        """
        Perform a liveness check.
        
        Returns:
            Dict containing liveness status
        """
        return await self._client._make_request(
            "GET",
            "/health/live"
        )
    
    async def detailed(self) -> Dict[str, Any]:
        """
        Perform a detailed health check.
        
        Returns:
            Dict containing detailed health information
        """
        return await self._client._make_request(
            "GET",
            "/health/detailed"
        )
