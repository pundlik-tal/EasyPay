"""
EasyPay Payment Gateway - Enhanced Authorization Middleware
"""
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.core.services.auth_service import AuthService
from src.core.services.rbac_service import RBACService
from src.core.services.scoping_service import ScopingService
from src.core.services.request_signing_service import RequestSigningService, RequestSigningMiddleware
from src.core.services.audit_logging_service import AuditLoggingService, AuditLogger
from src.core.models.auth import Permission
from src.api.v1.schemas.auth import TokenValidationResponse

# Security scheme
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


class EnhancedAuthMiddleware:
    """
    Enhanced authentication middleware with comprehensive security features.
    
    This middleware integrates RBAC, scoping, request signing, and audit logging
    to provide comprehensive security for API endpoints.
    """
    
    def __init__(
        self,
        required_permissions: Optional[List[Permission]] = None,
        require_signed_requests: bool = False,
        enable_scoping: bool = True,
        enable_audit_logging: bool = True,
        signing_service: Optional[RequestSigningService] = None
    ):
        """
        Initialize enhanced authentication middleware.
        
        Args:
            required_permissions: List of required permissions
            require_signed_requests: Whether to require signed requests
            enable_scoping: Whether to enable API key scoping
            enable_audit_logging: Whether to enable audit logging
            signing_service: Request signing service instance
        """
        self.required_permissions = required_permissions or []
        self.require_signed_requests = require_signed_requests
        self.enable_scoping = enable_scoping
        self.enable_audit_logging = enable_audit_logging
        self.signing_service = signing_service
        self.signing_middleware = RequestSigningMiddleware(signing_service) if signing_service else None
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """
        Authenticate request and return enhanced user context.
        
        Args:
            request: FastAPI request object
            credentials: Authorization credentials
            db: Database session
            
        Returns:
            Dict containing enhanced authentication context
            
        Raises:
            HTTPException: If authentication or authorization fails
        """
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time())}")
        
        try:
            # Initialize services
            auth_service = AuthService(db)
            rbac_service = RBACService(db)
            scoping_service = ScopingService(db)
            audit_service = AuditLoggingService(db)
            audit_logger = AuditLogger(audit_service)
            
            # Extract authentication method
            auth_method = await self._extract_auth_method(request, credentials)
            
            if auth_method["type"] == "api_key":
                auth_context = await self._authenticate_api_key(
                    auth_method, db, auth_service, rbac_service, scoping_service, audit_logger, request, request_id
                )
            elif auth_method["type"] == "jwt":
                auth_context = await self._authenticate_jwt(
                    auth_method, db, auth_service, rbac_service, audit_logger, request, request_id
                )
            else:
                await audit_logger.log_login_failure(
                    api_key_id=None,
                    failure_reason="No authentication provided",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Validate request signing if required
            if self.require_signed_requests and self.signing_middleware:
                await self._validate_request_signing(request, auth_context, audit_logger, request_id)
            
            # Check RBAC permissions
            await self._check_rbac_permissions(
                auth_context, rbac_service, request, audit_logger, request_id
            )
            
            # Validate API key scoping
            if self.enable_scoping and auth_context.get("auth_type") == "api_key":
                await self._validate_api_key_scoping(
                    auth_context, scoping_service, request, audit_logger, request_id
                )
            
            # Log successful authentication
            if self.enable_audit_logging:
                await audit_logger.log_login_success(
                    api_key_id=auth_context.get("api_key_id"),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
            
            # Add enhanced context
            auth_context.update({
                "request_id": request_id,
                "auth_timestamp": start_time,
                "enhanced_auth": True
            })
            
            return auth_context
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Enhanced authentication error: {str(e)}")
            
            # Log authentication failure
            if self.enable_audit_logging:
                try:
                    audit_service = AuditLoggingService(db)
                    audit_logger = AuditLogger(audit_service)
                    await audit_logger.log_login_failure(
                        api_key_id=None,
                        failure_reason=f"Authentication service error: {str(e)}",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("User-Agent", ""),
                        request_id=request_id
                    )
                except Exception:
                    pass  # Don't fail on audit logging errors
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    async def _extract_auth_method(
        self, 
        request: Request, 
        credentials: Optional[HTTPAuthorizationCredentials]
    ) -> Dict[str, Any]:
        """Extract authentication method from request."""
        # Check for API key in headers
        api_key_id = request.headers.get("X-API-Key-ID")
        api_key_secret = request.headers.get("X-API-Key-Secret")
        
        if api_key_id and api_key_secret:
            return {
                "type": "api_key",
                "key_id": api_key_id,
                "key_secret": api_key_secret
            }
        
        # Check for JWT token in Authorization header
        if credentials and credentials.scheme.lower() == "bearer":
            return {
                "type": "jwt",
                "token": credentials.credentials
            }
        
        # Check for API key in query parameters (less secure, for testing)
        api_key_id = request.query_params.get("api_key_id")
        api_key_secret = request.query_params.get("api_key_secret")
        
        if api_key_id and api_key_secret:
            return {
                "type": "api_key",
                "key_id": api_key_id,
                "key_secret": api_key_secret
            }
        
        return {"type": "none"}
    
    async def _authenticate_api_key(
        self,
        auth_method: Dict[str, Any],
        db: AsyncSession,
        auth_service: AuthService,
        rbac_service: RBACService,
        scoping_service: ScopingService,
        audit_logger: AuditLogger,
        request: Request,
        request_id: str
    ) -> Dict[str, Any]:
        """Authenticate using API key with enhanced security checks."""
        try:
            api_key = await auth_service.validate_api_key(
                auth_method["key_id"],
                auth_method["key_secret"]
            )
            
            if not api_key:
                await audit_logger.log_login_failure(
                    api_key_id=None,
                    failure_reason="Invalid API key credentials",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key credentials"
                )
            
            # Get role-based permissions
            role_permissions = []
            if api_key.role and api_key.role.is_active:
                role_permissions = api_key.role.get_permission_names()
            
            # Combine with legacy permissions
            all_permissions = list(set(api_key.permissions + role_permissions))
            
            return {
                "authenticated": True,
                "auth_type": "api_key",
                "api_key_id": str(api_key.id),
                "key_id": api_key.key_id,
                "permissions": all_permissions,
                "role_id": str(api_key.role_id) if api_key.role_id else None,
                "role_name": api_key.role.name if api_key.role else None,
                "rate_limits": {
                    "per_minute": api_key.rate_limit_per_minute,
                    "per_hour": api_key.rate_limit_per_hour,
                    "per_day": api_key.rate_limit_per_day
                },
                "scopes": {
                    "ip_whitelist": api_key.ip_whitelist,
                    "ip_blacklist": api_key.ip_blacklist,
                    "user_agent_patterns": api_key.user_agent_patterns
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    async def _authenticate_jwt(
        self,
        auth_method: Dict[str, Any],
        db: AsyncSession,
        auth_service: AuthService,
        rbac_service: RBACService,
        audit_logger: AuditLogger,
        request: Request,
        request_id: str
    ) -> Dict[str, Any]:
        """Authenticate using JWT token with enhanced security checks."""
        try:
            validation_result = await auth_service.validate_token(auth_method["token"])
            
            if not validation_result["valid"]:
                await audit_logger.log_login_failure(
                    api_key_id=None,
                    failure_reason=validation_result.get("error", "Invalid token"),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=validation_result.get("error", "Invalid token")
                )
            
            return {
                "authenticated": True,
                "auth_type": "jwt",
                "token_id": validation_result["token_id"],
                "api_key_id": validation_result["api_key_id"],
                "permissions": validation_result["permissions"],
                "expires_at": validation_result["expires_at"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    async def _validate_request_signing(
        self,
        request: Request,
        auth_context: Dict[str, Any],
        audit_logger: AuditLogger,
        request_id: str
    ):
        """Validate request signing if required."""
        try:
            if not self.signing_middleware.should_validate_signature(dict(request.headers)):
                await audit_logger.log_security_violation_event(
                    violation_type="unsigned_request",
                    message="Request signing required but not provided",
                    api_key_id=auth_context.get("api_key_id"),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request signing required"
                )
            
            # Validate signature
            await self.signing_middleware.validate_request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                body=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            await audit_logger.log_security_violation_event(
                violation_type="invalid_signature",
                message=f"Request signature validation failed: {str(e)}",
                api_key_id=auth_context.get("api_key_id"),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent", ""),
                request_id=request_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature"
            )
    
    async def _check_rbac_permissions(
        self,
        auth_context: Dict[str, Any],
        rbac_service: RBACService,
        request: Request,
        audit_logger: AuditLogger,
        request_id: str
    ):
        """Check RBAC permissions."""
        if not self.required_permissions:
            return
        
        user_permissions = auth_context.get("permissions", [])
        
        for required_permission in self.required_permissions:
            if required_permission.value not in user_permissions:
                # Check resource-level permissions
                resource_type = self._extract_resource_type(request)
                resource_id = self._extract_resource_id(request)
                
                if resource_type and resource_id:
                    has_resource_permission = await rbac_service.check_permission(
                        api_key_id=auth_context.get("api_key_id"),
                        resource_type=resource_type,
                        action=required_permission.value.split(":")[1] if ":" in required_permission.value else "read",
                        resource_id=resource_id
                    )
                    
                    if has_resource_permission:
                        continue
                
                await audit_logger.log_permission_denied(
                    api_key_id=auth_context.get("api_key_id"),
                    resource_type=resource_type or "unknown",
                    resource_id=resource_id or "unknown",
                    action=required_permission.value,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission.value}"
                )
    
    async def _validate_api_key_scoping(
        self,
        auth_context: Dict[str, Any],
        scoping_service: ScopingService,
        request: Request,
        audit_logger: AuditLogger,
        request_id: str
    ):
        """Validate API key scoping."""
        try:
            # Extract environment from request
            environment = request.headers.get("X-Environment", "production")
            
            # Validate scoping
            validation_result = await scoping_service.validate_api_key_access(
                api_key_id=auth_context.get("api_key_id"),
                environment=environment,
                domain=request.headers.get("Host"),
                client_ip=request.client.host if request.client else None,
                resource_type=self._extract_resource_type(request),
                resource_count=1
            )
            
            if not validation_result["valid"]:
                await audit_logger.log_security_violation_event(
                    violation_type="scope_violation",
                    message=f"API key scoping violation: {', '.join(validation_result['restrictions'])}",
                    api_key_id=auth_context.get("api_key_id"),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent", ""),
                    request_id=request_id
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: {', '.join(validation_result['restrictions'])}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key scoping validation error: {str(e)}")
            # Don't fail on scoping errors, just log them
            await audit_logger.log_security_violation_event(
                violation_type="scoping_error",
                message=f"API key scoping validation error: {str(e)}",
                api_key_id=auth_context.get("api_key_id"),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent", ""),
                request_id=request_id
            )
    
    def _extract_resource_type(self, request: Request) -> Optional[str]:
        """Extract resource type from request path."""
        path = request.url.path
        
        if "/payments/" in path:
            return "payment"
        elif "/webhooks/" in path:
            return "webhook"
        elif "/api-keys/" in path:
            return "api_key"
        elif "/users/" in path:
            return "user"
        elif "/admin/" in path:
            return "system"
        
        return None
    
    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """Extract resource ID from request path."""
        path_parts = request.url.path.split("/")
        
        # Look for UUID patterns in the path
        for part in path_parts:
            if len(part) == 36 and "-" in part:  # UUID format
                return part
        
        return None


# Enhanced dependency functions
async def require_enhanced_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Require enhanced authentication with all security features."""
    middleware = EnhancedAuthMiddleware()
    return await middleware(request, credentials, db)


async def require_enhanced_payments_read(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Require enhanced authentication with payments read permission."""
    middleware = EnhancedAuthMiddleware([Permission.PAYMENTS_READ])
    return await middleware(request, credentials, db)


async def require_enhanced_payments_write(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Require enhanced authentication with payments write permission."""
    middleware = EnhancedAuthMiddleware([Permission.PAYMENTS_WRITE])
    return await middleware(request, credentials, db)


async def require_enhanced_admin_access(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Require enhanced authentication with admin access."""
    middleware = EnhancedAuthMiddleware([Permission.ADMIN_WRITE])
    return await middleware(request, credentials, db)


async def require_signed_requests(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Require signed requests with enhanced authentication."""
    # Initialize signing service (in production, this would come from config)
    signing_service = RequestSigningService("your-secret-key-change-in-production")
    
    middleware = EnhancedAuthMiddleware(
        require_signed_requests=True,
        signing_service=signing_service
    )
    return await middleware(request, credentials, db)
