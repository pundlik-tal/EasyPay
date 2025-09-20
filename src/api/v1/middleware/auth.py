"""
EasyPay Payment Gateway - Authentication Middleware
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.core.services.auth_service import AuthService
from src.core.models.auth import Permission
from src.api.v1.schemas.auth import TokenValidationResponse

# Security scheme
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Authentication middleware for API endpoints.
    
    This middleware handles API key and JWT token validation,
    permission checking, and rate limiting.
    """
    
    def __init__(self, required_permissions: Optional[List[Permission]] = None):
        """
        Initialize authentication middleware.
        
        Args:
            required_permissions: List of required permissions
        """
        self.required_permissions = required_permissions or []
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """
        Authenticate request and return user context.
        
        Args:
            request: FastAPI request object
            credentials: Authorization credentials
            db: Database session
            
        Returns:
            Dict containing authentication context
            
        Raises:
            HTTPException: If authentication fails
        """
        # Extract authentication method
        auth_method = await self._extract_auth_method(request, credentials)
        
        if auth_method["type"] == "api_key":
            return await self._authenticate_api_key(auth_method, db)
        elif auth_method["type"] == "jwt":
            return await self._authenticate_jwt(auth_method, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    async def _extract_auth_method(
        self, 
        request: Request, 
        credentials: Optional[HTTPAuthorizationCredentials]
    ) -> Dict[str, Any]:
        """
        Extract authentication method from request.
        
        Args:
            request: FastAPI request object
            credentials: Authorization credentials
            
        Returns:
            Dict containing authentication method info
        """
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
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Authenticate using API key.
        
        Args:
            auth_method: Authentication method info
            db: Database session
            
        Returns:
            Dict containing authentication context
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            auth_service = AuthService(db)
            api_key = await auth_service.validate_api_key(
                auth_method["key_id"],
                auth_method["key_secret"]
            )
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key credentials"
                )
            
            # Check permissions
            await self._check_permissions(api_key.permissions)
            
            # Check rate limits (simplified implementation)
            await self._check_rate_limits(api_key, db)
            
            return {
                "authenticated": True,
                "auth_type": "api_key",
                "api_key_id": str(api_key.id),
                "key_id": api_key.key_id,
                "permissions": api_key.permissions,
                "rate_limits": {
                    "per_minute": api_key.rate_limit_per_minute,
                    "per_hour": api_key.rate_limit_per_hour,
                    "per_day": api_key.rate_limit_per_day
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
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Authenticate using JWT token.
        
        Args:
            auth_method: Authentication method info
            db: Database session
            
        Returns:
            Dict containing authentication context
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            auth_service = AuthService(db)
            validation_result = await auth_service.validate_token(auth_method["token"])
            
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=validation_result.get("error", "Invalid token")
                )
            
            # Check permissions
            await self._check_permissions(validation_result["permissions"])
            
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
    
    async def _check_permissions(self, user_permissions: List[str]) -> None:
        """
        Check if user has required permissions.
        
        Args:
            user_permissions: User's permissions
            
        Raises:
            HTTPException: If user lacks required permissions
        """
        if not self.required_permissions:
            return
        
        for required_permission in self.required_permissions:
            if required_permission.value not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission.value}"
                )
    
    async def _check_rate_limits(self, api_key, db: AsyncSession) -> None:
        """
        Check API key rate limits (simplified implementation).
        
        Args:
            api_key: API key object
            db: Database session
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # This is a simplified rate limiting implementation
        # In production, you would use Redis or similar for distributed rate limiting
        
        # For now, we'll just log the usage
        logger.info(f"API key {api_key.key_id} used. Usage count: {api_key.usage_count}")
        
        # You could implement more sophisticated rate limiting here
        # using Redis counters and sliding windows


# Dependency functions for different permission levels
async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require any valid authentication.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware()
    return await middleware(request, credentials, db)


async def require_payments_read(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require payments read permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.PAYMENTS_READ])
    return await middleware(request, credentials, db)


async def require_payments_write(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require payments write permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.PAYMENTS_WRITE])
    return await middleware(request, credentials, db)


async def require_payments_delete(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require payments delete permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.PAYMENTS_DELETE])
    return await middleware(request, credentials, db)


async def require_webhooks_read(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require webhooks read permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.WEBHOOKS_READ])
    return await middleware(request, credentials, db)


async def require_webhooks_write(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require webhooks write permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.WEBHOOKS_WRITE])
    return await middleware(request, credentials, db)


async def require_admin_read(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require admin read permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.ADMIN_READ])
    return await middleware(request, credentials, db)


async def require_admin_write(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Require admin write permission.
    
    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Authentication context
    """
    middleware = AuthMiddleware([Permission.ADMIN_WRITE])
    return await middleware(request, credentials, db)


# Utility function to check permissions in endpoints
def check_permission(user_permissions: List[str], required_permission: Permission) -> bool:
    """
    Check if user has specific permission.
    
    Args:
        user_permissions: User's permissions
        required_permission: Required permission
        
    Returns:
        True if user has permission
    """
    return required_permission.value in user_permissions


# Utility function to get current user context
def get_current_user(auth_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current user context from authentication context.
    
    Args:
        auth_context: Authentication context
        
    Returns:
        User context
    """
    return {
        "api_key_id": auth_context.get("api_key_id"),
        "key_id": auth_context.get("key_id"),
        "permissions": auth_context.get("permissions", []),
        "auth_type": auth_context.get("auth_type")
    }
