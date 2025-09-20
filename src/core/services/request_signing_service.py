"""
EasyPay Payment Gateway - Request Signing Service
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs

from src.core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError
)


class RequestSigningService:
    """
    Request signing service for API security using HMAC.
    
    This service provides cryptographic request signing to ensure
    request integrity and authenticity.
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize request signing service.
        
        Args:
            secret_key: Secret key for HMAC signing
        """
        self.secret_key = secret_key.encode('utf-8')
    
    def generate_signature(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        timestamp: Optional[int] = None
    ) -> str:
        """
        Generate HMAC signature for a request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            body: Request body (optional)
            timestamp: Request timestamp (optional, defaults to current time)
            
        Returns:
            Base64-encoded HMAC signature
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create signature string
        signature_string = self._create_signature_string(
            method, url, headers, body, timestamp
        )
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key,
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Return base64-encoded signature
        import base64
        return base64.b64encode(signature).decode('utf-8')
    
    def _create_signature_string(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        timestamp: int
    ) -> str:
        """Create the string to be signed."""
        # Parse URL
        parsed_url = urlparse(url)
        
        # Create signature components
        components = [
            method.upper(),
            parsed_url.netloc,
            parsed_url.path,
            self._create_query_string(parsed_url.query),
            self._create_header_string(headers),
            str(timestamp),
            body or ""
        ]
        
        return "\n".join(components)
    
    def _create_query_string(self, query: str) -> str:
        """Create normalized query string."""
        if not query:
            return ""
        
        # Parse and sort query parameters
        params = parse_qs(query, keep_blank_values=True)
        sorted_params = []
        
        for key in sorted(params.keys()):
            values = params[key]
            for value in sorted(values):
                sorted_params.append(f"{key}={value}")
        
        return "&".join(sorted_params)
    
    def _create_header_string(self, headers: Dict[str, str]) -> str:
        """Create normalized header string."""
        # Filter and sort headers
        filtered_headers = {}
        for key, value in headers.items():
            if key.lower().startswith('x-'):
                filtered_headers[key.lower()] = value
        
        # Create header string
        header_pairs = []
        for key in sorted(filtered_headers.keys()):
            header_pairs.append(f"{key}:{filtered_headers[key]}")
        
        return "\n".join(header_pairs)
    
    def verify_signature(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        signature: str,
        timestamp: int,
        max_age: int = 300  # 5 minutes default
    ) -> bool:
        """
        Verify HMAC signature for a request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            signature: Provided signature
            timestamp: Request timestamp
            max_age: Maximum age of request in seconds
            
        Returns:
            True if signature is valid
            
        Raises:
            AuthenticationError: If signature verification fails
        """
        # Check timestamp
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age:
            raise AuthenticationError("Request timestamp is too old")
        
        # Generate expected signature
        expected_signature = self.generate_signature(
            method, url, headers, body, timestamp
        )
        
        # Compare signatures (constant time comparison)
        if not self._constant_time_compare(signature, expected_signature):
            raise AuthenticationError("Invalid request signature")
        
        return True
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks."""
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0
    
    def create_signed_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a signed request with all necessary headers.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Existing headers
            body: Request body
            
        Returns:
            Dict containing headers for the signed request
        """
        if headers is None:
            headers = {}
        
        timestamp = int(time.time())
        
        # Generate signature
        signature = self.generate_signature(method, url, headers, body, timestamp)
        
        # Create signed headers
        signed_headers = headers.copy()
        signed_headers.update({
            'X-Timestamp': str(timestamp),
            'X-Signature': signature,
            'X-Signature-Method': 'HMAC-SHA256',
            'X-Signature-Version': '1.0'
        })
        
        return signed_headers
    
    def extract_signature_info(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract signature information from headers.
        
        Args:
            headers: Request headers
            
        Returns:
            Dict containing signature information
            
        Raises:
            ValidationError: If required headers are missing
        """
        required_headers = ['X-Timestamp', 'X-Signature', 'X-Signature-Method']
        
        for header in required_headers:
            if header not in headers:
                raise ValidationError(f"Missing required header: {header}")
        
        try:
            timestamp = int(headers['X-Timestamp'])
        except ValueError:
            raise ValidationError("Invalid timestamp format")
        
        return {
            'timestamp': timestamp,
            'signature': headers['X-Signature'],
            'method': headers['X-Signature-Method'],
            'version': headers.get('X-Signature-Version', '1.0')
        }
    
    def validate_request_signature(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        max_age: int = 300
    ) -> bool:
        """
        Validate request signature from headers.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            max_age: Maximum age of request in seconds
            
        Returns:
            True if signature is valid
            
        Raises:
            AuthenticationError: If signature validation fails
        """
        # Extract signature info
        sig_info = self.extract_signature_info(headers)
        
        # Verify signature
        return self.verify_signature(
            method=method,
            url=url,
            headers=headers,
            body=body,
            signature=sig_info['signature'],
            timestamp=sig_info['timestamp'],
            max_age=max_age
        )


class WebhookSigningService:
    """
    Webhook signing service for secure webhook delivery.
    
    This service provides webhook signature generation and verification
    to ensure webhook authenticity and integrity.
    """
    
    def __init__(self, webhook_secret: str):
        """
        Initialize webhook signing service.
        
        Args:
            webhook_secret: Secret key for webhook signing
        """
        self.webhook_secret = webhook_secret.encode('utf-8')
    
    def generate_webhook_signature(
        self,
        payload: str,
        timestamp: Optional[int] = None
    ) -> str:
        """
        Generate webhook signature.
        
        Args:
            payload: Webhook payload
            timestamp: Timestamp (optional, defaults to current time)
            
        Returns:
            Webhook signature
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create signature string
        signature_string = f"{timestamp}.{payload}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.webhook_secret,
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"t={timestamp},v1={signature}"
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature_header: str,
        max_age: int = 300
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Webhook payload
            signature_header: Signature header value
            max_age: Maximum age of webhook in seconds
            
        Returns:
            True if signature is valid
            
        Raises:
            AuthenticationError: If signature verification fails
        """
        # Parse signature header
        sig_parts = {}
        for part in signature_header.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                sig_parts[key.strip()] = value.strip()
        
        if 't' not in sig_parts or 'v1' not in sig_parts:
            raise AuthenticationError("Invalid signature format")
        
        try:
            timestamp = int(sig_parts['t'])
        except ValueError:
            raise AuthenticationError("Invalid timestamp format")
        
        # Check timestamp
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age:
            raise AuthenticationError("Webhook timestamp is too old")
        
        # Generate expected signature
        expected_signature = self.generate_webhook_signature(payload, timestamp)
        expected_sig_parts = {}
        for part in expected_signature.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                expected_sig_parts[key.strip()] = value.strip()
        
        # Compare signatures
        if sig_parts['v1'] != expected_sig_parts['v1']:
            raise AuthenticationError("Invalid webhook signature")
        
        return True


class RequestSigningMiddleware:
    """
    Middleware for request signing validation.
    
    This middleware validates request signatures for API endpoints
    that require signed requests.
    """
    
    def __init__(self, signing_service: RequestSigningService):
        """
        Initialize request signing middleware.
        
        Args:
            signing_service: Request signing service instance
        """
        self.signing_service = signing_service
    
    async def validate_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None
    ) -> bool:
        """
        Validate request signature.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            True if request is valid
            
        Raises:
            AuthenticationError: If request validation fails
        """
        try:
            return self.signing_service.validate_request_signature(
                method=method,
                url=url,
                headers=headers,
                body=body
            )
        except Exception as e:
            raise AuthenticationError(f"Request signature validation failed: {str(e)}")
    
    def should_validate_signature(self, headers: Dict[str, str]) -> bool:
        """
        Check if request should be validated for signature.
        
        Args:
            headers: Request headers
            
        Returns:
            True if signature validation is required
        """
        return 'X-Signature' in headers
    
    def extract_client_info(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract client information from signed request headers.
        
        Args:
            headers: Request headers
            
        Returns:
            Dict containing client information
        """
        client_info = {}
        
        if 'X-Client-ID' in headers:
            client_info['client_id'] = headers['X-Client-ID']
        
        if 'X-Client-Version' in headers:
            client_info['client_version'] = headers['X-Client-Version']
        
        if 'X-Request-ID' in headers:
            client_info['request_id'] = headers['X-Request-ID']
        
        return client_info
