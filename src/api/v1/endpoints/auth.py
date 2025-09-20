"""
EasyPay Payment Gateway - Authentication Endpoints
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.core.services.auth_service import AuthService
from src.core.exceptions import (
    AuthenticationError,
    ValidationError,
    DatabaseError,
    NotFoundError
)
from src.api.v1.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyUpdateRequest,
    APIKeyResponse,
    APIKeyCreateResponse,
    APIKeyListResponse,
    TokenRequest,
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenValidationResponse,
    AuthErrorResponse,
    PermissionCheckRequest,
    PermissionCheckResponse
)
from src.api.v1.schemas.errors import (
    ErrorResponse,
    ValidationErrorResponse,
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    NotFoundErrorResponse
)
from src.api.v1.middleware.auth import (
    require_auth,
    require_admin_write,
    require_admin_read,
    get_current_user
)

router = APIRouter()


@router.post(
    "/api-keys", 
    response_model=APIKeyCreateResponse, 
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "API key created successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid request data"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Create API Key",
    description="""
    Create a new API key with specified permissions and rate limits.
    
    ### API Key Features
    - **Unique Key Pair**: Generated key_id and key_secret for authentication
    - **Permission-based Access**: Granular permissions for different operations
    - **Rate Limiting**: Configurable limits per minute, hour, and day
    - **IP Restrictions**: Whitelist and blacklist IP addresses
    - **Expiration**: Optional expiration date for automatic key rotation
    
    ### Permissions
    - `payments:read`: Read payment data
    - `payments:write`: Create and update payments
    - `payments:delete`: Delete payments
    - `webhooks:read`: Read webhook data
    - `webhooks:write`: Manage webhooks
    - `admin:read`: Read administrative data
    - `admin:write`: Administrative operations
    
    ### Security
    - Key secret is only returned once during creation
    - Store the key secret securely
    - Use environment variables for key storage
    - Rotate keys regularly for security
    
    ### Rate Limits
    - Default: 100/min, 1000/hour, 10000/day
    - Configurable per API key
    - Enforced at the gateway level
    """,
    tags=["authentication"]
)
async def create_api_key(
    request: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_write)
) -> APIKeyCreateResponse:
    """
    Create a new API key.
    
    Args:
        request: API key creation request
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        APIKeyCreateResponse: Created API key information
        
    Raises:
        ValidationError: If request data is invalid
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.create_api_key(request)
        
        return APIKeyCreateResponse(
            id=result["id"],
            key_id=result["key_id"],
            key_secret=result["key_secret"],
            name=result["name"],
            description=result["description"],
            permissions=result["permissions"],
            expires_at=result["expires_at"],
            created_at=result["created_at"]
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_read)
) -> APIKeyListResponse:
    """
    List API keys with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        APIKeyListResponse: List of API keys
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        api_keys = await auth_service.list_api_keys(skip, limit, status)
        
        # Convert to response format
        api_key_responses = [
            APIKeyResponse(
                id=key.id,
                key_id=key.key_id,
                name=key.name,
                description=key.description,
                status=key.status,
                permissions=key.permissions,
                usage_count=key.usage_count,
                rate_limit_per_minute=key.rate_limit_per_minute,
                rate_limit_per_hour=key.rate_limit_per_hour,
                rate_limit_per_day=key.rate_limit_per_day,
                ip_whitelist=key.ip_whitelist,
                ip_blacklist=key.ip_blacklist,
                expires_at=key.expires_at,
                created_at=key.created_at,
                updated_at=key.updated_at,
                last_used_at=key.last_used_at
            )
            for key in api_keys
        ]
        
        return APIKeyListResponse(
            api_keys=api_key_responses,
            total=len(api_key_responses),
            page=skip // limit + 1,
            per_page=limit
        )
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_read)
) -> APIKeyResponse:
    """
    Get API key by ID.
    
    Args:
        api_key_id: API key UUID
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        APIKeyResponse: API key information
        
    Raises:
        NotFoundError: If API key not found
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        api_key = await auth_service.get_api_key_by_id(api_key_id)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return APIKeyResponse(
            id=api_key.id,
            key_id=api_key.key_id,
            name=api_key.name,
            description=api_key.description,
            status=api_key.status,
            permissions=api_key.permissions,
            usage_count=api_key.usage_count,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_hour=api_key.rate_limit_per_hour,
            rate_limit_per_day=api_key.rate_limit_per_day,
            ip_whitelist=api_key.ip_whitelist,
            ip_blacklist=api_key.ip_blacklist,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            last_used_at=api_key.last_used_at
        )
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: UUID,
    request: APIKeyUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_write)
) -> APIKeyResponse:
    """
    Update an API key.
    
    Args:
        api_key_id: API key UUID
        request: Update request
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        APIKeyResponse: Updated API key information
        
    Raises:
        NotFoundError: If API key not found
        ValidationError: If request data is invalid
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        api_key = await auth_service.update_api_key(api_key_id, request)
        
        return APIKeyResponse(
            id=api_key.id,
            key_id=api_key.key_id,
            name=api_key.name,
            description=api_key.description,
            status=api_key.status,
            permissions=api_key.permissions,
            usage_count=api_key.usage_count,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_hour=api_key.rate_limit_per_hour,
            rate_limit_per_day=api_key.rate_limit_per_day,
            ip_whitelist=api_key.ip_whitelist,
            ip_blacklist=api_key.ip_blacklist,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            last_used_at=api_key.last_used_at
        )
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_write)
) -> None:
    """
    Delete an API key.
    
    Args:
        api_key_id: API key UUID
        db: Database session dependency
        auth_context: Authentication context
        
    Raises:
        NotFoundError: If API key not found
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        await auth_service.delete_api_key(api_key_id)
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tokens", 
    response_model=TokenResponse,
    responses={
        200: {"description": "Tokens generated successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid request data"},
        401: {"model": AuthenticationErrorResponse, "description": "Invalid API key credentials"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate JWT Tokens",
    description="""
    Generate JWT access and refresh tokens using API key credentials.
    
    ### Token Types
    - **Access Token**: Short-lived token for API access (default 1 hour)
    - **Refresh Token**: Long-lived token for token renewal (default 30 days)
    
    ### Token Features
    - **Stateless Authentication**: No server-side session storage
    - **Permission-based Access**: Tokens inherit API key permissions
    - **Configurable Expiration**: Custom token lifetime
    - **Secure Signing**: HMAC-SHA256 signed tokens
    
    ### Usage
    1. Use API key credentials to generate tokens
    2. Include access token in Authorization header: `Bearer <access_token>`
    3. Use refresh token to get new access tokens when expired
    4. Tokens automatically inherit API key permissions and rate limits
    
    ### Security
    - Tokens are signed with a secret key
    - Store tokens securely (not in localStorage for web apps)
    - Use HTTPS for all token transmission
    - Implement token rotation for enhanced security
    """,
    tags=["authentication"]
)
async def generate_tokens(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """
    Generate JWT tokens for API key.
    
    Args:
        request: Token generation request
        db: Database session dependency
        
    Returns:
        TokenResponse: Generated tokens
        
    Raises:
        AuthenticationError: If API key validation fails
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.generate_tokens(request)
        
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            expires_at=result["expires_at"]
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tokens/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session)
) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Token refresh request
        db: Database session dependency
        
    Returns:
        TokenRefreshResponse: New tokens
        
    Raises:
        AuthenticationError: If refresh token is invalid
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.refresh_token(request)
        
        return TokenRefreshResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            expires_at=result["expires_at"]
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tokens/validate", response_model=TokenValidationResponse)
async def validate_token(
    token: str,
    db: AsyncSession = Depends(get_db_session)
) -> TokenValidationResponse:
    """
    Validate JWT token.
    
    Args:
        token: JWT token to validate
        db: Database session dependency
        
    Returns:
        TokenValidationResponse: Validation result
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        result = await auth_service.validate_token(token)
        
        return TokenValidationResponse(
            valid=result["valid"],
            token_id=result.get("token_id"),
            api_key_id=result.get("api_key_id"),
            permissions=result.get("permissions"),
            expires_at=result.get("expires_at"),
            error=result.get("error")
        )
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tokens/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token: str,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_auth)
) -> None:
    """
    Revoke a JWT token.
    
    Args:
        token: JWT token to revoke
        db: Database session dependency
        auth_context: Authentication context
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        await auth_service.revoke_token(token)
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_auth)
) -> PermissionCheckResponse:
    """
    Check if current user has specific permission.
    
    Args:
        request: Permission check request
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        PermissionCheckResponse: Permission check result
    """
    user_permissions = auth_context.get("permissions", [])
    has_permission = request.permission in user_permissions
    
    return PermissionCheckResponse(
        has_permission=has_permission,
        permission=request.permission,
        api_key_id=auth_context.get("api_key_id")
    )


@router.get("/me", response_model=dict)
async def get_current_user_info(
    auth_context: dict = Depends(require_auth)
) -> dict:
    """
    Get current user information.
    
    Args:
        auth_context: Authentication context
        
    Returns:
        Dict containing current user information
    """
    return get_current_user(auth_context)


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_tokens(
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_admin_write)
) -> dict:
    """
    Clean up expired tokens from database.
    
    Args:
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        Dict containing cleanup results
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        auth_service = AuthService(db)
        cleaned_count = await auth_service.cleanup_expired_tokens()
        
        return {
            "message": f"Cleaned up {cleaned_count} expired tokens",
            "cleaned_count": cleaned_count
        }
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
