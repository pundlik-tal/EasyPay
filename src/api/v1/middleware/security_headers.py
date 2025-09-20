"""
EasyPay Payment Gateway - Security Headers Middleware
"""
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding comprehensive security headers.
    
    This middleware adds various security headers to all responses
    to enhance the security posture of the API.
    """
    
    def __init__(
        self,
        app,
        cors_origins: Optional[list] = None,
        cors_methods: Optional[list] = None,
        cors_headers: Optional[list] = None,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        enable_frame_options: bool = True,
        enable_content_type_options: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            cors_origins: Allowed CORS origins
            cors_methods: Allowed CORS methods
            cors_headers: Allowed CORS headers
            enable_csp: Enable Content Security Policy
            enable_hsts: Enable HTTP Strict Transport Security
            enable_frame_options: Enable X-Frame-Options
            enable_content_type_options: Enable X-Content-Type-Options
            enable_referrer_policy: Enable Referrer Policy
            enable_permissions_policy: Enable Permissions Policy
        """
        super().__init__(app)
        
        # CORS configuration
        self.cors_origins = cors_origins or ["*"]
        self.cors_methods = cors_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_headers = cors_headers or ["*"]
        
        # Security features
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.enable_frame_options = enable_frame_options
        self.enable_content_type_options = enable_content_type_options
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_permissions_policy = enable_permissions_policy
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers."""
        try:
            # Handle preflight CORS requests
            if request.method == "OPTIONS":
                response = await self._handle_preflight_request(request)
                return response
            
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Security headers middleware error: {str(e)}")
            # Return error response with security headers
            error_response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
            self._add_security_headers(request, error_response)
            return error_response
    
    async def _handle_preflight_request(self, request: Request) -> Response:
        """Handle CORS preflight requests."""
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        if self._is_origin_allowed(origin):
            response = Response(status_code=200)
            self._add_cors_headers(response, origin)
            self._add_security_headers(request, response)
            return response
        else:
            response = Response(status_code=403)
            self._add_security_headers(request, response)
            return response
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return False
        
        if "*" in self.cors_origins:
            return True
        
        return origin in self.cors_origins
    
    def _add_cors_headers(self, response: Response, origin: Optional[str] = None):
        """Add CORS headers to response."""
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.cors_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.cors_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
    
    def _add_security_headers(self, request: Request, response: Response):
        """Add comprehensive security headers to response."""
        # CORS headers
        origin = request.headers.get("origin")
        self._add_cors_headers(response, origin)
        
        # Content Security Policy
        if self.enable_csp:
            self._add_csp_header(response)
        
        # HTTP Strict Transport Security
        if self.enable_hsts:
            self._add_hsts_header(response)
        
        # X-Frame-Options
        if self.enable_frame_options:
            self._add_frame_options_header(response)
        
        # X-Content-Type-Options
        if self.enable_content_type_options:
            self._add_content_type_options_header(response)
        
        # Referrer Policy
        if self.enable_referrer_policy:
            self._add_referrer_policy_header(response)
        
        # Permissions Policy
        if self.enable_permissions_policy:
            self._add_permissions_policy_header(response)
        
        # Additional security headers
        self._add_additional_security_headers(response)
    
    def _add_csp_header(self, response: Response):
        """Add Content Security Policy header."""
        csp_policy = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "child-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "manifest-src 'self'"
        ]
        
        response.headers["Content-Security-Policy"] = "; ".join(csp_policy)
    
    def _add_hsts_header(self, response: Response):
        """Add HTTP Strict Transport Security header."""
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    
    def _add_frame_options_header(self, response: Response):
        """Add X-Frame-Options header."""
        response.headers["X-Frame-Options"] = "DENY"
    
    def _add_content_type_options_header(self, response: Response):
        """Add X-Content-Type-Options header."""
        response.headers["X-Content-Type-Options"] = "nosniff"
    
    def _add_referrer_policy_header(self, response: Response):
        """Add Referrer Policy header."""
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    def _add_permissions_policy_header(self, response: Response):
        """Add Permissions Policy header."""
        permissions_policy = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "speaker=()",
            "vibrate=()",
            "fullscreen=(self)",
            "sync-xhr=()"
        ]
        
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)
    
    def _add_additional_security_headers(self, response: Response):
        """Add additional security headers."""
        # X-XSS-Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Cache Control for sensitive endpoints
        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        # Pragma
        response.headers["Pragma"] = "no-cache"
        
        # Expires
        response.headers["Expires"] = "0"
        
        # Server header (hide server information)
        response.headers["Server"] = "EasyPay-API"
        
        # X-Powered-By (remove if present)
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]


class SecurityHeadersConfig:
    """Configuration for security headers middleware."""
    
    def __init__(
        self,
        cors_origins: Optional[list] = None,
        cors_methods: Optional[list] = None,
        cors_headers: Optional[list] = None,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        enable_frame_options: bool = True,
        enable_content_type_options: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True
    ):
        """Initialize security headers configuration."""
        self.cors_origins = cors_origins or ["*"]
        self.cors_methods = cors_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_headers = cors_headers or ["*"]
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.enable_frame_options = enable_frame_options
        self.enable_content_type_options = enable_content_type_options
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_permissions_policy = enable_permissions_policy
    
    def get_cors_origins_for_environment(self, environment: str) -> list:
        """Get CORS origins based on environment."""
        if environment == "production":
            return [
                "https://app.easypay.com",
                "https://dashboard.easypay.com",
                "https://api.easypay.com"
            ]
        elif environment == "staging":
            return [
                "https://staging-app.easypay.com",
                "https://staging-dashboard.easypay.com",
                "https://staging-api.easypay.com"
            ]
        else:
            return ["*"]  # Development/testing
    
    def get_csp_policy_for_environment(self, environment: str) -> str:
        """Get CSP policy based on environment."""
        if environment == "production":
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "frame-ancestors 'none'"
            )
        else:
            return (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            )


def create_security_headers_middleware(
    cors_origins: Optional[list] = None,
    cors_methods: Optional[list] = None,
    cors_headers: Optional[list] = None,
    enable_csp: bool = True,
    enable_hsts: bool = True,
    enable_frame_options: bool = True,
    enable_content_type_options: bool = True,
    enable_referrer_policy: bool = True,
    enable_permissions_policy: bool = True
) -> SecurityHeadersMiddleware:
    """
    Create security headers middleware with configuration.
    
    Args:
        cors_origins: Allowed CORS origins
        cors_methods: Allowed CORS methods
        cors_headers: Allowed CORS headers
        enable_csp: Enable Content Security Policy
        enable_hsts: Enable HTTP Strict Transport Security
        enable_frame_options: Enable X-Frame-Options
        enable_content_type_options: Enable X-Content-Type-Options
        enable_referrer_policy: Enable Referrer Policy
        enable_permissions_policy: Enable Permissions Policy
        
    Returns:
        Configured SecurityHeadersMiddleware instance
    """
    def middleware_factory(app):
        return SecurityHeadersMiddleware(
            app=app,
            cors_origins=cors_origins,
            cors_methods=cors_methods,
            cors_headers=cors_headers,
            enable_csp=enable_csp,
            enable_hsts=enable_hsts,
            enable_frame_options=enable_frame_options,
            enable_content_type_options=enable_content_type_options,
            enable_referrer_policy=enable_referrer_policy,
            enable_permissions_policy=enable_permissions_policy
        )
    
    return middleware_factory
